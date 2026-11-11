"""第01章 · Agent 循环骨架（伪工具演示控制流，真实工具协议见第04章）

演示：感知-决策-行动-观察 的循环结构。模型每次只输出 JSON 决策：
    {"type": "final", "answer": "..."}                 -> 结束
    {"type": "action", "tool": "工具名", "args": {...}} -> 执行工具并回喂结果

运行：
    pip install -r requirements.txt
    python agent_skeleton.py
"""
import json

from openai import OpenAI

client = OpenAI()

# 伪工具注册表：工具名 -> 处理函数。第04章将替换为原生 Function Calling。
TOOLS = {
    "get_time": lambda _args: "现在是 2026-11-10 周二 上午。",
}

SYSTEM_PROMPT = (
    "你是一个助手。每次回复必须只输出一个 JSON 对象：\n"
    '{"type": "final", "answer": "..."} 表示直接回答并结束；\n'
    '{"type": "action", "tool": "工具名", "args": {...}} 表示要调用工具。\n'
    f"可用工具：{list(TOOLS.keys())}。"
)


def run_agent(user_task: str, max_turns: int = 5) -> str:
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_task},
    ]

    for turn in range(max_turns):
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        raw = resp.choices[0].message.content
        messages.append({"role": "assistant", "content": raw})

        decision = json.loads(raw)
        if decision["type"] == "final":
            return decision["answer"]  # 决策完成 -> 退出循环

        # 决策为 action：程序执行工具，把观察结果回喂模型，进入下一轮
        tool_name = decision["tool"]
        observation = TOOLS[tool_name](decision.get("args", {}))
        print(f"[第{turn + 1}轮] 调用 {tool_name}，观察结果：{observation}")
        messages.append({
            "role": "user",
            "content": f"工具返回：{observation}，请继续推进任务。",
        })

    return "达到最大轮次仍未完成。"


if __name__ == "__main__":
    print(run_agent("现在几点？告诉我，然后一句话总结它。"))
