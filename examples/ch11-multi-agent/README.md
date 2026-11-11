# ch11-multi-agent · 第 11 章配套示例

一个最小的 CrewAI 三角色流水线：研究员 → 文案 → 审稿人。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

> crewai 依赖较重（会拉 litellm、pydantic 等），建议新建虚拟环境安装。

## 运行

```bash
python crew_demo.py
```

预期输出：依次看到三个角色各自的产出，最后打印一段 200 字以内的短评。把 `topic` 改成你关心的任意主题即可复用。

## 这个 demo 想让你看到什么

1. **角色（Agent）**只声明 `role / goal / backstory`，不写控制流——控制流由 Task 之间的 `context` 决定。
2. **任务（Task）**用 `context=[t1]` 显式声明依赖，CrewAI 会按依赖顺序执行。
3. **流程（Crew + Process.sequential）**是最简单的顺序流水线；层级主管、辩论等模式在第 11 章正文里展开。

## 练习参考答案

### 练习 1：把 reviewer 改成"打回重写"

CrewAI 原生不支持自动重跑某个 Task，工程做法是：把 `t3` 拆成两步——先跑审稿，解析结果若是"打回"，把"打回原因"作为新输入再 `kickoff` 一次。这暴露出声明式框架的边界：复杂循环要回到代码控制（第 12 章 LangGraph）。

### 练习 2：让 researcher 用一个真实工具

给 `researcher` 配一个 `tools=[...]`（比如 `SerperDevTool` 或你自己封装的搜索函数），重新跑一遍。你会发现：工具越多，Planner/角色的 Prompt 越要收窄，否则模型会乱调。这正是"多 Agent 不等于多工具"的含义。

### 练习 3：换成 Process.hierarchical

把 `Process.sequential` 改成 `Process.hierarchical`，并给 Crew 设一个 `manager_llm`。你会看到主管角色自动决定下一步派给谁——灵活度上去了，但可预测性下降，调试成本明显变高。这就是正文里"层级主管"模式的权衡。
