"""第09章 · RAG 检索侧评测：命中率、召回率、MRR（纯标准库，不依赖 ragas）

运行：
    python rag_eval.py

说明：
    - 本脚本只算检索侧指标：召回是否命中、排得是否靠前；
    - 答案侧指标（忠实度、相关性）需要大模型参与评判，属于 RAGAS 一类框架的
      范围，本章正文讲解概念，工程接入留到第 13 章；
    - 数据集结构：每个用例给出问题、相关文档 id 集合、按相关度降序的召回 id 列表。
"""
from dataclasses import dataclass


@dataclass
class EvalCase:
    """一条评测用例。

    relevant_ids：标准答案对应的文档 id 集合（金标准）。
    retrieved_ids：检索器返回的文档 id，按相关度从高到低排序。
    """

    query: str
    relevant_ids: set[str]
    retrieved_ids: list[str]


def recall_at_k(case: EvalCase, k: int) -> float:
    """召回率@k：前 k 条里命中的相关文档占全部相关文档的比例。"""
    if not case.relevant_ids:
        return 0.0
    hit = len(set(case.retrieved_ids[:k]) & case.relevant_ids)
    return hit / len(case.relevant_ids)


def hit_at_k(cases: list[EvalCase], k: int) -> float:
    """命中率@k：前 k 条中至少命中一条相关文档的用例占比。"""
    if not cases:
        return 0.0
    hits = sum(
        1 for c in cases if set(c.retrieved_ids[:k]) & c.relevant_ids
    )
    return hits / len(cases)


def reciprocal_rank(case: EvalCase) -> float:
    """单条用例的倒数排名：第一条相关文档出现在第几位，取其倒数；未命中为 0。"""
    for rank, doc_id in enumerate(case.retrieved_ids, start=1):
        if doc_id in case.relevant_ids:
            return 1.0 / rank
    return 0.0


def mrr(cases: list[EvalCase]) -> float:
    """MRR（Mean Reciprocal Rank）：所有用例倒数排名的平均值。"""
    if not cases:
        return 0.0
    return sum(reciprocal_rank(c) for c in cases) / len(cases)


# 示例评测集：doc-1 ~ doc-5 为知识库文档 id，金标准由人工标注
SAMPLE_CASES: list[EvalCase] = [
    EvalCase(
        query="RAG 怎么降低模型幻觉？",
        relevant_ids={"doc-1", "doc-2"},
        retrieved_ids=["doc-1", "doc-3", "doc-2", "doc-4"],
    ),
    EvalCase(
        query="微调适合固化什么能力？",
        relevant_ids={"doc-3"},
        retrieved_ids=["doc-5", "doc-3", "doc-1"],
    ),
    EvalCase(
        query="向量数据库有哪些选型？",
        relevant_ids={"doc-4"},
        retrieved_ids=["doc-4", "doc-2", "doc-5"],
    ),
    EvalCase(
        query="退款多久到账？",
        relevant_ids={"doc-5"},
        retrieved_ids=["doc-2", "doc-1", "doc-5"],
    ),
    EvalCase(
        query="切分块太大有什么问题？",
        relevant_ids={"doc-2"},
        retrieved_ids=["doc-3", "doc-4", "doc-1"],  # 未命中相关文档
    ),
]


def main() -> None:
    cases = SAMPLE_CASES
    for k in (1, 3):
        print(f"Hit@{k}: {hit_at_k(cases, k):.3f}")
        print(f"Recall@{k}: {sum(recall_at_k(c, k) for c in cases) / len(cases):.3f}")
    print(f"MRR: {mrr(cases):.3f}")

    print("\n逐条明细：")
    for c in cases:
        print(
            f"  {c.query}  RR={reciprocal_rank(c):.3f}  "
            f"Recall@3={recall_at_k(c, 3):.2f}  召回={c.retrieved_ids}"
        )


if __name__ == "__main__":
    main()
