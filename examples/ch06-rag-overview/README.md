# ch06-rag-overview · 第 06 章配套示例

一个最小端到端 RAG demo：内存向量库 + OpenAI Embedding + 余弦相似度 + 上下文拼装 + 聊天模型生成。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

# 可选：覆盖默认模型
# export RAG_EMBEDDING_MODEL=text-embedding-3-small
# export RAG_CHAT_MODEL=gpt-4o-mini

pip install -r requirements.txt
```

## 运行

```bash
python minimal_rag.py
```

## 预期输出

程序先把两段示例文档切分、向量化并写入内存库，然后依次回答三个问题：

1. 「RAG 主要解决哪三类问题？」——应能从资料中提取出知识截止、私有数据、幻觉三点；
2. 「微调适合解决什么样的问题？」——应指向稳定的风格、格式与领域推理；
3. 「2026 年世界杯冠军是谁？」——资料中没有该信息，模型应明确说明资料不足，而不是编造。

检索阶段会按余弦相似度取前 `TOP_K` 个块；上下文里每个资料块都标注了来源，便于溯源。

## 代码结构与后续章节接口

| 组件 | 职责 | 后续替换方向 |
|---|---|---|
| `split_into_paragraphs` | 占位切分 | 第 07 章：递归字符切分、标题层级切分 |
| `EmbeddingModel` | 文本向量化 | 第 08 章：本地模型、批量与缓存 |
| `InMemoryVectorStore` | 向量存储与相似度检索 | 第 08 章：FAISS / 向量数据库、混合检索、重排序 |
| `Retriever` | query → 检索 | 第 09 章：查询改写、多路召回 |
| `RagChain` | 拼上下文 → 生成 | 第 09 章：引用标注、答案校验与评测 |

## 练习参考答案

### 练习 1：调整召回数量

把 `TOP_K` 从 3 改为 1，重跑第一个问题。上下文变短、token 成本下降，但如果相关信息分散在多个段落，单块可能覆盖不全，答案容易缺要点；`TOP_K` 过大则会塞进无关片段，稀释模型注意力并增加成本。实际取值需要结合 chunk 大小与评测结果确定（第 09 章）。

### 练习 2：把检索结果打印出来

在 `RagChain.answer` 中，`retrieved = self.retriever.retrieve(query)` 之后遍历 `retrieved`，打印每条的 `score`、`metadata["source"]` 与正文前 50 字。可以观察到：相关块的余弦相似度明显高于无关块；得分接近时，块的顺序对最终答案影响不大。

### 练习 3：观察「资料不足」时的行为

第三个问题在资料中没有对应答案。由于 system prompt 要求「资料不足就直接说明」，模型应拒绝编造。如果把 system prompt 中这条约束删掉，模型更可能凭参数记忆补出一个答案——这正是 RAG 不能替代 Prompt 约束与答案校验的原因，第 09 章会讨论评测与兜底策略。
