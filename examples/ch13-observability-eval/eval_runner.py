"""第 13 章 · 评测集打分脚本（纯本地，不依赖外部服务）。

覆盖四类基础指标：
- 任务成功率：回答是否命中预期关键词；
- 工具调用正确率：实际调用的工具集合是否与预期一致；
- 延迟：每条用例的耗时（毫秒）；
- token 消耗：prompt / completion / total。

默认使用内置样例数据集 + 桩函数跑通流程；接入真实 Agent 时，
把 ``run_case`` 替换为你自己的执行函数即可，评分逻辑保持不变。

运行：
    python eval_runner.py                      # 内置样例
    python eval_runner.py dataset.json         # 外部 JSON 评测集
    python eval_runner.py dataset.json --output report.json
"""
from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable


# ── 评测集结构 ──────────────────────────────────────────────────────

@dataclass
class EvalCase:
    case_id: str
    question: str
    expected_tools: list[str]          # 预期应调用的工具名集合
    expected_keywords: list[str]       # 回答中必须出现的关键词
    notes: str = ""


@dataclass
class CaseResult:
    case_id: str
    answer: str
    tools_called: list[str]
    latency_ms: float
    token: dict = field(default_factory=dict)


@dataclass
class ScoredCase:
    result: CaseResult
    success: bool
    keyword_hit: float                 # 关键词命中率 0~1
    tool_match: bool                   # 工具集合是否完全一致
    tool_precision: float
    tool_recall: float


# ── 内置样例数据集 ──────────────────────────────────────────────────

SAMPLE_DATASET: list[EvalCase] = [
    EvalCase(
        case_id="case-01",
        question="北京今天天气怎么样？",
        expected_tools=["weather"],
        expected_keywords=["北京", "晴"],
        notes="单工具查询",
    ),
    EvalCase(
        case_id="case-02",
        question="帮我查一下上海的气温并对比深圳的气温。",
        expected_tools=["weather"],
        expected_keywords=["上海", "深圳"],
        notes="同一工具两次调用",
    ),
    EvalCase(
        case_id="case-03",
        question="把这篇文档的摘要存到知识库。",
        expected_tools=["kb_upsert"],
        expected_keywords=["已保存", "知识库"],
        notes="写操作工具",
    ),
    EvalCase(
        case_id="case-04",
        question="现在几点了？",
        expected_tools=["get_time"],
        expected_keywords=["点"],
        notes="桩函数故意不调工具，用于暴露工具正确率问题",
    ),
]


# ── 桩执行器：离线演示用，接入真实 Agent 时替换本函数 ──────────────

def stub_runner(case: EvalCase) -> CaseResult:
    """按样例问题返回伪造的执行结果。

    真实接入时，此处应调用你的 Agent 循环，从 trace / usage 中取出
    answer、工具列表、延迟与 token（可结合 local_tracer.py）。
    """
    canned: dict[str, CaseResult] = {
        "case-01": CaseResult(
            case_id="case-01",
            answer="北京今天晴，气温 12~20℃。",
            tools_called=["weather"],
            latency_ms=860.0,
            token={"prompt": 132, "completion": 38, "total": 170},
        ),
        "case-02": CaseResult(
            case_id="case-02",
            answer="上海 15℃，深圳 23℃，深圳更暖和。",
            tools_called=["weather", "weather"],
            latency_ms=1420.0,
            token={"prompt": 176, "completion": 55, "total": 231},
        ),
        "case-03": CaseResult(
            case_id="case-03",
            answer="文档摘要已保存到知识库。",
            tools_called=["kb_upsert"],
            latency_ms=640.0,
            token={"prompt": 158, "completion": 41, "total": 199},
        ),
        "case-04": CaseResult(
            case_id="case-04",
            answer="现在是下午三点左右。",
            tools_called=[],  # 预期 get_time，实际未调用
            latency_ms=310.0,
            token={"prompt": 96, "completion": 22, "total": 118},
        ),
    }
    return canned[case.case_id]


# ── 评分逻辑 ───────────────────────────────────────────────────────

