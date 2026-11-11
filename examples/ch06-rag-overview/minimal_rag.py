"""第06章 · 最小端到端 RAG demo（内存存储 + OpenAI Embedding + 余弦相似度）

前置：
    export OPENAI_API_KEY=sk-...
    # 兼容 OpenAI 协议的国产服务另设：
    # export OPENAI_BASE_URL=https://your-endpoint/v1

运行：
    pip install -r requirements.txt
    python minimal_rag.py

说明：
    - 向量库用内存列表代替，目的是把「加载 → 切分 → embedding → 入库 →
      检索 → 拼上下文 → 生成」这条主干链路讲清楚；
    - 切分与 embedding 的工程化细节在第 07、08 章展开，这里用最简单的
      按段落切分占位；
    - 接口（IngestPipeline / Retriever / RagChain）按可替换组件设计，
      后续章节可以把内存向量库换成 FAISS / 向量数据库，把检索换成
      混合检索或重排序，而不必改动调用方。
"""
import os
import math
from dataclasses import dataclass, field

from openai import OpenAI

# 模型名可按兼容服务替换；embedding 模型需与服务端支持的型号一致
EMBEDDING_MODEL = os.getenv("RAG_EMBEDDING_MODEL", "text-embedding-3-small")
CHAT_MODEL = os.getenv("RAG_CHAT_MODEL", "gpt-4o-mini")
TOP_K = 3


# --------------------------------------------------------------------------- #
# 数据结构：一个文档块（chunk）及其入库记录
# --------------------------------------------------------------------------- #
@dataclass
class Document:
    """原始文档：text 为正文，metadata 记录来源等信息。"""

    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class Chunk:
    """切分后的块：保留正文与来源元数据。"""

    text: str
    metadata: dict = field(default_factory=dict)


@dataclass
class RetrievedChunk:
    """检索结果：正文、元数据、相似度得分。"""

    text: str
    metadata: dict
    score: float


# --------------------------------------------------------------------------- #
# 1. 切分占位：第 07 章会替换为递归字符切分
# --------------------------------------------------------------------------- #
def split_into_paragraphs(doc: Document) -> list[Chunk]:
    """按空行把文档切成段落，过滤过短的碎片。"""
    chunks: list[Chunk] = []
    for para in doc.text.split("\n\n"):
        para = para.strip()
        if len(para) >= 20:
            chunks.append(Chunk(text=para, metadata=dict(doc.metadata)))
    return chunks


# --------------------------------------------------------------------------- #
# 2. Embedding：批量调用，返回与输入等长的向量列表
# --------------------------------------------------------------------------- #
class EmbeddingModel:
    """对 OpenAI Embedding 接口的薄封装，便于后续替换为本地模型。"""

    def __init__(self, client: OpenAI, model: str = EMBEDDING_MODEL):
        self.client = client
        self.model = model

    def embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        resp = self.client.embeddings.create(model=self.model, input=texts)
        return [item.embedding for item in resp.data]


