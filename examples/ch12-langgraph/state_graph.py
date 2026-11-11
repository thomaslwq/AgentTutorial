"""第12章 · 手写 StateGraph：带工具调用的 ReAct 循环
前置：export OPENAI_API_KEY=sk-... （兼容服务另设 OPENAI_BASE_URL）
运行：pip install -r requirements.txt && python state_graph.py

这个脚本做两件事：
1. 不用 create_react_agent，亲手把 StateGraph 拼出来，看清每一个节点和边；
2. 挂上 MemorySaver，演示同一 thread_id 下状态会被持久化（第二次提问能接上上下文）。
"""
from typing import Annotated

from langchain_openai import ChatOpenAI
from langchain_core.messages import BaseMessage
from langchain_core.tools import tool
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.checkpoint.memory import MemorySaver


# ---------- 1. State：图在节点之间流转的数据结构 ----------
class AgentState(dict):
    """messages 用 add_messages 做 reducer：节点返回新消息时不是覆盖，而是追加。"""
    messages: Annotated[list[BaseMessage], add_messages]


# ---------- 2. 工具：一个可被模型调用的真实函数 ----------
@tool
def get_weather(city: str) -> str:
    """查询某城市当前天气。这里返回的是假数据，生产里换成真实天气 API。"""
    fake = {"北京": "晴，8°C", "上海": "多云，12°C", "深圳": "小雨，20°C"}
    return fake.get(city, f"没有 {city} 的天气数据。")


TOOLS = [get_weather]


# ---------- 3. 节点：每个节点是一个接收 state、返回 state 分片的函数 ----------
model = ChatOpenAI(model="gpt-4o-mini", temperature=0).bind_tools(TOOLS)


def agent_node(state: AgentState) -> dict:
    """调用 LLM。返回值会被 reducer 合并进 state。"""
    response = model.invoke(state["messages"])
    return {"messages": [response]}


# ---------- 4. 组装图 ----------
builder = StateGraph(AgentState)
builder.add_node("agent", agent_node)
builder.add_node("tools", ToolNode(TOOLS))

# 入口：从 START 进入 agent 节点
builder.add_edge(START, "agent")

# 条件边：agent 看完模型返回，决定下一步——
# 模型要求调工具就去 tools 节点，否则直接结束（END）
builder.add_conditional_edges("agent", tools_condition)

# 工具执行完，回到 agent 让模型基于观察结果继续推理
builder.add_edge("tools", "agent")

# checkpointer：把每次节点执行后的 state 存起来，按 thread_id 隔离
graph = builder.compile(checkpointer=MemorySaver())


# ---------- 5. 跑两次，演示状态持久化 ----------
if __name__ == "__main__":
    # thread_id 是会话的唯一标识；同一 thread_id 会复用同一份 checkpoint
    config = {"configurable": {"thread_id": "demo-thread-1"}}

    print("=== 第一轮：问天气 ===")
    result1 = graph.invoke(
        {"messages": [("user", "北京今天天气怎么样？")]},
        config=config,
    )
    print(result1["messages"][-1].content)

    print("\n=== 第二轮：不告诉城市，看它是否记得上文 ===")
    result2 = graph.invoke(
        {"messages": [("user", "那上海呢？")]},
        config=config,  # 同一个 thread_id，checkpoint 把第一轮的消息全带回来了
    )
    print(result2["messages"][-1].content)