def _keyword_hit(answer: str, keywords: list[str]) -> float:
    if not keywords:
        return 1.0
    hit = sum(1 for kw in keywords if kw.lower() in answer.lower())
    return hit / len(keywords)


def _tool_set_metrics(expected: list[str], actual: list[str]) -> tuple[bool, float, float]:
    exp, act = set(expected), set(actual)
    if not exp and not act:
        return True, 1.0, 1.0
    if not act:
        return False, 0.0, 0.0
    precision = len(exp & act) / len(act)
    recall = len(exp & act) / len(exp)
    return exp == act, precision, recall


def score_case(case: EvalCase, result: CaseResult) -> ScoredCase:
    hit = _keyword_hit(result.answer, case.expected_keywords)
    tool_match, precision, recall = _tool_set_metrics(case.expected_tools, result.tools_called)
    return ScoredCase(
        result=result,
        success=hit >= 1.0,  # 任务成功口径：关键词全部命中
        keyword_hit=round(hit, 3),
        tool_match=tool_match,
        tool_precision=round(precision, 3),
        tool_recall=round(recall, 3),
    )


def summarize(scored: list[ScoredCase]) -> dict:
    n = len(scored)
    latencies = [s.result.latency_ms for s in scored]
    totals = [s.result.token.get("total", 0) for s in scored]
    summary = {
        "case_count": n,
        "task_success_rate": round(sum(s.success for s in scored) / n, 3),
        "tool_match_rate": round(sum(s.tool_match for s in scored) / n, 3),
        "avg_latency_ms": round(statistics.mean(latencies), 2),
        "p50_latency_ms": round(statistics.median(latencies), 2),
        "total_tokens": sum(totals),
        "avg_tokens": round(statistics.mean(totals), 2),
    }
    return summary


def load_dataset(path: Path) -> list[EvalCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return [
        EvalCase(
            case_id=item["case_id"],
            question=item["question"],
            expected_tools=item.get("expected_tools", []),
            expected_keywords=item.get("expected_keywords", []),
            notes=item.get("notes", ""),
        )
        for item in raw
    ]


def run(
    dataset: list[EvalCase],
    runner: Callable[[EvalCase], CaseResult] = stub_runner,
) -> tuple[list[ScoredCase], dict]:
    scored: list[ScoredCase] = []
    for case in dataset:
        started = time.perf_counter()
        result = runner(case)
        # 若执行器未回填延迟，用本地计时兜底
        if not result.latency_ms:
            result.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        scored.append(score_case(case, result))
    return scored, summarize(scored)


def _print_report(scored: list[ScoredCase], summary: dict) -> None:
    print(f"{'用例':<10}{'成功':<6}{'关键词命中':<10}{'工具匹配':<8}"
          f"{'延迟(ms)':<10}{'token'}")
    for s in scored:
        print(f"{s.result.case_id:<10}{'✓' if s.success else '✗':<6}"
              f"{s.keyword_hit:<10}{'✓' if s.tool_match else '✗':<8}"
              f"{s.result.latency_ms:<10}{s.result.token.get('total', 0)}")
    print("\n汇总指标：")
    for key, value in summary.items():
        print(f"  {key}: {value}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Agent 评测集打分脚本")
    parser.add_argument("dataset", nargs="?", type=Path, help="外部 JSON 评测集（可选）")
    parser.add_argument("--output", type=Path, help="把报告写入 JSON 文件（可选）")
    args = parser.parse_args()

    dataset = load_dataset(args.dataset) if args.dataset else SAMPLE_DATASET
    scored, summary = run(dataset)
    _print_report(scored, summary)

    if args.output:
        report = {
            "summary": summary,
            "cases": [
                {
                    "case_id": s.result.case_id,
                    "success": s.success,
                    "keyword_hit": s.keyword_hit,
                    "tool_match": s.tool_match,
                    "tool_precision": s.tool_precision,
                    "tool_recall": s.tool_recall,
                    "latency_ms": s.result.latency_ms,
                    "token": s.result.token,
                    "answer": s.result.answer,
                }
                for s in scored
            ],
        }
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2),
                               encoding="utf-8")
        print(f"\n报告已写入 {args.output}")


if __name__ == "__main__":
    main()
