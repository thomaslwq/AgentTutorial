# ch03-memory · 第 03 章配套示例

三个脚本分别对应：滑动窗口记忆、摘要压缩记忆、长期记忆三种落法。

## 环境准备

```bash
export OPENAI_API_KEY=sk-你的key
# 兼容 OpenAI 协议的国产服务另设：
# export OPENAI_BASE_URL=https://your-endpoint/v1

pip install -r requirements.txt
```

> `sliding_window.py` 与 `long_term_memory.py` 不调用模型，无需 Key 即可运行；
> `summary_memory.py` 的压缩步骤会发起一次真实模型调用。

## 运行

```bash
python sliding_window.py      # 窗口淘汰：观察超预算时最旧消息被丢弃
python summary_memory.py       # 摘要压缩：旧对话并入摘要，只保留摘要 + 近期窗口
python long_term_memory.py     # 键值 / 向量 / 文件三种长期记忆最小演示
```

## 预期输出说明

- `sliding_window.py`：打印 `[淘汰]` 日志与最终窗口内保留的消息，末尾给出窗口 token 估算与预算；越旧的消息越早被移出窗口。
- `summary_memory.py`：近期窗口超过 `max_recent` 时打印 `[压缩]`，组装出的消息列表由「系统提示 + 历史摘要 + 近期消息」构成；无 Key 时压缩调用会报错，属预期行为。
- `long_term_memory.py`：依次输出键值召回结果、向量相似度 Top 命中、文件检索结果，并在当前目录生成 `long_term_memory.json`。

## 练习参考答案

### 练习 1：调整窗口预算

把 `sliding_window.py` 的 `max_window_tokens` 从 `120` 调到 `300`：窗口能容纳的消息变多，淘汰日志减少；调小到 `60` 则更早丢弃历史。预算设置要给模型回复留出 `max_tokens` 空间，不能把输入窗口撑到模型上下文上限。

### 练习 2：摘要记忆的过期策略

在 `SummaryMemory` 中增加「摘要字数上限」：当 `len(self.summary)` 超过阈值时，对摘要本身再做一次压缩，只保留最近出现过的实体与结论。实现上复用 `_compress`，把已有摘要当作「新对话记录」的一部分重新总结即可。

### 练习 3：向量记忆接真实 Embedding

把 `VectorMemory._cosine` 替换为调用 Embedding 接口：

```python
from openai import OpenAI
client = OpenAI()

def embed(text: str) -> list[float]:
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding
```

入库时存稠密向量，检索时对查询文本做同样的嵌入再算余弦相似度；数据量变大后再迁入 Chroma / Qdrant / pgvector 等向量库。
