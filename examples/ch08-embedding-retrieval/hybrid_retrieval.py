"""第08章 · 混合检索：BM25 关键词召回 + 向量语义召回，RRF 分数融合

前置：
    export OPENAI_API_KEY=sk-...   # 可选；未配置时向量侧走离线哈希兜底
    # 兼容 OpenAI 协议的国产服务另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install -r requirements.txt
    python hybrid_retrieval.py

说明：
    - BM25 负责精确词项匹配（型号、编号、专有名词），向量检索负责语义近义匹配；
    - 两路分数量纲不同（BM25 是加权词频分，向量是余弦相似度），不直接相加，
      而是用 RRF（Reciprocal Rank Fusion，倒数排名融合）按排名融合；
    - 交叉编码器重排（rerank）在本章正文讲解，本示例只做到两路召回 + 融合。
"""
import re

import numpy as np

from simple_vector_store import VectorStore

TOP_K = 5
RECALL_K = 10  # 每路先各召回多少条，再融合截断
RRF_K = 60  # RRF 平滑常数，取值越大排名差异被拉得越平


def tokenize(text: str) -> list[str]:
    """中英文混合切分：英文/数字按词，中文按单字。"""
    return re.findall(r"[a-z0-9]+|[一-鿿]", text.lower())


class BM25:
    """轻量 BM25 关键词检索器：词项精确匹配，带 IDF 与长度归一化。"""

    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.docs = docs
        self.k1 = k1
        self.b = b
        self.tokens = [tokenize(d) for d in docs]
        self.doc_len = [len(t) for t in self.tokens]
        self.avgdl = sum(self.doc_len) / max(1, len(self.doc_len))
        self.n = len(docs)

        # 文档频率：每个词项出现在多少篇文档中
        df: dict[str, int] = {}
        for toks in self.tokens:
            for tok in set(toks):
                df[tok] = df.get(tok, 0) + 1
        self.idf = {
            tok: np.log(1 + (self.n - cnt + 0.5) / (cnt + 0.5))
            for tok, cnt in df.items()
        }
        # 每篇文档内部的词频
        self.tf: list[dict[str, int]] = []
        for toks in self.tokens:
            freq: dict[str, int] = {}
            for tok in toks:
                freq[tok] = freq.get(tok, 0) + 1
            self.tf.append(freq)

    def score(self, query: str) -> np.ndarray:
        q_tokens = tokenize(query)
        scores = np.zeros(self.n, dtype=np.float64)
        for i, freq in enumerate(self.tf):
            dl = self.doc_len[i]
            length_norm = self.k1 * (1 - self.b + self.b * dl / self.avgdl)
            total = 0.0
            for tok in q_tokens:
                if tok not in freq:
                    continue
                tf = freq[tok]
                idf = self.idf.get(tok, 0.0)
                total += idf * tf * (self.k1 + 1) / (tf + length_norm)
            scores[i] = total
        return scores

    def rank(self, query: str, top_k: int) -> list[int]:
        scores = self.score(query)
        order = np.argsort(-scores)[:top_k]
        return [int(i) for i in order]


def rrf_fuse(rank_lists: list[list[int]], n: int, k: int = RRF_K) -> np.ndarray:
    """RRF：每路召回按排名给分，排名越靠前贡献越大；不依赖原始分数量纲。"""
    scores = np.zeros(n, dtype=np.float64)
    for ranks in rank_lists:
        for rank, idx in enumerate(ranks):
            scores[idx] += 1.0 / (k + rank + 1)
    return scores


class HybridRetriever:
    """关键词 + 向量两路召回，RRF 融合后返回 top-k。"""

    def __init__(self, docs: list[str], top_k: int = TOP_K, recall_k: int = RECALL_K):
        self.docs = docs
        self.top_k = top_k
        self.recall_k = recall_k
        self.bm25 = BM25(docs)
        self.store = VectorStore()
        self.store.add(docs)

    def retrieve(self, query: str) -> list[tuple[float, str]]:
        # 向量路：余弦相似度召回
        vector_hits = self.store.search(query, top_k=self.recall_k)
        vector_ranks = [self.docs.index(doc) for _, doc in vector_hits]

        # 关键词路：BM25 召回
        bm25_ranks = self.bm25.rank(query, top_k=self.recall_k)

        fused = rrf_fuse([vector_ranks, bm25_ranks], n=len(self.docs))
        order = np.argsort(-fused)[: self.top_k]
        return [(float(fused[i]), self.docs[i]) for i in order]


SAMPLE_DOCS = [
    "客服工单 #A-1024：用户反馈订单 88213 未按时发货，要求补发并赔偿优惠券。",
    "订单 88213 的物流状态为运输中，预计明天送达，仓库已登记延迟原因。",
    "RAG 先检索知识库片段再生成回答，适合接入频繁更新且需要溯源的事实性知识。",
    "向量检索通过语义相似度找到近义表述，对用户换一种说法提问依然能命中。",
    "退款流程：在订单详情页申请退款，财务在 3 个工作日内原路退回支付账户。",
]


def main() -> None:
    retriever = HybridRetriever(SAMPLE_DOCS)
    queries = [
        "订单 88213 现在到哪了？",      # 编号精确匹配，BM25 占优
        "怎么让大模型参考企业内部资料回答问题？",  # 语义近义，向量占优
        "钱付了但没收到货怎么办？",        # 两路都可能命中工单/退款
    ]
    for q in queries:
        print(f"\n问题：{q}")
        for rank, (score, doc) in enumerate(retriever.retrieve(q), start=1):
            print(f"  {rank}. [RRF={score:.4f}] {doc}")


if __name__ == "__main__":
    main()
