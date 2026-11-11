"""第 13 章 · 本地 JSONL Trace 记录器。

不依赖任何外部观测平台，把一次 Agent 运行中的模型调用、工具调用、
token 消耗与耗时逐条写入 JSONL 文件，便于离线排查与评测统计。

JSONL 每行一个 Span 对象，结构与 OpenTelemetry 的 Trace/Span 概念对齐：
- trace_id：一次完整任务运行的标识；
- span_id：单个操作（一次模型调用 / 一次工具调用）的标识；
- parent_span_id：父子层级，用于还原调用树。

运行：python local_tracer.py
输出：traces.jsonl（同目录下）。
"""
from __future__ import annotations

import json
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Optional


@dataclass
class Span:
    """单个可观测单元。"""

    trace_id: str
    span_id: str
    parent_span_id: Optional[str]
    name: str
    span_type: str  # chain / llm / tool
    start_ts: float
    end_ts: Optional[float] = None
    attributes: dict = field(default_factory=dict)
    token: dict = field(default_factory=dict)  # prompt / completion / total

    def to_record(self) -> dict:
        record = {
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_span_id": self.parent_span_id,
            "name": self.name,
            "span_type": self.span_type,
            "start_ts": round(self.start_ts, 6),
            "end_ts": round(self.end_ts, 6) if self.end_ts else None,
            "duration_ms": round((self.end_ts - self.start_ts) * 1000, 2)
            if self.end_ts
            else None,
            "attributes": self.attributes,
            "token": self.token,
        }
        return record


class LocalTracer:
    """把 Span 缓冲后批量落盘为 JSONL。

    用法一：显式开始 / 结束
        tracer = LocalTracer("traces.jsonl")
        span_id = tracer.start_span(trace_id, "llm-call", "llm", attributes={...})
        tracer.end_span(span_id, token={"prompt": 120, "completion": 30})

    用法二：上下文管理器
        with tracer.span(trace_id, "tool-search", "tool") as span_id:
            ...
    """

    def __init__(self, output_path: str = "traces.jsonl") -> None:
        self.output_path = Path(output_path)
        self._spans: dict[str, Span] = {}

    # ── 基础 Span 操作 ──────────────────────────────────────────────

    @staticmethod
    def new_trace_id() -> str:
        return f"trace-{uuid.uuid4().hex[:12]}"

    def start_span(
        self,
        trace_id: str,
        name: str,
        span_type: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> str:
        span_id = f"span-{uuid.uuid4().hex[:10]}"
        self._spans[span_id] = Span(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            name=name,
            span_type=span_type,
            start_ts=time.perf_counter(),
            attributes=attributes or {},
        )
        return span_id

    def end_span(
        self,
        span_id: str,
        token: Optional[dict] = None,
        attributes: Optional[dict] = None,
    ) -> None:
        span = self._spans[span_id]
        span.end_ts = time.perf_counter()
        if token:
            span.token = token
        if attributes:
            span.attributes.update(attributes)

    @contextmanager
    def span(
        self,
        trace_id: str,
        name: str,
        span_type: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[dict] = None,
    ) -> Iterator[str]:
        span_id = self.start_span(trace_id, name, span_type, parent_span_id, attributes)
        try:
            yield span_id
        finally:
            self.end_span(span_id)

    # ── 业务语义化封装 ──────────────────────────────────────────────

    def record_llm_call(
        self,
        trace_id: str,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        latency_ms: float,
        parent_span_id: Optional[str] = None,
        message_preview: str = "",
    ) -> None:
        """记录一次模型调用：模型名、token 用量、耗时、输入预览。"""
        span_id = self.start_span(
            trace_id,
            name=f"llm:{model}",
            span_type="llm",
            parent_span_id=parent_span_id,
            attributes={"model": model, "message_preview": message_preview[:200]},
        )
        span = self._spans[span_id]
        span.start_ts = time.perf_counter() - latency_ms / 1000
        span.end_ts = time.perf_counter()
        span.token = {
            "prompt": prompt_tokens,
            "completion": completion_tokens,
            "total": prompt_tokens + completion_tokens,
        }

    def record_tool_call(
        self,
        trace_id: str,
        tool_name: str,
        arguments: dict,
        result_preview: str,
        latency_ms: float,
        parent_span_id: Optional[str] = None,
        status: str = "ok",
    ) -> None:
        """记录一次工具调用：工具名、入参、结果预览、耗时、状态。"""
        span_id = self.start_span(
            trace_id,
            name=f"tool:{tool_name}",
            span_type="tool",
            parent_span_id=parent_span_id,
            attributes={
                "tool": tool_name,
                "arguments": arguments,
                "result_preview": result_preview[:200],
                "status": status,
            },
        )
        span = self._spans[span_id]
        span.start_ts = time.perf_counter() - latency_ms / 1000
        span.end_ts = time.perf_counter()

    # ── 落盘与汇总 ─────────────────────────────────────────────────

    def flush(self) -> None:
        """把缓冲的 Span 追加写入 JSONL，并清空缓冲。"""
        records = [span.to_record() for span in self._spans.values()]
        with self.output_path.open("a", encoding="utf-8") as f:
            for record in records:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        self._spans.clear()

    def trace_summary(self, trace_id: str) -> dict:
        """汇总单个 trace 的总 token、总耗时、Span 数量。"""
        spans = [s for s in self._spans.values() if s.trace_id == trace_id]
        prompt = sum(s.token.get("prompt", 0) for s in spans)
        completion = sum(s.token.get("completion", 0) for s in spans)
        durations = [
            (s.end_ts - s.start_ts) * 1000 for s in spans if s.end_ts and s.start_ts
        ]
        return {
            "trace_id": trace_id,
            "span_count": len(spans),
            "prompt_tokens": prompt,
            "completion_tokens": completion,
            "total_tokens": prompt + completion,
            "total_latency_ms": round(sum(durations), 2),
        }


def _demo() -> None:
    """离线演示：伪造一轮 Agent 运行，写入 traces.jsonl。"""
    tracer = LocalTracer("traces.jsonl")
    trace_id = tracer.new_trace_id()

    root = tracer.start_span(trace_id, "agent-run", "chain",
                             attributes={"task": "北京今天天气如何"})

    llm_span = tracer.start_span(trace_id, "llm:gpt-4o-mini", "llm", parent_span_id=root)
    tracer.end_span(llm_span, token={"prompt": 128, "completion": 42},
                    attributes={"decision": "call_tool"})

    tool_span = tracer.start_span(trace_id, "tool:weather", "tool", parent_span_id=root)
    tracer.end_span(tool_span, attributes={"arguments": {"city": "北京"},
                                            "status": "ok"})

    llm_span2 = tracer.start_span(trace_id, "llm:gpt-4o-mini", "llm", parent_span_id=root)
    tracer.end_span(llm_span2, token={"prompt": 180, "completion": 65})

    tracer.end_span(root)
    print("trace 汇总：", json.dumps(tracer.trace_summary(trace_id), ensure_ascii=False))
    tracer.flush()
    print(f"已写入 {tracer.output_path}")


if __name__ == "__main__":
    _demo()
