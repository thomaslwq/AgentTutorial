"""第12章 · 人机协同：用 interrupt 在关键节点暂停，等人审批后再继续
前置：export OPENAI_API_KEY=sk-...
运行：python human_in_loop.py

流程：
  draft -> review(interrupt 暂停) -> send(根据审批结果决定是否真的"发送")
第一次 invoke 会在 review 节点停下，返回的是中断现场；
拿到人审批结果后，用 Command(resume=...) 从断点续跑。
"""
from typing import Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import interrupt, Command


class EmailState(dict):
    messages: Annotated[list[BaseMessage], add_messages]
    recipient: str
    subject: str
    body: str
    approved: bool | None  # None=待定，True/False=人审批结果


llm = ChatOpenAI(model="gpt-4o-mini", temperature=0)


def draft_node(state: EmailState) -> dict:
    """让 LLM 起草一封邮件。"""
    prompt = (
        "给客户写一封简短的售后跟进邮件，"
        "主题和正文用一两句话即可，语气礼貌专业。"
    )
    msg = llm.invoke([("system", prompt), ("user", state["messages"][0].content)])
    return {
        "recipient": "customer@example.com",
        "subject": "售后跟进",
        "body": msg.content,
        "approved": None,
    }


def review_node(state: EmailState) -> dict:
    """在这里 interrupt：把草稿抛给人看，等人回一个 approve/reject。"""
    decision = interrupt(
        {
            "to": state["recipient"],
            "subject": state["subject"],
            "body": state["body"],
            "question": "是否允许发送？回复 approve 或 reject。",
        }
    )
    # 第二次进来时，decision 就是人通过 Command(resume=...) 给的值
    return {"approved": decision == "approve"}


def send_node(state: EmailState) -> dict:
    """模拟发送：生产里这里才是真正发邮件的副作用。"""
    if not state["approved"]:
        return {"messages": [("ai", "已按审批结果取消发送。")]}
    return {"messages": [("ai", f"已发送给 {state['recipient']}。")]}


def route_after_review(state: EmailState) -> str:
    # 简单起见：审批完统一进入 send_node，由它内部判断发不发
    return "send"


builder = StateGraph(EmailState)
builder.add_node("draft", draft_node)
builder.add_node("review", review_node)
builder.add_node("send", send_node)

builder.add_edge(START, "draft")
builder.add_edge("draft", "review")
builder.add_conditional_edges("review", route_after_review, {"send": "send"})
builder.add_edge("send", END)

graph = builder.compile(checkpointer=MemorySaver())


if __name__ == "__main__":
    config = {"configurable": {"thread_id": "email-thread-1"}}

    print("=== 第一次运行：走到 review 会被 interrupt 暂停 ===")
    paused = graph.invoke(
        {"messages": [("user", "跟进上周的售后工单")]},
        config=config,
    )
    # 中断现场会挂在 __interrupt__ 字段里
    for item in paused.get("__interrupt__", []):
        print("待审批内容：", item.value)

    print("\n=== 人审批通过，用 Command(resume=...) 续跑 ===")
    final = graph.invoke(Command(resume="approve"), config=config)
    print(final["messages"][-1].content)
