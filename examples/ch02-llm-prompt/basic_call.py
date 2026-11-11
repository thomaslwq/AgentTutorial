"""第02章 · 最基础的 Chat Completions 调用，含关键参数说明与工程化错误处理。

前置：
    export OPENAI_API_KEY=sk-你的key
    # 兼容 OpenAI 协议的服务另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install openai>=1.40,<2
    python basic_call.py
"""
import time

from openai import OpenAI, APITimeoutError, RateLimitError, APIConnectionError

# OpenAI() 会自动读取环境变量 OPENAI_API_KEY / OPENAI_BASE_URL，严禁硬编码 Key
client = OpenAI(timeout=10.0)

# messages 是一个有序消息列表，三种标准角色：
# - system：设定模型角色、总体规则与风格，通常只在列表开头出现一次；
# - user：用户（或程序代入的外部输入）提出的任务；
# - assistant：模型上一轮的回复，多轮对话时把它追加回列表即可形成上下文。
messages = [
    {"role": "system", "content": "你是一名严谨的技术讲师，回答简洁直接，必要时给出简短代码示例。"},
    {"role": "user", "content": "用一句话解释什么是缓存击穿。"},
]


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数：英文约 4 字符/token，中文约 1.5 字符/token。

    生产环境建议用 tiktoken 按具体模型词表精确计数；这里只演示预算控制的思路。
    """
    return max(1, len(text) // 3)


def truncate_messages(msgs: list[dict], max_prompt_tokens: int) -> list[dict]:
    """在不丢弃 system 消息的前提下，从最早的历史消息开始裁剪，防止上下文超长。"""
    system_msgs = [m for m in msgs if m["role"] == "system"]
    history = [m for m in msgs if m["role"] != "system"]

    total = sum(estimate_tokens(m["content"]) for m in system_msgs)
    kept: list[dict] = []
    for msg in reversed(history):  # 优先保留最近的消息
        cost = estimate_tokens(msg["content"])
        if total + cost > max_prompt_tokens:
            break
        kept.append(msg)
        total += cost
    return system_msgs + list(reversed(kept))


def create_chat_completion_with_retry(
    msgs: list[dict],
    model: str = "gpt-4o-mini",
    max_retries: int = 3,
):
    """带超时、限流退避与连接错误重试的调用封装，返回完整 response 对象。

    - APITimeoutError：请求超时，直接重试；
    - RateLimitError：触发限流，按指数退避等待后重试；
    - APIConnectionError：网络/网关问题，退避后重试。
    """
    last_error: Exception | None = None
    for attempt in range(max_retries):
        try:
            return client.chat.completions.create(
                model=model,
                messages=truncate_messages(msgs, max_prompt_tokens=3000),
                temperature=0.3,        # 采样温度：越低越稳定，0 接近确定性输出；决策/抽取类任务用 0~0.3
                top_p=1.0,              # 核采样概率阈值，与 temperature 二选一调节即可，不要同时大调
                max_tokens=512,         # 本次回复允许生成的最大 token 数，防止长输出挤占预算
                frequency_penalty=0.0,  # 降低重复用词：>0 时越出现过的词越被压制，取值范围 -2.0~2.0
            )
        except APITimeoutError as exc:
            last_error = exc
            wait = 1.0 * (2 ** attempt)
            print(f"[超时] 第 {attempt + 1} 次失败，{wait:.1f}s 后重试")
        except RateLimitError as exc:
            last_error = exc
            wait = 2.0 * (2 ** attempt)
            print(f"[限流] 第 {attempt + 1} 次失败，{wait:.1f}s 后重试")
        except APIConnectionError as exc:
            last_error = exc
            wait = 1.0 * (2 ** attempt)
            print(f"[连接错误] 第 {attempt + 1} 次失败，{wait:.1f}s 后重试")
        time.sleep(wait)

    raise RuntimeError(f"调用多次重试后仍失败：{last_error}")


if __name__ == "__main__":
    response = create_chat_completion_with_retry(messages)
    print(response.choices[0].message.content)

    # usage 记录本次消耗的 token，工程化阶段靠它做成本统计与限流预算
    usage = response.usage
    print(f"\n[token 使用] 输入 {usage.prompt_tokens} / 输出 {usage.completion_tokens} / 合计 {usage.total_tokens}")