# --------------------------------------------------------------------------- #
# 3. 内存向量库：存 chunk 文本、元数据与向量；第 08 章替换为向量数据库
# --------------------------------------------------------------------------- #
class InMemoryVectorStore:
    def __init__(self) -> None:
        self.chunks: list[Chunk] = []
        self.vectors: list[list[float]] = []

    def add(self, chunks: list[Chunk], vectors: list[list[float]]) -> None:
        self.chunks.extend(chunks)
        self.vectors.extend(vectors)

    def search(self, query_vector: list[float], top_k: int) -> list[RetrievedChunk]:
        scored: list[tuple[float, Chunk]] = []
        for chunk, vec in zip(self.chunks, self.vectors):
            scored.append((cosine_similarity(query_vector, vec), chunk))
        scored.sort(key=lambda pair: pair[0], reverse=True)
        return [
            RetrievedChunk(text=chunk.text, metadata=chunk.metadata, score=score)
            for score, chunk in scored[:top_k]
        ]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    """余弦相似度：向量方向越接近得分越高。"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# --------------------------------------------------------------------------- #
# 4. 检索器：把「query → embedding → 向量库检索」封装成一个组件
# --------------------------------------------------------------------------- #
class Retriever:
    def __init__(self, store: InMemoryVectorStore, embedder: EmbeddingModel, top_k: int = TOP_K):
        self.store = store
        self.embedder = embedder
        self.top_k = top_k

    def retrieve(self, query: str) -> list[RetrievedChunk]:
        query_vec = self.embedder.embed([query])[0]
        return self.store.search(query_vec, self.top_k)


# --------------------------------------------------------------------------- #
# 5. 上下文拼装 + 生成：把检索结果塞进 Prompt，再调聊天模型
# --------------------------------------------------------------------------- #
SYSTEM_PROMPT = (
    "你是一名严谨的技术助手。只能依据下面给出的「参考资料」回答问题；"
    "如果参考资料中没有相关信息，直接说明资料不足，不要编造。"
)


def build_context(chunks: list[RetrievedChunk]) -> str:
    """把检索到的块拼成编号上下文，保留来源元数据便于溯源。"""
    lines: list[str] = []
    for idx, chunk in enumerate(chunks, start=1):
        source = chunk.metadata.get("source", "未知来源")
        lines.append(f"[资料 {idx}]（来源：{source}）\n{chunk.text}")
    return "\n\n".join(lines)


class RagChain:
    def __init__(self, client: OpenAI, retriever: Retriever, model: str = CHAT_MODEL):
        self.client = client
        self.retriever = retriever
        self.model = model

    def answer(self, query: str) -> str:
        retrieved = self.retriever.retrieve(query)
        context = build_context(retrieved)

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": f"参考资料：\n{context}\n\n问题：{query}",
            },
        ]
        resp = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            temperature=0.2,
        )
        return resp.choices[0].message.content or ""


# --------------------------------------------------------------------------- #
# 6. 入库流水线：文档 → 切分 → embedding → 写入向量库
# --------------------------------------------------------------------------- #
class IngestPipeline:
    def __init__(self, store: InMemoryVectorStore, embedder: EmbeddingModel):
        self.store = store
        self.embedder = embedder

    def ingest(self, docs: list[Document]) -> None:
        chunks: list[Chunk] = []
        for doc in docs:
            chunks.extend(split_into_paragraphs(doc))
        vectors = self.embedder.embed([chunk.text for chunk in chunks])
        self.store.add(chunks, vectors)


# --------------------------------------------------------------------------- #
# 演示数据与主流程
# --------------------------------------------------------------------------- #
SAMPLE_DOCS = [
    Document(
        text=(
            "RAG（Retrieval-Augmented Generation，检索增强生成）是一种把外部知识"
            "检索结果注入大模型 Prompt 的技术路线。模型在回答前先从知识库中取回"
            "相关片段，再基于这些片段生成答案，从而不必把所有知识都训练进参数。\n\n"
            "RAG 主要解决三类问题：模型训练数据存在知识截止日期，无法回答最新事件；"
            "企业内部的私有文档、工单、制度没有进入训练集；模型在信息不足时容易"
            "产生看似合理但与事实不符的幻觉。\n\n"
            "一条标准 RAG 链路包含离线入库与在线检索两段：离线侧完成文档加载、"
            "切分、向量化与入库；在线侧接收用户问题，检索相关块，拼装上下文后"
            "交给生成模型。"
        ),
        metadata={"source": "rag-basics.md"},
    ),
    Document(
        text=(
            "微调（Fine-tuning）是在预训练模型基础上用领域数据继续训练，把特定"
            "领域的表达习惯、任务格式固化进模型参数。微调成本高、更新慢，适合"
            "稳定的风格与任务形态。\n\n"
            "RAG 与微调不是互斥关系：RAG 擅长接入频繁更新、需要溯源的事实性知识；"
            "微调擅长塑造模型的语气、格式与领域推理方式。生产系统常两者结合使用。"
        ),
        metadata={"source": "finetune-vs-rag.md"},
    ),
]


def main() -> None:
    client = OpenAI()
    embedder = EmbeddingModel(client)
    store = InMemoryVectorStore()

    # 离线：入库
    IngestPipeline(store, embedder).ingest(SAMPLE_DOCS)

    # 在线：检索 + 生成
    chain = RagChain(client, Retriever(store, embedder))

    questions = [
        "RAG 主要解决哪三类问题？",
        "微调适合解决什么样的问题？",
        "2026 年世界杯冠军是谁？",  # 资料中没有，预期模型承认资料不足
    ]
    for q in questions:
        print(f"\n问题：{q}")
        print(f"回答：{chain.answer(q)}")


if __name__ == "__main__":
    main()
