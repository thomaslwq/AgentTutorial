"""第07章 · 切分策略实现（不依赖 langchain）

包含：
- 固定长度切分 FixedSizeChunker
- 递归字符切分 RecursiveCharacterChunker（按分隔符逐级回退）
- 重叠窗口：相邻 chunk 之间保留 overlap 字符，避免句义被截断
- 元数据保留：来源、标题层级、页码等随块向下传递

运行：
    python chunkers.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# 默认分隔符优先级：先按段落，再按换行，再按句子，最后按字符
DEFAULT_SEPARATORS = ["\n\n", "\n", "。", "！", "？", "；", "，", " ", ""]


@dataclass
class Chunk:
    """切分后的块：正文 + 继承自文档的元数据。"""

    text: str
    metadata: dict = field(default_factory=dict)


def _count(text: str) -> int:
    """统计长度。中文按字符计；接入 tokenizer 后可替换为 token 计数。"""
    return len(text)


# --------------------------------------------------------------------------- #
# 1. 固定长度切分：最朴素，不考虑边界
# --------------------------------------------------------------------------- #
class FixedSizeChunker:
    """按字符数硬性切分，支持 overlap。

    优点：实现简单、长度可控；缺点：可能从句子中间断开，语义破碎。
    """

    def __init__(self, chunk_size: int = 400, overlap: int = 50):
        if overlap >= chunk_size:
            raise ValueError("overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap

    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        metadata = metadata or {}
        text = text.strip()
        if not text:
            return []

        chunks: list[Chunk] = []
        step = self.chunk_size - self.overlap
        start = 0
        while start < len(text):
            end = start + self.chunk_size
            piece = text[start:end].strip()
            if piece:
                chunks.append(Chunk(text=piece, metadata=dict(metadata)))
            if end >= len(text):
                break
            start += step
        return chunks


# --------------------------------------------------------------------------- #
# 2. 递归字符切分：优先在自然边界断开，放不下才回退到更细的分隔符
# --------------------------------------------------------------------------- #
class RecursiveCharacterChunker:
    """递归字符切分器。

    流程：
    1. 用当前分隔符把文本拆成片段；
    2. 依次把片段攒入当前块，超过 chunk_size 就先落块；
    3. 单个片段仍超长时，用下一级更细的分隔符递归再拆；
    4. 相邻块按 overlap 保留尾部重叠，降低截断造成的语义损失。
    """

    def __init__(
        self,
        chunk_size: int = 400,
        overlap: int = 50,
        separators: list[str] | None = None,
    ):
        if overlap >= chunk_size:
            raise ValueError("overlap 必须小于 chunk_size")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.separators = separators or DEFAULT_SEPARATORS

    def split(self, text: str, metadata: dict | None = None) -> list[Chunk]:
        metadata = metadata or {}
        text = text.strip()
        if not text:
            return []
        pieces = self._split_text(text, self.separators)
        return self._merge(pieces, metadata)

    def _split_text(self, text: str, separators: list[str]) -> list[str]:
        """按分隔符递归拆分；返回不可再按当前边界切分的片段列表。"""
        sep = separators[0]
        rest = separators[1:]

        # 空分隔符表示已到最细粒度，直接按字符切
        if sep == "":
            return [text[i : i + self.chunk_size] for i in range(0, len(text), self.chunk_size)]

        parts = text.split(sep)
        result: list[str] = []
        for part in parts:
            if not part:
                continue
            if _count(part) <= self.chunk_size:
                result.append(part)
            elif rest:
                # 当前片段仍超长 → 用下一级分隔符递归
                result.extend(self._split_text(part, rest))
            else:
                result.append(part)
        return result

    def _merge(self, pieces: list[str], metadata: dict) -> list[Chunk]:
        """把短片段合并成 chunk_size 以内的块，并加重叠窗口。"""
        chunks: list[str] = []
        current = ""

        for piece in pieces:
            candidate = piece if not current else current + piece
            if _count(candidate) <= self.chunk_size:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                # 单片段已超长：递归阶段已保证其不超过 chunk_size，这里直接落块
                current = piece
        if current:
            chunks.append(current)

        return [
            Chunk(text=self._with_overlap(chunks, i), metadata=dict(metadata))
            for i in range(len(chunks))
        ]

    def _with_overlap(self, chunks: list[str], index: int) -> str:
        """给当前块头部补上前一块尾部的 overlap 字符。"""
        if index == 0 or self.overlap == 0:
            return chunks[index]
        prev_tail = chunks[index - 1][-self.overlap :]
        return prev_tail + chunks[index]


# --------------------------------------------------------------------------- #
# 3. 标题层级切分（Markdown）：按 # 标题归组，保留层级元数据
# --------------------------------------------------------------------------- #
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*)$")


def split_by_headings(
    text: str, metadata: dict | None = None, max_chars: int = 600
) -> list[Chunk]:
    """按 Markdown 标题切分，标题层级写入 metadata.heading。

    某个小节过长时，再交给递归字符切分兜底；短小节保持完整，避免
    把同属一个主题的内容拆到不同块。
    """
    metadata = metadata or {}
    sections: list[tuple[str, str, list[str]]] = []  # level, title, lines
    current_level, current_title, current_lines = "", "", []

    for line in text.splitlines():
        m = _HEADING_RE.match(line)
        if m:
            if current_lines:
                sections.append((current_level, current_title, current_lines))
            current_level, current_title = m.group(1), m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_level, current_title, current_lines))

    chunker = RecursiveCharacterChunker(chunk_size=max_chars, overlap=40)
    chunks: list[Chunk] = []
    for level, title, lines in sections:
        section_text = "\n".join(lines).strip()
        if not section_text:
            continue
        section_meta = dict(metadata)
        section_meta["heading"] = title
        section_meta["heading_level"] = len(level)
        if _count(section_text) <= max_chars:
            chunks.append(Chunk(text=section_text, metadata=section_meta))
        else:
            chunks.extend(chunker.split(section_text, section_meta))
    return chunks


# --------------------------------------------------------------------------- #
# 演示
# --------------------------------------------------------------------------- #
def _demo() -> None:
    sample = (
        "RAG 链路包含离线入库与在线检索两段。离线侧完成文档加载、切分、"
        "向量化与入库；在线侧接收用户问题，检索相关块，拼装上下文后交给生成模型。\n\n"
        "检索质量直接决定答案上限。漏掉关键片段，生成环节再强也无法补回；"
        "混入无关内容则会稀释模型注意力。因此切分需要在语义完整与长度可控之间权衡。\n\n"
        "元数据随块保留：来源文件、页码、标题层级，便于溯源与后续过滤检索。"
    )

    print("=== 固定长度切分（chunk_size=60, overlap=10）===")
    for c in FixedSizeChunker(chunk_size=60, overlap=10).split(sample, {"source": "demo.md"}):
        print(f"- [{len(c.text)}字] {c.text[:40]}...")

    print("\n=== 递归字符切分（chunk_size=80, overlap=15）===")
    for c in RecursiveCharacterChunker(chunk_size=80, overlap=15).split(
        sample, {"source": "demo.md"}
    ):
        print(f"- [{len(c.text)}字] {c.text[:40]}...")

    md = "# 产品手册\nRAG 定义段落。\n\n## 入库流程\n加载、切分、向量化、入库。\n\n## 检索流程\n问题向量化、召回、拼上下文、生成。"
    print("\n=== 标题切分 ===")
    for c in split_by_headings(md, {"source": "manual.md"}):
        print(f"- {c.metadata['heading']}（L{c.metadata['heading_level']}）: {c.text[:30]}")


if __name__ == "__main__":
    _demo()
