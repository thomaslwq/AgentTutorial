# ch07-parse-chunk · 第 07 章配套示例

文档加载清洗与切分策略的最小实现，不依赖 LangChain。

## 环境准备

```bash
# Markdown / HTML / CSV / 切分部分仅用 Python 标准库；解析 PDF 需要 pypdf
pip install -r requirements.txt
```

## 文件说明

| 文件 | 职责 |
|---|---|
| `loader.py` | Markdown/纯文本、HTML、PDF（pypdf）、CSV 表格的加载与清洗 |
| `chunkers.py` | 固定长度切分、递归字符切分、标题层级切分、重叠窗口 |

## 运行

```bash
python chunkers.py   # 三种切分策略在示例文本上的输出对比
python loader.py     # HTML 抽取与表格清洗演示（标准库可跑通）
```

### 解析真实 PDF

`loader.py` 中的 `load_pdf(path)` 在安装 pypdf 后可用：

```python
from loader import load_pdf

doc = load_pdf("your-manual.pdf")
print(doc.metadata["pages"], doc.text[:200])
```

## 练习参考答案

### 练习 1：对比两种切分的块边界

分别用 `FixedSizeChunker(chunk_size=80, overlap=15)` 与 `RecursiveCharacterChunker(chunk_size=80, overlap=15)` 切同一段长文本，打印每个块的首尾。固定长度切分会在句子甚至词语中间断开；递归切分优先落在段落、换行、句末标点等自然边界上，单块语义更完整。代价是实现更复杂，且块长度不如固定切分整齐。

### 练习 2：调整 overlap

把 `overlap` 从 0 逐步增大到 `chunk_size` 的四分之一。overlap 为 0 时，被截断的句子在相邻块之间没有重复，跨块推理容易丢上下文；overlap 增大后衔接更平滑，但每个块携带的重复内容变多，索引体积与检索 token 成本上升。`overlap` 一般取 `chunk_size` 的 10%–20%，并按实测召回效果调整。

### 练习 3：为 chunk 补元数据

在 `split_by_headings` 产出的块上补充页码：解析 PDF 时按页记录文本边界，切分后根据块正文在原文中的起止位置反查所属页码，写入 `metadata["page"]`。要点是元数据必须在「加载阶段就拿到、随切分逐层传递」，而不是切完之后再回查；否则表格、标题等信息已经在清洗中丢失。
