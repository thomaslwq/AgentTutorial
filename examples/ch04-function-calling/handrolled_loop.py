"""第04章 · 手写 Function Calling 工具循环（不依赖 LangChain）。

运行：
    export OPENAI_API_KEY=sk-...
    pip install -r requirements.txt
    python handrolled_loop.py

你会看到：模型先发起一次 get_weather 调用（并行两个城市），
观察回来后再发起一次 calculate，最后给出最终回答。
"""
from __future__ import annotations

import json

from openai import OpenAI

from tools import TOOLS, dispatch

client = OpenAI()  # 自动读 OPENAI_API_KEY / OPENAI_BASE_URL
MODEL = "gpt-4o-mini"  # 可换成任何兼容 OpenAI 协议的模型

SYSTEM = (
    "你是一个能使用工具的助手。遇到天气、算术等需要外部信息或精确计算的问题，"
    "必须先调用工具，拿到结果后再用中文回答用户；不要编造天气数字，也不要心算数值。"
)


def run(user_message: str, max_turns: int = 6) -> str:
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_message},
    ]
    tool_schemas = [entry["schema"] for entry in TOOLS.values()]

    for turn in range(1, max_turns + 1):
        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=tool_schemas,   # 把工具清单告诉模型
            tool_choice="auto",   # auto=模型自己决定要不要调；也可强制 required/特定函数
            temperature=0,
        )
        msg = resp.choices[0].message

        # 把助手这一轮（可能含 tool_calls）原样追加回历史，
        # 否则下一次请求模型会忘记自己刚才要调什么。
        messages.append(msg.model_dump(exclude_none=True))

        if not msg.tool_calls:
            # 没有工具调用 = 模型认为任务完成，直接结束循环
            return msg.content or ""

        print(f"--- 第 {turn} 轮：模型发起 {len(msg.tool_calls)} 个工具调用 ---")
        # 注意：一次响应里 tool_calls 可能是多个（并行工具调用）
        for tc in msg.tool_calls:
            name = tc.function.name
            try:
                args = json.loads(tc.function.arguments or "{}")
            except json.JSONDecodeError:
                args = {}
            print(f"  调用 {name}({args})")

            observation = dispatch(name, args)
            print(f"  观察：{observation}")

            # 每个 tool_call 必须配一条 role=tool 消息，
            # 且 tool_call_id 与上面的 tc.id 一一对应，否则模型报错。
            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": observation,
            })

    return "（达到最大轮次仍未完成，已强制终止）"


if __name__ == "__main__":
    task = "北京和上海今天的天气如何？把两地温差算出来，用摄氏度回答我。"
    print("用户：", task)
    print("助手：", run(task))
