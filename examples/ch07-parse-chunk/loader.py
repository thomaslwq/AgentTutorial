"""第07章 · 文档加载与清洗示例

覆盖：Markdown / 纯文本、HTML、PDF（pypdf）、表格行清洗。
重库（pypdf）在 requirements.txt 中声明，未安装时 PDF 函数给出明确报错；
Markdown / HTML / 表格部分仅用标准库即可运行。

运行：
    pip install -r requirements.txt
    python loader.py
"""
from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class Document:
    """加载后的原始文档：正文 + 元数据。

    metadata 至少包含 source（来源标识），解析阶段能拿到的页码、
    标题层级等也在这里记录，后续随 chunk 向下传递。
    """

    text: str
    metadata: dict = field(default_factory=dict)


# --------------------------------------------------------------------------- #
# 1. Markdown / 纯文本
# --------------------------------------------------------------------------- #
def load_markdown(path: str | Path) -> Document:
    """读取 Markdown 或纯文本，保留标题行用于后续层级解析。"""
    path = Path(path)
    text = path.read_text(encoding="utf-8").strip()
    return Document(text=text, metadata={"source": path.name, "format": "markdown"})


# --------------------------------------------------------------------------- #
# 2. HTML：去标签、反转义 HTML 实体、压缩多余空白
# --------------------------------------------------------------------------- #
_TAG_RE = re.compile(r"<(script|style)[^>]*>.*?</\1>", re.S | re.I)
_ANY_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"[ \t]+")


def load_html(path: str | Path) -> Document:
    """从 HTML 中抽取正文：先删脚本样式，再去标签，最后反转义并规整空白。"""
    path = Path(path)
    raw = path.read_text(encoding="utf-8")

    raw = _TAG_RE.sub(" ", raw)              # 移除 <script>/<style> 整块
    raw = _ANY_TAG_RE.sub(" ", raw)          # 移除其余标签
    raw = html.unescape(raw)                 # &amp; &lt; 等实体还原
    raw = _WS_RE.sub(" ", raw)
    raw = re.sub(r"\n\s*\n+", "\n\n", raw)   # 保留段落空行
    return Document(text=raw.strip(), metadata={"source": path.name, "format": "html"})


# --------------------------------------------------------------------------- #
# 3. PDF：pypdf 按页抽取，页码写入元数据（重库，按需安装）
# --------------------------------------------------------------------------- #
def load_pdf(path: str | Path) -> Document:
    """逐页抽取 PDF 文本，页间用换行分隔；页码保留在 metadata.pages。

    返回的是整篇文档；页码级别的归属在切分时再映射到具体 chunk。
    """
    path = Path(path)
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # 练习环境未安装重库时给出可读提示
        raise RuntimeError(
            "未安装 pypdf，请先 `pip install -r requirements.txt` 后再解析 PDF。"
        ) from exc

    reader = PdfReader(str(path))
    page_texts: list[str] = []
    for page in reader.pages:
        page_texts.append((page.extract_text() or "").strip())

    text = "\n\n".join(t for t in page_texts if t)
    return Document(
        text=text,
        metadata={
            "source": path.name,
            "format": "pdf",
            "pages": len(reader.pages),
        },
    )


# --------------------------------------------------------------------------- #
# 4. 表格清洗：把 CSV 行转成可读文本，剔空行与分隔行
# --------------------------------------------------------------------------- #
def clean_table_rows(rows: list[list[str]], headers: list[str]) -> list[str]:
    """把二维表格转成「列名：值」形式的文本行，便于后续随正文一起切分。

    空单元格跳过；整行为空或全为分隔符（如 ---）时丢弃。
    """
    lines: list[str] = []
    for row in rows:
        cells = [c.strip() for c in row]
        if not any(cells):
            continue
        if all(re.fullmatch(r"-+", c or "") for c in cells):
            continue
        pairs = [
            f"{headers[i]}：{cells[i]}"
            for i in range(min(len(headers), len(cells)))
            if cells[i]
        ]
        if pairs:
            lines.append("；".join(pairs))
    return lines


def load_csv_as_doc(path: str | Path) -> Document:
    """把 CSV 表格读成文档：首行表头，其余行转成描述性文本。"""
    import csv

    path = Path(path)
    with path.open(encoding="utf-8", newline="") as f:
        reader = csv.reader(f)
        rows = list(reader)
    if not rows:
        return Document(text="", metadata={"source": path.name, "format": "csv"})

    headers, data_rows = rows[0], rows[1:]
    lines = clean_table_rows(data_rows, headers)
    return Document(
        text="\n".join(lines),
        metadata={"source": path.name, "format": "csv", "rows": len(lines)},
    )


# --------------------------------------------------------------------------- #
# 演示：标准库可跑通的 HTML / 表格清洗
# --------------------------------------------------------------------------- #
def _demo() -> None:
    sample_html = """
    <html><head><style>body{color:red}</style></head>
    <body><h1>产品手册</h1><p>RAG 链路包含离线入库与在线检索两段。</p>
    <script>console.log('ignore me')</script></body></html>
    """
    doc = load_html_from_string(sample_html)
    print("[HTML 抽取结果]")
    print(doc.text)
    print("metadata:", doc.metadata)

    lines = clean_table_rows(
        [["标准版", "99"], ["企业版", "299"], ["", ""], ["---", "---"]],
        headers=["套餐", "价格"],
    )
    print("\n[表格清洗结果]")
    for line in lines:
        print(line)


def load_html_from_string(raw: str) -> Document:
    """便于演示：直接从字符串加载 HTML。"""
    raw = _TAG_RE.sub(" ", raw)
    raw = _ANY_TAG_RE.sub(" ", raw)
    raw = html.unescape(raw)
    raw = _WS_RE.sub(" ", raw)
    return Document(text=raw.strip(), metadata={"source": "<string>", "format": "html"})


if __name__ == "__main__":
    _demo()
