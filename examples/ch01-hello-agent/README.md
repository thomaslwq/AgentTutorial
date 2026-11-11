# ch01-hello-agent · 第 01 章配套示例

两个最小脚本，分别对应「一次调用」与「Agent 循环骨架」。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

## 运行

```bash
python hello_llm.py        # 一次调用：看 messages 结构与 token usage
python agent_skeleton.py   # 循环骨架：看决策-执行-观察的控制流
```

> `agent_skeleton.py` 的工具是伪实现，且依赖 Prompt 硬约束 JSON，仅用于理解循环；
> 生产协议见第 04 章 Function Calling。

## 练习参考答案

### 练习 1：观察 temperature 的影响
把 `hello_llm.py` 的 `temperature` 改为 0（每次几乎相同）与 1（发散），同一问题连问三次：
`temperature=0` 回答高度一致，`temperature=1` 措辞与细节开始发散。这说明低温更适合需要稳定、可复现行为的 Agent 决策。

### 练习 2：新增 calculate 伪工具
在 `TOOLS` 中注册：

```python
import ast

def _safe_eval(expr: str):
    # 仅练习用：生产环境严禁直接 eval 用户/模型输入
    return eval(expr, {"__builtins__": {}}, {})

TOOLS["calculate"] = lambda args: str(_safe_eval(args["expression"]))
```

并在 SYSTEM_PROMPT 的可用工具列表中加上 `calculate`。模型在遇到算式时会先 `action` 调 `calculate`，拿到结果后再 `final` 回答。

### 练习 3：需求辨析参考判断标准
问自己：任务路径是否需要「根据外部反馈临场决定下一步」？是 → 可考虑 Agent；
只是固定流程或单轮问答 → 普通程序 / 单次调用即可。
