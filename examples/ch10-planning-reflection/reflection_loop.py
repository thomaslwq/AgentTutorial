"""第10章 · Reflection / Reflexion：产出 → 自评 → 重写一轮

演示三段式：Writer 出草稿 → Critic 按维度打分并指出问题 → Reviser 按意见重写。
实际工程中"是否重写"应由 Critic 的 verdict 决定，本示例固定重写一次。

前置：
    export OPENAI_API_KEY=sk-...
运行：
    pip install -r requirements.txt
    python reflection_loop.py
"""
from openai import OpenAI

client = OpenAI()

WRITE_PROMPT = (
    "你是一名技术写作者。请用 120 字以内回答用户问题，给出清晰结论，不要绕弯。"
)

CRITIQUE_INSTRUCTION = (
    "你是严格的审稿人。针对下面这段草稿，从三个维度打分（1-5）并指出问题：\n"
    "1. 事实准确性\n"
    "2. 结构清晰度\n"
    "3. 是否直接回答了用户问题\n"
    "只输出 JSON：{\"scores\": {\"fact\": n, \"structure\": n, \"on_topic\": n},"
    " \"issues\": [\"问题1\", ...], \"verdict\": \"pass/rewrite\"}"
)

REVISE_PROMPT = (
    "请根据审稿意见重写草稿，保持 120 字以内，直接回答问题。\n"
    "用户问题：{question}\n"
    "原草稿：{draft}\n"
    "审稿意见：{critique}"
)


def draft(question: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": WRITE_PROMPT},
            {"role": "user", "content": question},
        ],
        temperature=0.7,
    )
    return resp.choices[0].message.content.strip()


def critique(question: str, draft_text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": CRITIQUE_INSTRUCTION},
            {"role": "user", "content": f"问题：{question}\n草稿：{draft_text}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,
    )
    return resp.choices[0].message.content


def revise(question: str, draft_text: str, critique_text: str) -> str:
    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{
            "role": "user",
            "content": REVISE_PROMPT.format(
                question=question, draft=draft_text, critique=critique_text,
            ),
        }],
        temperature=0.5,
    )
    return resp.choices[0].message.content.strip()


if __name__ == "__main__":
    q = "RAG 相比微调大模型，在什么场景下更划算？"
    d = draft(q)
    c = critique(q, d)
    f = revise(q, d, c)

    print("【草稿】\n" + d)
    print("\n【审稿】\n" + c)
    print("\n【重写】\n" + f)
