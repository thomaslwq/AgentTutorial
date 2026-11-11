"""第08章 · 最小向量库：numpy 手写余弦相似度

前置：
    export OPENAI_API_KEY=sk-...   # 可选；未设置时退化为离线哈希向量，仅用于跑通流程
    # 兼容 OpenAI 协议的国产服务另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install -r requirements.txt
    python simple_vector_store.py

说明：
    - 向量库只用 numpy 矩阵 + 手写余弦相似度，目的是把「文本 → 向量 → 相似度排序
      → top-k」这条链路讲清楚；
    - 配置了 OPENAI_API_KEY 时走 text-embedding-3-small；未配置时使用离线哈希
      兜底向量，它不具备真实语义能力，仅保证脚本在无网环境也能跑通并验证排序逻辑；
    - 生产级向量库（Chroma / Qdrant / pgvector）的选型对比见本章正文。
"""
import hashlib
import os
import re
from dataclasses import dataclass, field

import numpy as np

EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
OFFLINE_DIM = 128  # 离线兜底向量维度；走 OpenAI 时维度由接口返回值决定

# 未配置 Key 时不初始化客户端，走离线兜底，保证脚本在无网环境也能跑通
_client = None
if os.getenv("OPENAI_API_KEY"):
    from openai import OpenAI

    _client = OpenAI()


def _stable_hash(token: str, dim: int) -> int:
    """对词元做稳定哈希，映射到向量维度上的一个槽位。"""
    digest = hashlib.md5(token.encode("utf-8")).hexdigest()
    return int(digest[:8], 16) % dim


def _offline_embed(text: str, dim: int = OFFLINE_DIM) -> np.ndarray:
    """离线兜底：词袋哈希向量。只做演示，不具备真实语义相似度能力。"""
    vec = np.zeros(dim, dtype=np.float32)
    for tok in re.findall(r"[a-z0-9]+|[一-鿿]", text.lower()):
        vec[_stable_hash(tok, dim)] += 1.0
    norm = np.linalg.norm(vec)
    return vec / norm if norm > 0 else vec


def embed_texts(texts: list[str]) -> np.ndarray:
    """批量向量化，返回 L2 归一化后的矩阵，形状 (n, dim)。"""
    if _client is not None:
        resp = _client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
        arr = np.array([item.embedding for item in resp.data], dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        norms[norms == 0] = 1.0  # 避免零向量除零
        return arr / norms
    return np.stack([_offline_embed(t) for t in texts])


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """批量余弦相似度；向量已归一化时，内积就是余弦相似度。"""
    return matrix @ query_vec


@dataclass
class VectorStore:
    """内存向量库：文档文本 + 向量矩阵，按余弦相似度做 top-k 检索。"""

    documents: list[str] = field(default_factory=list)
    vectors: np.ndarray | None = None

    def add(self, documents: list[str]) -> None:
        new_vecs = embed_texts(documents)
        self.documents.extend(documents)
        if self.vectors is None:
            self.vectors = new_vecs
        else:
            self.vectors = np.vstack([self.vectors, new_vecs])

    def search(self, query: str, top_k: int = 3) -> list[tuple[float, str]]:
        if self.vectors is None:
            return []
        query_vec = embed_texts([query])[0]
        scores = cosine_similarity(query_vec, self.vectors)
        top_k = min(top_k, len(self.documents))
        order = np.argsort(-scores)[:top_k]
        return [(float(scores[i]), self.documents[i]) for i in order]


SAMPLE_DOCS = [
    "RAG 在回答前先从知识库检索相关片段，再把片段拼进 Prompt 交给大模型生成答案。",
    "微调是在预训练模型基础上用领域数据继续训练，把领域表达与任务格式固化进参数。",
    "向量数据库支持按相似度检索，常见选型有 Chroma、Qdrant 和 PostgreSQL 的 pgvector 扩展。",
    "余弦相似度衡量两个向量方向的接近程度，取值范围在 -1 到 1 之间。",
]


def main() -> None:
    store = VectorStore()
    store.add(SAMPLE_DOCS)

    queries = [
        "怎么把外部资料接进大模型的回答里？",
        "有哪些存向量的数据库可选？",
        "微调适合用来做什么？",
    ]
    for q in queries:
        print(f"\n问题：{q}")
        for rank, (score, doc) in enumerate(store.search(q, top_k=3), start=1):
            print(f"  {rank}. [{score:.4f}] {doc}")


if __name__ == "__main__":
    main()
