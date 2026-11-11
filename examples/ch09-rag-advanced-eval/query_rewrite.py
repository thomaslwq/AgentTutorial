"""第09章 · 查询改写：改写、多查询扩展、HyDE、子问题分解

前置：
    export OPENAI_API_KEY=sk-...   # 可选；未配置时各函数返回离线兜底结果
    # 兼容 OpenAI 协议的国产服务另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install -r requirements.txt
    python query_rewrite.py

说明：
    - rewrite_query：去除口语与冗余、补全指代，得到规范检索式；
    - expand_multi_query：把一个问题扩成多条同义查询，分别召回后合并结果；
    - hyde：先让模型生成一段假设性答案，用答案文本（而非问题）去做向量检索；
    - decompose_subquestions：把复杂问题拆成可独立检索的子问题，逐个回答后汇总。
    - 未配置 Key 时返回原始查询兜底，仅用于跑通控制流；生产环境以线上模型为准。
"""
import json
import os

MODEL = os.getenv("RAG_CHAT_MODEL", "gpt-4o-mini")

_client = None
if os.getenv("OPENAI_API_KEY"):
    from openai import OpenAI

    _client = OpenAI()


def _chat(system: str, user: str) -> str:
    resp = _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=0.0,
    )
    return resp.choices[0].message.content or ""


def _load_json(text: str, fallback: dict) -> dict:
    try:
        parsed = json.loads(text)
        return parsed if isinstance(parsed, dict) else fallback
    except json.JSONDecodeError:
        return fallback


def rewrite_query(query: str) -> str:
    """规范改写：去口语、补指代，保留核心实体。"""
    if _client is None:
        return query
    system = (
        "把用户问题改写为一条规范、可检索的查询：去除口语与冗余，补全省略的指代，"
        "保留核心实体与限定条件。只输出改写后的查询，不要解释。"
    )
    return _chat(system, query).strip()


def expand_multi_query(query: str, n: int = 3) -> list[str]:
    """多查询扩展：同一意图的多种表述，分别召回后合并去重。"""
    fallback = [query]
    if _client is None:
        return fallback
    system = (
        f"围绕用户问题生成 {n} 条表述不同但意图相同的检索查询，覆盖同义说法与不同侧重。"
        '输出 JSON 对象：{"queries": ["...", "..."]}。'
    )
    data = _load_json(_chat(system, query), {})
    queries = data.get("queries")
    return queries if isinstance(queries, list) and queries else fallback


def hyde(query: str) -> str:
    """HyDE：生成假设性参考答案，用这段文本参与向量检索。"""
    if _client is None:
        return query
    system = (
        "你是一名知识库助手。针对用户问题，先写一段简短的假设性参考答案，"
        "即使细节不确定也按最合理的方式写出；这段文本将用于向量检索。直接输出答案文本。"
    )
    return _chat(system, query).strip()


def decompose_subquestions(query: str) -> list[str]:
    """子问题分解：复杂问题拆成可独立检索回答的子问题。"""
    fallback = [query]
    if _client is None:
        return fallback
    system = (
        "把复杂问题拆成若干个可独立检索回答的子问题，按回答顺序排列。"
        '输出 JSON 对象：{"subquestions": ["...", "..."]}。'
    )
    data = _load_json(_chat(system, query), {})
    subs = data.get("subquestions")
    return subs if isinstance(subs, list) and subs else fallback


def main() -> None:
    question = "我们公司的差旅报销需要哪些审批步骤，发票有什么要求？"
    print("原始问题：", question)
    print("规范改写：", rewrite_query(question))
    print("多查询扩展：", expand_multi_query(question))
    print("HyDE 假设答案：", hyde(question))
    print("子问题分解：", decompose_subquestions(question))


if __name__ == "__main__":
    main()
