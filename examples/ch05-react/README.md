# ch05-react · 第 05 章配套示例

手写经典 ReAct 循环（Thought / Action / Action Input / Observation / Final Answer），
用文本格式 + 正则解析实现，不使用原生 function calling。

## 文件

- `react_loop.py`：单文件实现——ReAct Prompt、正则解析、工具执行、循环主结构

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

## 运行

```bash
python react_loop.py
```

默认任务：「北京今天几度？上海今天几度？把两城的温差算出来。」

你会看到每一轮模型输出一段 Thought + Action + Action Input，程序执行后把
`Observation: ...` 拼回上下文，模型继续写下一段 Thought，直到输出
`Final Answer: ...`。

## 与第 04 章的对照

| | 第 04 章 | 本章 |
|---|---|---|
| 行动通道 | 原生 `tool_calls`（结构化） | 文本 `Action:` 行 + 正则 |
| 推理可见性 | 不可见 | 每段 `Thought:` 显式输出 |
| 格式稳定性 | SDK 保证 | 靠 Prompt + 失败回喂纠正 |

## 练习参考答案

### 练习 1：未知城市的处理

把任务改成「广州今天天气怎么样？」。模型第一次 `Action: get_weather`、
`Action Input: 广州`，程序回喂：

```
Observation: 未知城市 广州，支持：['北京', '上海']
```

下一轮模型应在 Thought 里承认查不到，然后直接给 `Final Answer` 说明情况，
而不是反复重试。如果它重试了同一个城市——这就是教材里「循环失控」的实例，
正好用练习 2 的检测器去拦。

### 练习 2：连续相同调用检测器

在 `run()` 里维护一个历史：

```python
history = []  # [(tool_name, args_str), ...]
...
key = (action_m.group(1), input_m.group(1).strip())
if len(history) >= 2 and history[-1] == key and history[-2] == key:
    return "（检测到连续重复调用同一动作，已终止）"
history.append(key)
```

命中即强制结束，避免模型在同一个工具上反复横跳烧 token。

### 练习 3：与 Function Calling 对比

同一个问题分别跑：

```bash
cd ../ch04-function-calling && python handrolled_loop.py
cd ../ch05-react && python react_loop.py
```

在两次调用之间临时加一行打印 `resp.usage`：

- Function Calling：总轮次通常 2–3 轮，token 主要花在工具调用的结构化字段上；
- ReAct：总轮次通常 3–5 轮，每轮都要把整段 Thought/Action/Observation 草稿
  重发一次，prompt token 显著高于 Function Calling，但你能从 trace 里直接读
  出「模型为什么这么调」。

结论：生产用 Function Calling，调试/研究/跨模型兼容时用 ReAct。
