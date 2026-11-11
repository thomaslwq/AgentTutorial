# ch10-planning-reflection · 第 10 章配套示例

两个最小脚本，分别对应 Plan-and-Execute 与 Reflection/Reflexion 两种控制流。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

## 运行

```bash
python plan_execute.py       # 看 Planner/Executor/Reviser 三段分工
python reflection_loop.py    # 看 草稿 → 审稿 → 重写 的一轮闭环
```

预期输出：

- `plan_execute.py` 先打印一份初始计划（3-6 步），然后逐步打印"执行→观察→修订剩余计划"，最后退出。
- `reflection_loop.py` 依次打印草稿、JSON 审稿意见（含三维打分）、重写版本。

> 两个脚本都依赖 Prompt 硬约束 JSON，仅用于讲清控制流；生产做法见第 04 章 Function Calling 与第 12 章 LangGraph。

## 练习参考答案

### 练习 1：给 Plan-and-Execute 加预算上限

在 `run()` 里加一个 `token_budget` 参数：每轮执行后累加 `resp.usage.total_tokens`，超过预算立即停止并返回当前结果。要点是把"轮次上限"换成"成本上限"，对应工程里的真实约束（第 13 章成本治理）。

### 练习 2：让 Critic 决定是否重写

把 `reflection_loop.py` 末尾固定重写改成：解析 `critique` 返回的 JSON，若 `verdict == "pass"` 直接输出草稿，否则调用 `revise()`。进一步可以循环"重写→再审稿"直到 `pass` 或达到最大轮次——这就是 Reflexion 论文的基本形态。

### 练习 3：给 Executor 接一个真实工具

把 `execute()` 从"一次 LLM 调用"替换成一个具体工具，比如 `search_web(query)`（调一次搜索 API）。你会发现 Planner 输出的步骤粒度通常需要调 Prompt 才能对齐工具参数——这正是真实项目里 80% 的工作量。
