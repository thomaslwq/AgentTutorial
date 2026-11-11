"""第10章 · Plan-and-Execute 手写循环

流程：Planner 先把目标拆成有序步骤；Executor 逐步执行；
每步执行完由 Reviser 依据观察结果决定是否调整剩余计划。
这里 Executor 暂时用一次 LLM 调用充当"干活的人"，便于跑通控制流；
真实项目里 Executor 应替换为一组工具（搜索、写文件、调 API）。

前置：
    export OPENAI_API_KEY=sk-...
    # 兼容 OpenAI 协议的服务另设：export OPENAI_BASE_URL=https://.../v1
运行：
    pip install -r requirements.txt
    python plan_execute.py
"""
import json
from openai import OpenAI

client = OpenAI()

PLANNER_PROMPT = (
    "你是任务规划器。把用户目标拆成 3-6 个有序、可执行的原子步骤。\n"
    "只输出 JSON：{\"steps\": [\"步骤1\", \"步骤2\", ...]}。\n"
    "每一步必须能被执行器独立完成，不要写『做整体评估』这种含糊步骤。"
)

REVISER_PROMPT = (
    "你是计划修订器。已知：\n"
    "- 原计划剩余步骤：{remaining}\n"
    "- 上一步执行结果（观察）：{observation}\n"
    "判断是否需要调整剩余计划（增删、改顺序、合并）。\n"
    "只输出 JSON：{\"steps\": [\"调整后的剩余步骤...\"]}；若无需调整，原样返回。"
)


def plan(goal: str) -> list[str]:
    """Planner：一次性产出初始计划。"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": PLANNER_PROMPT},
            {"role": "user", "content": goal},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)["steps"]


def execute(step: str) -> str:
    """Executor：真实项目里这里是一组工具；本示例用一次 LLM 调用顶替。"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": f"请用一句话完成这一步：{step}"}],
        temperature=0.3,
    )
    return resp.choices[0].message.content.strip()


def revise(remaining: list[str], observation: str) -> list[str]:
    """Reviser：基于上一步的观察，决定剩余计划要不要改。"""
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": REVISER_PROMPT.format(
                remaining=json.dumps(remaining, ensure_ascii=False),
                observation=observation,
            ),
        }],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return json.loads(resp.choices[0].message.content)["steps"]


def run(goal: str, max_rounds: int = 8) -> str:
    steps = plan(goal)
    print("== 初始计划 ==")
    for i, s in enumerate(steps, 1):
        print(f"  {i}. {s}")

    final_obs = ""
    rounds = 0
    while steps and rounds < max_rounds:
        rounds += 1
        step = steps.pop(0)
        print(f"\n== 第{rounds}轮执行：{step} ==")
        obs = execute(step)
        print(f"  观察：{obs}")
        final_obs = obs

        if steps:
            steps = revise(steps, obs)
            print(f"  修订后剩余：{steps}")

    if not steps:
        print("\n== 计划已全部完成 ==")
    else:
        print(f"\n== 达到 max_rounds={max_rounds}，提前退出 ==")
    return final_obs


if __name__ == "__main__":
    run("为一个开源 CLI 工具写一段 200 字的英文发布说明，并列出三个卖点。")
