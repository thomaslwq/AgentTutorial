"""第05章 · 手写 ReAct 循环（Thought / Action / Observation 范式）。

运行：
    export OPENAI_API_KEY=sk-...
    pip install -r requirements.txt
    python react_loop.py

与第04章的差别：这里不使用模型原生的 function calling，
而是靠 Prompt 把模型约束在「Thought/Action/Action Input/Observation」文本格式里，
让推理过程显式可见。这是 ReAct 论文（Yao et al., 2022）的经典做法。
"""
from __future__ import annotations

import ast
import json
import operator
import re

from openai import OpenAI

client = OpenAI()
MODEL = "gpt-4o-mini"

# ---------------------------------------------------------------- 工具

_MOCK_WEATHER = {
    "北京": {"temp_c": 8, "condition": "晴", "humidity": 30},
    "上海": {"temp_c": 14, "condition": "多云", "humidity": 65},
}


def get_weather(city: str) -> str:
    if city not in _MOCK_WEATHER:
        return f"未知城市 {city}，支持：{list(_MOCK_WEATHER)}"
    return json.dumps(_MOCK_WEATHER[city], ensure_ascii=False)


_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
}


def calculate(expression: str) -> str:
    def ev(n: ast.AST) -> float:
        if isinstance(n, ast.Constant):
            return n.value  # type: ignore[no-any-return]
        if isinstance(n, ast.BinOp) and type(n.op) in _BIN_OPS:
            return _BIN_OPS[type(n.op)](ev(n.left), ev(n.right))
        raise ValueError("不支持的表达式")

    return str(ev(ast.parse(expression, mode="eval").body))


TOOLS = {"get_weather": get_weather, "calculate": calculate}

# ---------------------------------------------------------------- Prompt

REACT_TEMPLATE = """你必须严格按下面的格式推进任务，每一段都以指定前缀开头：

Question: 用户的问题
Thought: 你此刻的思考——要解决什么、下一步该做什么
Action: {tool_names} 之一（只写工具名）
Action Input: 传给该动作的参数（get_weather 给城市名；calculate 给算术表达式）
Observation: （系统填回，你不要自己写这一行）
...（重复 Thought / Action / Action Input / Observation）...
Thought: 我已经掌握全部需要的信息
Final Answer: 面向用户的中文最终答案

硬性规则：
1. 每一轮只允许一个 Action；
2. 不要在 Thought 里编造 Observation；
3. 一旦写出 Final Answer，整个流程结束，不要再调工具；
4. 如果上一轮 Observation 显示出错，先在 Thought 里分析原因，再决定下一步。

Begin!
Question: {question}
"""

ACTION_RE = re.compile(r"^Action:\s*([\w_]+)\s*$", re.MULTILINE)
INPUT_RE = re.compile(r"^Action Input:\s*(.+?)\s*$", re.MULTILINE)
FINAL_RE = re.compile(r"^Final Answer:\s*(.+)$", re.MULTILINE)


def execute_action(name: str, action_input: str) -> str:
    fn = TOOLS.get(name)
    if fn is None:
        return f"[错误] 未知动作 {name}，可用动作：{list(TOOLS)}"
    try:
        return fn(action_input.strip().strip('"'))
    except Exception as e:  # noqa: BLE001
        return f"[异常] {type(e).__name__}: {e}"


def run(user_question: str, max_turns: int = 6) -> str:
    prompt = REACT_TEMPLATE.format(
        tool_names=", ".join(TOOLS), question=user_question,
    )
    # 整段 ReAct 草稿作为一条 user 消息起点；
    # 模型后续每一轮输出与系统填入的 Observation 都追加进 messages。
    messages = [
        {"role": "system", "content": "你是一个严谨、克制的助手，严格遵守给定格式。"},
        {"role": "user", "content": prompt},
    ]

    for turn in range(1, max_turns + 1):
        resp = client.chat.completions.create(
            model=MODEL, messages=messages, temperature=0,
        )
        text = resp.choices[0].message.content or ""
        print(f"\n=== 第 {turn} 轮模型输出 ===\n{text}")

        final = FINAL_RE.search(text)
        if final:
            return final.group(1).strip()

        action_m = ACTION_RE.search(text)
        input_m = INPUT_RE.search(text)
        messages.append({"role": "assistant", "content": text})

        if not action_m or not input_m:
            # 格式跑偏：把错误作为 user 消息回喂，给模型一次自我纠正机会
            messages.append({
                "role": "user",
                "content": "格式错误：这一轮必须包含一行 'Action: 工具名' 与一行 "
                           "'Action Input: 参数'，或者给出 'Final Answer: ...'。"
                           "请基于上一个 Observation 重新输出。",
            })
            continue

        observation = execute_action(action_m.group(1), input_m.group(1))
        print(f"Observation: {observation}")
        # 关键：Observation 作为下一条 user 消息回到上下文，
        # 模型会接着写下一个 Thought。
        messages.append({"role": "user", "content": f"Observation: {observation}"})

    return "（达到最大轮次，模型未给出 Final Answer，已终止）"


if __name__ == "__main__":
    q = "北京今天几度？上海今天几度？把两城的温差算出来。"
    print("问题：", q)
    print("\n最终答案：", run(q))
