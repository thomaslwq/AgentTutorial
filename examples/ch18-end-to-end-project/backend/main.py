"""第18章 · 端到端示例后端：知识库客服 Agent 最小骨架。

串联的前序章节能力：
- FastAPI 服务化与 SSE 流式（第16章）
- 内存 RAG 检索（第08/09章的最小替代：关键词重叠打分，无外部向量库）
- 工具调用（第04章：search_kb）
- 前端按第17章契约解析同一套 SSE 事件

运行：
    pip install -r requirements.txt
    export OPENAI_API_KEY=sk-...   # 可选；不配置则走本地兜底回答
    uvicorn main:app --reload --port 8000
"""
from __future__ import annotations

import asyncio
import json
import os
import re
from typing import Any, Dict, List, Tuple

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

# ---------------------------------------------------------------- 知识库
# 演示用的内存条目；生产实现替换为第07章解析切分后的文档库 + 向量检索。

KB_DOCS: List[Dict[str, str]] = [
    {
        "title": "退货政策",
        "text": "商品签收后 7 天内可申请退货，商品需保持完好、配件齐全；定制类商品不支持无理由退货。",
    },
    {
        "title": "退款时效",
        "text": "退款审核通过后 1–3 个工作日按原支付路径退回；银行卡到账可能再延迟 1–2 个工作日。",
    },
    {
        "title": "物流查询",
        "text": "订单发货后可在「我的订单」查看物流单号；偏远地区配送时效为 5–7 个工作日。",
    },
    {
        "title": "发票开具",
        "text": "订单完成后 30 天内可申请电子发票，发票将发送至下单邮箱；纸质发票需联系客服登记。",
    },
    {
        "title": "会员权益",
        "text": "普通会员累计消费满 2000 元升级为银卡会员，享 95 折；银卡满 5000 元升级金卡，享 9 折与免运费。",
    },
]

# ------------------------------------------------------------ 内存检索

_WORD_RE = re.compile(r"[a-z0-9]+")
_CJK_RUN_RE = re.compile(r"[一-鿿]+")


def _tokenize(text: str) -> List[str]:
    """英文/数字按词切；中文按相邻二元组（bigram）切，避免单字误匹配。"""
    text = text.lower()
    tokens = _WORD_RE.findall(text)
    for run in _CJK_RUN_RE.findall(text):
        if len(run) == 1:
            tokens.append(run)
        else:
            tokens.extend(run[i : i + 2] for i in range(len(run) - 1))
    return tokens


def retrieve(query: str, top_k: int = 3) -> List[Dict[str, str]]:
    """关键词重叠打分的最小检索：无外部依赖，便于在示例中跑通 RAG 链路。

    生产实现替换为第08章的向量检索 / 第09章的混合检索与重排。
    """
    q_tokens = set(_tokenize(query))
    if not q_tokens:
        return []

    scored: List[Tuple[int, Dict[str, str]]] = []
    for doc in KB_DOCS:
        d_tokens = set(_tokenize(doc["title"] + " " + doc["text"]))
        overlap = len(q_tokens & d_tokens)
        if overlap > 0:
            scored.append((overlap, doc))
    scored.sort(key=lambda item: item[0], reverse=True)
    return [doc for _, doc in scored[:top_k]]


# ----------------------------------------------------------------- SSE 工具


def sse(payload: Dict[str, Any]) -> str:
    """把事件序列化为一帧 SSE：data: <json>\\n\\n。"""
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def fallback_answer(query: str, docs: List[Dict[str, str]]) -> str:
    """未配置模型 Key 时的本地兜底回答，只基于召回条目拼文案。"""
    if not docs:
        return "知识库中没有找到相关条目，建议换个说法，或转接人工客服。"
    lines = ["根据知识库为你整理："]
    for doc in docs:
        lines.append(f"· {doc['title']}：{doc['text']}")
    return "\n".join(lines)


def _llm_context(docs: List[Dict[str, str]]) -> str:
    return "\n".join(f"- [{d['title']}] {d['text']}" for d in docs)


# ----------------------------------------------------------------- FastAPI

app = FastAPI(title="ch18 知识库客服 Agent")

# 开发演示放开所有来源；生产环境必须收敛到具体前端域名（见本章部署 checklist）。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat")
async def chat(request: Request) -> StreamingResponse:
    body = await request.json()
    message = str(body.get("message", "")).strip()

    async def event_stream():
        try:
            # 1) 工具调用：检索知识库（对应第04章工具、第08章检索）
            yield sse({
                "type": "tool_start",
                "tool": "search_kb",
                "args": {"query": message},
            })
            docs = retrieve(message, top_k=3)
            yield sse({
                "type": "tool_end",
                "tool": "search_kb",
                "observation": (
                    f"召回 {len(docs)} 条相关条目："
                    f"{', '.join(d['title'] for d in docs)}"
                ),
            })

            context = _llm_context(docs)

            # 2) 生成回答：配了 Key 走 OpenAI 兼容接口流式输出；否则本地兜底
            if os.environ.get("OPENAI_API_KEY"):
                from openai import OpenAI

                # 自动读取 OPENAI_API_KEY / OPENAI_BASE_URL
                client = OpenAI()
                system_prompt = (
                    "你是一名严谨的知识库客服，只依据给定参考资料回答；"
                    "资料不足时明确说明，不要编造条款。\n参考资料：\n" + context
                )
                model = os.getenv("LLM_MODEL", "gpt-4o-mini")
                stream = client.chat.completions.create(
                    model=model,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": message},
                    ],
                    temperature=0.3,
                    stream=True,
                )
                for chunk in stream:
                    delta = chunk.choices[0].delta.content
                    if delta:
                        yield sse({"type": "token", "delta": delta})
            else:
                answer = fallback_answer(message, docs)
                # 按 6 字一片吐出，模拟流式节奏，便于前端观察逐字渲染
                for piece in re.findall(r".{1,6}", answer, flags=re.S):
                    yield sse({"type": "token", "delta": piece})
                    await asyncio.sleep(0.05)

            yield sse({"type": "done"})
        except Exception as exc:  # noqa: BLE001 —— 演示骨架：错误统一推给前端
            yield sse({"type": "error", "message": str(exc)})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
