# ch08-embedding-retrieval · 第 08 章配套示例

两个脚本：`simple_vector_store.py` 用 numpy 手写余弦相似度的最小向量库；`hybrid_retrieval.py` 演示 BM25 关键词召回与向量召回的 RRF 融合。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key   # 可选；不配置则向量侧走离线哈希兜底
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1
# 可选：覆盖默认 Embedding 模型
# export RAG_EMBEDDING_MODEL=text-embedding-3-small

pip install -r requirements.txt
```

> 未配置 `OPENAI_API_KEY` 时，脚本使用离线哈希向量跑通排序逻辑；该向量只记录词项是否出现，不具备真实语义相似度，得分不能与线上 Embedding 模型横向比较。

## 运行

```bash
python simple_vector_store.py   # 最小向量库：入库 → 余弦相似度 → top-k
python hybrid_retrieval.py      # 混合检索：BM25 + 向量召回，RRF 融合
```

## 预期输出

`simple_vector_store.py` 把 4 段示例文档入库，对 3 个问题各输出 top-3：得分越高表示向量方向越接近。配置真实 Embedding 模型后，语义改写类问题（如「怎么把外部资料接进大模型的回答里？」）应能命中讲 RAG 的片段；离线兜底模式下主要按词面重合度排序。

`hybrid_retrieval.py` 对 3 个问题分别做两路召回再融合：

1. 「订单 88213 现在到哪了？」——编号 `88213` 是强词项信号，BM25 路应把讲物流状态的文档顶到前面；
2. 「怎么让大模型参考企业内部资料回答问题？」——没有字面重合，向量路靠语义相似度命中 RAG 片段；
3. 「钱付了但没收到货怎么办？」——两路分别命中工单与退款流程，融合后共同排在前列。

RRF 分数只用于排名，不代表相似度绝对值；不同召回路的原始分数量纲不同，不能直接相加。

## 代码结构

| 组件 | 职责 |
|---|---|
| `embed_texts` | 批量向量化，返回 L2 归一化矩阵；有 Key 走 OpenAI，无 Key 走离线兜底 |
| `VectorStore` | 内存向量库：存文档文本与向量矩阵，余弦相似度 top-k 检索 |
| `BM25` | 关键词检索：IDF、词频饱和、文档长度归一化 |
| `rrf_fuse` | 倒数排名融合，按排名而非原始分数合并多路召回 |
| `HybridRetriever` | 两路召回 → RRF 融合 → 截断 top-k |

## 练习参考答案

### 练习 1：配 Key 与不配 Key 的得分差异

分别在配置与不配置 `OPENAI_API_KEY` 的情况下运行 `simple_vector_store.py`。离线哈希向量只记录词项出现与否，语义改写（同义表述、换语序）几乎得不到加分；真实 Embedding 模型把语义相近的文本映到相近方向，改写类问题仍能命中相关片段。因此检索质量的前提是嵌入模型本身的语义能力，向量库选型只是其次。

### 练习 2：调整 top-k 观察尾部得分

把 `VectorStore.search` 的 `top_k` 从 3 改为 5（示例库只有 4 篇文档时改为 4），重跑。前几条通常得分明显偏高，尾部文档得分趋近于零；工程上 top-k 过大会把低相关片段塞进上下文，稀释模型注意力并增加 token 成本，取值需要结合第 09 章的评测结果确定。

### 练习 3：编号类查询的两路短板

纯向量检索把编号 `88213` 当作普通数字编码，容易被同主题的其他工单分散注意力；BM25 对精确词项匹配强，但遇到用户换说法（如「钱付了没收到货」）又会失配。混合检索正是为了互补：关键词路保住精确匹配，向量路兜住语义改写，再用 RRF 融合排名。专有名词、型号、编号密集的知识库，建议默认开混合检索。
