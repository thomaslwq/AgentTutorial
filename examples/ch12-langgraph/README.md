# ch12-langgraph · 第 12 章配套示例

两个最小脚本，分别对应「手写 StateGraph 带工具调用」和「interrupt 人机审批」。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

> langgraph 会拉 langchain-core、langchain-openai 等依赖，建议新建虚拟环境。
> 模型默认 `gpt-4o-mini`，可在脚本里改成任意兼容 OpenAI 协议的模型名。

## 运行

```bash
python state_graph.py       # 手写状态图 + MemorySaver，演示两轮对话上下文连续
python human_in_loop.py     # interrupt 暂停 → Command(resume=...) 续跑
```

### 预期输出

- `state_graph.py`：第一轮问北京天气时模型会调 `get_weather` 工具；第二轮只说「上海呢」，因为同一 `thread_id` 的 checkpoint 保留了上一轮消息，模型能直接定位城市。
- `human_in_loop.py`：第一次 `invoke` 返回值里带 `__interrupt__` 字段，打印出草稿邮件；第二次用 `Command(resume="approve")` 续跑，最后输出「已发送给 customer@example.com」。

## 这个 demo 想让你看到什么

1. **State 是字典**：节点之间不直接传参，而是读写同一个 state；字段用 `Annotated[list, add_messages]` 声明 reducer，新消息自动追加。
2. **节点是普通函数**：`agent_node` 接收 state、返回一个字典（要更新的字段），LangGraph 负责合并。
3. **边决定控制流**：`add_conditional_edges("agent", tools_condition)` 这一行等价于第 01 章骨架里的「看模型要不要调工具」分支。
4. **checkpointer 让状态可中断、可恢复**：换 `MemorySaver` 为 `SqliteSaver`（需要额外装 `langgraph-checkpoint-sqlite`）就能把状态落盘，进程重启后按 `thread_id` 接着跑。

## 练习参考答案

### 练习 1：给 state_graph.py 再加一个工具

在 `TOOLS` 里用 `@tool` 装饰一个 `calculator(expression: str)`，内部用 `ast.literal_eval` 或简单安全求值返回结果。把它加进 `ToolNode(TOOLS)` 的列表即可——不需要改任何边，因为 `tools_condition` 只关心「模型是否在请求工具调用」，工具数量对控制流透明。

### 练习 2：把 MemorySaver 换成 SqliteSaver

```python
# pip install langgraph-checkpoint-sqlite
from langgraph.checkpoint.sqlite import SqliteSaver
import sqlite3

conn = sqlite3.connect("checkpoints.db", check_same_thread=False)
graph = builder.compile(checkpointer=SqliteSaver(conn))
```

跑完一次后退出进程，再次运行同一个脚本、用同一个 `thread_id`，第二轮对话依然能接上。这就是 checkpoint 落盘的意义：Agent 可以跨进程、跨部署实例恢复。

### 练习 3：在 human_in_loop.py 里演示「驳回重写」

把 `Command(resume="approve")` 改成 `Command(resume="reject")`，并在 `draft_node` 里读 `state.get("approved")`：如果是 `False`，把「人驳回的原因」追加进 messages，再让 LLM 重写一遍。你会发现：审批不只是一个布尔值，它本身就是下一轮推理的输入——这正是 interrupt 比「在代码里写个 input()」强的地方。
