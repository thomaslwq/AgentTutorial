"""第03章 · 滑动窗口记忆：只保留最近 N 轮对话，按 token 预算淘汰最旧消息。

本脚本不调用模型，纯内存演示窗口管理逻辑；运行：python sliding_window.py
"""
from collections import deque

# 粗略换算：中文约 1.5 字符/token，这里按 3 字符/token 保守估算。
CHARS_PER_TOKEN = 3


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // CHARS_PER_TOKEN)


class SlidingWindowMemory:
    """短期窗口记忆。

    - system 消息常驻，不参与淘汰；
    - 历史消息按时间顺序入队，超出 token 预算时从队首（最旧）开始丢弃；
    - 预算以「输入侧可容纳的 token 数」为界，给模型回复留出 max_tokens 空间。
    """

    def __init__(self, system_prompt: str, max_window_tokens: int = 600):
        self.system_message = {"role": "system", "content": system_prompt}
        self.max_window_tokens = max_window_tokens
        self.history: deque[dict] = deque()

    def add(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content})
        self._evict()

    def _window_tokens(self) -> int:
        return sum(estimate_tokens(m["content"]) for m in self.history)

    def _evict(self) -> None:
        # 至少保留一对 user/assistant，避免把刚产生的上下文清空
        while len(self.history) > 2 and self._window_tokens() > self.max_window_tokens:
            removed = self.history.popleft()
            print(f"[淘汰] 丢弃最旧消息：{removed['role']}: {removed['content'][:20]}…")

    def messages(self) -> list[dict]:
        """组装发给模型的完整消息列表。"""
        return [self.system_message, *self.history]

    def __len__(self) -> int:
        return len(self.history)


if __name__ == "__main__":
    memory = SlidingWindowMemory(
        system_prompt="你是一个简洁的对话助手。",
        max_window_tokens=120,
    )

    dialog = [
        ("user", "我叫小林，在做一个电商后台。"),
        ("assistant", "你好小林，电商后台主要涉及商品、订单与库存模块。"),
        ("user", "订单状态机有哪些常见状态？"),
        ("assistant", "常见状态：待支付、已支付、待发货、已发货、已完成、已取消、退款中。"),
        ("user", "待支付超时一般怎么处理？"),
        ("assistant", "通常用定时任务或延迟队列关闭订单并释放库存。"),
        ("user", "再补充一下库存扣减的时机。"),
    ]

    for role, content in dialog:
        memory.add(role, content)

    print("\n[当前窗口消息]")
    for msg in memory.messages():
        print(f"- {msg['role']}: {msg['content']}")
    print(f"\n[窗口 token 估算] {memory._window_tokens()} / 预算 {memory.max_window_tokens}")
