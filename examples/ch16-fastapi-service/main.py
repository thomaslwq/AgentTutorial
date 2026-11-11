"""第 16 章 · FastAPI 封装 Agent：非流式 /chat + SSE /chat/stream

运行：
  export OPENAI_API_KEY=sk-你的key
  pip install -r requirements.txt
  uvicorn main:app --host 0.0.0.0 --port 8000

可选环境变量：
  OPENAI_BASE_URL  兼容 OpenAI 协议的服务端点
  CHAT_MODEL       默认 gpt-4o-mini
  CORS_ORIGINS     逗号分隔的允许来源，默认 *（仅开发环境）
  MAX_HISTORY      每个会话保留的最近消息条数，默认 20
"""
from __future__ import annotations

import json
import os
import uuid
from typing import AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from openai import AsyncOpenAI, OpenAIError
from pydantic import BaseModel, Field

MODEL = os.getenv("CHAT_MODEL", "gpt-4o-mini")
MAX_HISTORY = int(os.getenv("MAX_HISTORY", "20"))
SYSTEM_PROMPT = "你是一名严谨的技术助手，回答简洁、有条理。"

# 自动读取环境变量 OPENAI_API_KEY / OPENAI_BASE_URL
client = AsyncOpenAI()

# 会话存储：session_id -> messages 列表。
# 生产环境替换为 Redis：会话历史按 session_id 存 Hash 或 JSON，带 TTL。
sessions: dict[str, list[dict]] = {}

app = FastAPI(title="Agent Chat Service", version="0.1.0")

# CORS：默认放开便于本地开发；生产环境通过 CORS_ORIGINS 指定具体来源
_origins = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials=_origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- 请求 / 响应契约 ----------


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="用户消息")
    session_id: str | None = Field(None, description="会话 ID；缺省则新建")


class ChatResponse(BaseModel):
    session_id: str
    reply: str
    model: str


# ---------- 会话管理 ----------


def get_or_create_session(session_id: str | None) -> str:
    if session_id and session_id in sessions:
        return session_id
    new_id = session_id or uuid.uuid4().hex[:12]
    sessions.setdefault(
        new_id, [{"role": "system", "content": SYSTEM_PROMPT}]
    )
    return new_id


def append_message(session_id: str, role: str, content: str) -> None:
    history = sessions[session_id]
    history.append({"role": role, "content": content})
    # 裁剪：保留 system 消息 + 最近 MAX_HISTORY 条，避免上下文无限膨胀
    if len(history) > MAX_HISTORY + 1:
        system = history[0]
        history[:] = [system] + history[-MAX_HISTORY:]


# ---------- 模型调用 ----------


async def call_model(messages: list[dict]) -> str:
    try:
        resp = await client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,
        )
    except OpenAIError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"上游模型调用失败: {exc}",
            headers={"X-Error-Code": "UPSTREAM_ERROR"},
        )
    return resp.choices[0].message.content or ""


# ---------- 端点 ----------


@app.get("/healthz")
async def healthz() -> dict:
    return {"status": "ok", "sessions": len(sessions), "model": MODEL}


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest) -> ChatResponse:
    """非流式端点：等模型跑完，一次性返回完整回答。"""
    session_id = get_or_create_session(req.session_id)
    append_message(session_id, "user", req.message)

    reply = await call_model(sessions[session_id])
    append_message(session_id, "assistant", reply)

    return ChatResponse(session_id=session_id, reply=reply, model=MODEL)


async def stream_generator(session_id: str, message: str) -> AsyncIterator[bytes]:
    """SSE 异步生成器：逐 token 推送给客户端，结束后回写完整回答。"""
    append_message(session_id, "user", message)
    collected: list[str] = []

    try:
        stream = await client.chat.completions.create(
            model=MODEL,
            messages=sessions[session_id],
            temperature=0.3,
            stream=True,
        )
        async for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content
            if delta:
                collected.append(delta)
                payload = {"event": "token", "token": delta, "session_id": session_id}
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n".encode()

        reply = "".join(collected)
        append_message(session_id, "assistant", reply)
        done = {"event": "done", "session_id": session_id, "reply": reply, "model": MODEL}
        yield f"data: {json.dumps(done, ensure_ascii=False)}\n\n".encode()
    except OpenAIError as exc:
        err = {"event": "error", "code": "UPSTREAM_ERROR", "message": str(exc)}
        yield f"data: {json.dumps(err, ensure_ascii=False)}\n\n".encode()


@app.post("/chat/stream")
async def chat_stream(req: ChatRequest) -> StreamingResponse:
    """SSE 流式端点：异步生成器逐 token 推送，响应类型为 text/event-stream。"""
    session_id = get_or_create_session(req.session_id)
    return StreamingResponse(
        stream_generator(session_id, req.message),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",  # 关闭反向代理缓冲，保证逐 token 下发
        },
    )
