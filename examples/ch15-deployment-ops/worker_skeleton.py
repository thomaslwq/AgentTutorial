"""第 15 章 · 异步任务队列骨架（asyncio）

包含：
- asyncio.Queue 作为任务缓冲区；
- 一组 worker 协程并发消费任务，失败按次数重试 + 退避；
- 任务状态存储（内存 dict，生产环境替换为 Redis / 数据库）；
- 结构化日志（时间、级别、任务 ID、事件、字段）；
- 健康检查 HTTP 端点（标准库 asyncio 实现，不依赖 Web 框架）。

运行：python worker_skeleton.py

可选环境变量：
  WORKER_CONCURRENCY  并发 worker 数，默认 3
  HEALTH_PORT         健康检查端口，默认 8081
  LOG_LEVEL           日志级别，默认 INFO
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

# ---------- 结构化日志 ----------


class JsonLineFormatter(logging.Formatter):
    """把日志记录拍平成一行 JSON，便于 ELK / Loki 等日志系统采集。"""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(record.created)),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        # 结构化字段通过 extra= 传入，例如 extra={"job_id": ...}
        for key in ("job_id", "attempt", "elapsed_ms", "error", "backoff"):
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def configure_logging(level: str) -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonLineFormatter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())


logger = logging.getLogger("agent-worker")

# ---------- 任务模型与存储 ----------

STATUS_QUEUED = "queued"
STATUS_RUNNING = "running"
STATUS_SUCCEEDED = "succeeded"
STATUS_FAILED = "failed"

MAX_ATTEMPTS = 3
BACKOFF_SECONDS = [0.2, 0.5, 1.0]


@dataclass
class Job:
    job_id: str
    payload: dict[str, Any]
    status: str = STATUS_QUEUED
    attempts: int = 0
    result: Any = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


class TaskStore:
    """内存任务台账。生产环境替换为 Redis（状态 + 过期）或关系库。"""

    def __init__(self) -> None:
        self._jobs: dict[str, Job] = {}

    def put(self, job: Job) -> None:
        self._jobs[job.job_id] = job
        self._touch(job)

    def get(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def update(self, job: Job, **changes: Any) -> None:
        for key, value in changes.items():
            setattr(job, key, value)
        self._touch(job)

    def all_jobs(self) -> list[Job]:
        return list(self._jobs.values())

    def stats(self) -> dict[str, int]:
        counts = {STATUS_QUEUED: 0, STATUS_RUNNING: 0,
                  STATUS_SUCCEEDED: 0, STATUS_FAILED: 0}
        for job in self._jobs.values():
            counts[job.status] = counts.get(job.status, 0) + 1
        return counts

    @staticmethod
    def _touch(job: Job) -> None:
        job.updated_at = time.time()


# ---------- Agent 执行体（扩展点） ----------


async def run_agent_task(payload: dict[str, Any]) -> dict[str, Any]:
    """真正的 Agent 执行体。

    骨架里用 sleep 模拟一次多步推理 / 工具调用；接入真实系统时，
    在这里替换为：读取会话历史 -> 跑 Agent 循环（第 05 章）-> 返回结果。

    注意：OpenAI 同步 SDK 会阻塞事件循环，异步服务里应使用 AsyncOpenAI，
    或用 asyncio.to_thread 包裹同步调用。
    """
    topic = payload.get("topic", "（空任务）")
    await asyncio.sleep(0.5)  # 模拟模型推理 + 工具执行耗时
    return {"echo": topic, "finished_at": time.time()}


# ---------- Worker 协程 ----------


async def worker(name: str, queue: asyncio.Queue[Job], store: TaskStore) -> None:
    while True:
        job = await queue.get()
        started = time.monotonic()
        store.update(job, status=STATUS_RUNNING, attempts=job.attempts + 1)
        logger.info("job_start", extra={"job_id": job.job_id, "attempt": job.attempts})

        try:
            result = await run_agent_task(job.payload)
            store.update(job, status=STATUS_SUCCEEDED, result=result)
            logger.info("job_succeeded", extra={
                "job_id": job.job_id,
                "elapsed_ms": int((time.monotonic() - started) * 1000),
            })
        except Exception as exc:  # 顶层兜底，按重试策略处理
            store.update(job, error=f"{type(exc).__name__}: {exc}")
            if job.attempts >= MAX_ATTEMPTS:
                store.update(job, status=STATUS_FAILED)
                logger.error("job_failed_permanent", extra={
                    "job_id": job.job_id, "error": str(exc),
                }, exc_info=True)
            else:
                delay = BACKOFF_SECONDS[min(job.attempts - 1, len(BACKOFF_SECONDS) - 1)]
                await asyncio.sleep(delay)
                await queue.put(job)  # 重新入队，等待下一次消费
                logger.warning("job_retry_scheduled", extra={
                    "job_id": job.job_id, "attempt": job.attempts, "backoff": delay,
                })
        finally:
            queue.task_done()


# ---------- 健康检查 ----------


async def health_handler(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    queue: asyncio.Queue[Job],
    store: TaskStore,
    started_at: float,
) -> None:
    try:
        request_line = await reader.readline()
        if not request_line:
            writer.close()
            return
        method, path, *_ = request_line.decode().split()
        if method == "GET" and path == "/healthz":
            body = {
                "status": "ok",
                "uptime_s": int(time.time() - started_at),
                "queue_depth": queue.qsize(),
                "stats": store.stats(),
            }
            payload = json.dumps(body, ensure_ascii=False).encode()
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: application/json; charset=utf-8\r\n"
                b"Content-Length: " + str(len(payload)).encode() + b"\r\n\r\n" + payload
            )
        else:
            writer.write(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
        await writer.drain()
    finally:
        writer.close()
        await writer.wait_closed()


# ---------- 主流程 ----------


async def main() -> None:
    configure_logging(os.getenv("LOG_LEVEL", "INFO"))
    concurrency = int(os.getenv("WORKER_CONCURRENCY", "3"))
    health_port = int(os.getenv("HEALTH_PORT", "8081"))
    started_at = time.time()

    queue: asyncio.Queue[Job] = asyncio.Queue()
    store = TaskStore()

    workers = [
        asyncio.create_task(worker(f"worker-{i}", queue, store))
        for i in range(concurrency)
    ]

    server = await asyncio.start_server(
        lambda r, w: health_handler(r, w, queue, store, started_at),
        host="0.0.0.0",
        port=health_port,
    )
    logger.info("health_server_started", extra={"port": health_port})

    for topic in ["整理本周技术周报", "检索并总结三份产品文档"]:
        job = Job(job_id=uuid.uuid4().hex[:8], payload={"topic": topic})
        store.put(job)
        await queue.put(job)
        logger.info("job_enqueued", extra={"job_id": job.job_id})

    await queue.join()

    for w in workers:
        w.cancel()
    server.close()
    await server.wait_closed()

    logger.info("all_done", extra={"stats": store.stats()})
    print(json.dumps(
        {"jobs": [job.__dict__ for job in store.all_jobs()]},
        ensure_ascii=False,
        indent=2,
        default=str,
    ))


if __name__ == "__main__":
    asyncio.run(main())
