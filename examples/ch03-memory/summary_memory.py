"""第03章 · 摘要压缩记忆：旧对话交给 LLM 总结成摘要，只保留摘要 + 最近若干轮。

前置：export OPENAI_API_KEY=sk-你的key
运行：python summary_memory.py
"""
from collections import deque

from openai import OpenAI

client = OpenAI()

MODEL = "gpt-4o-mini"

SUMMARY_PROMPT = (
    "下面是一段已有对话摘要和一批新的对话记录。请合并成一段简洁的中文摘要，"
    "保留：用户身份与目标、已确认的关键事实、待办事项；删除寒暄与重复细节。\n\n"
    "已有摘要：{existing_summary}\n\n"
    "新对话记录：\n{new_history}\n\n"
    "合并后的摘要："
)


class SummaryMemory:
    """摘要记忆（压缩型短期记忆）。

    结构：一段跨轮次的摘要 + 一个有限长度的近期窗口。
    当近期窗口超过阈值，就把窗口内容连同旧摘要一起交给模型重新总结，
    用一次额外的模型调用换取上下文长度的可控。
    """

    def __init__(
        self,
        system_prompt: str,
        max_recent: int = 4,
        model: str = MODEL,
    ):
        self.system_prompt = system_prompt
        self.max_recent = max_recent
        self.model = model
        self.summary = ""
        self.recent: deque[dict] = deque()

    def add(self, role: str, content: str) -> None:
        self.recent.append({"role": role, "content": content})
        if len(self.recent) > self.max_recent:
            self._compress()

    def _compress(self) -> None:
        history_text = "\n".join(
            f"{m['role']}: {m['content']}" for m in self.recent
        )
        resp = client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "user",
                    "content": SUMMARY_PROMPT.format(
                        existing_summary=self.summary or "（暂无）",
                        new_history=history_text,
                    ),
                }
            ],
            temperature=0,
        )
        self.summary = resp.choices[0].message.content or ""
        self.recent.clear()
        print(f"[压缩] 近期 {self.max_recent + 1} 条记录已并入摘要。")

    def messages(self) -> list[dict]:
        msgs = [{"role": "system", "content": self.system_prompt}]
        if self.summary:
            msgs.append({"role": "system", "content": f"历史对话摘要：{self.summary}"})
        msgs.extend(self.recent)
        return msgs

    def dump(self) -> dict:
        return {"summary": self.summary, "recent": list(self.recent)}


if __name__ == "__main__":
    memory = SummaryMemory(
        system_prompt="你是一个项目助手，回答时记住用户已确认的结论。",
        max_recent=4,
    )

    dialog = [
        ("user", "我们要给电商后台做订单模块，负责人是小林。"),
        ("assistant", "已记录：订单模块，负责人小林。"),
        ("user", "订单状态机先支持待支付、已支付、已发货、已完成。"),
        ("assistant", "状态机四个初始状态已记录。"),
        ("user", "待支付超时 15 分钟自动关单并释放库存。"),
        ("assistant", "超时关单与库存释放规则已记录。"),
        ("user", "退款流程先做人工审核，不自动退款。"),
    ]

    for role, content in dialog:
        memory.add(role, content)

    print("\n[组装后的消息列表]")
    for msg in memory.messages():
        print(f"- {msg['role']}: {msg['content']}")
