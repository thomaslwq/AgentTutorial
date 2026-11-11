"""第 14 章 · 按会话累计 token 的预算熔断。

三道防线：
- 软阈值（soft_ratio）：达到预算的一定比例后告警，可在此降级到更便宜的模型；
- 硬阈值：累计 token 达到上限，直接熔断，拒绝继续发起模型调用；
- 单次预估：调用前先估算本轮 token，超出剩余预算则提前拦截，避免「先扣钱再报错」。

预算口径按会话（session_id）累计，跨轮次生效；token 取自模型返回的 usage，
调用前的预估值可按历史均值或消息长度粗算。

运行：python budget_guard.py
"""
from __future__ import annotations

from dataclasses import dataclass, field


class BudgetExceededError(RuntimeError):
    """会话预算耗尽，熔断时抛出。"""


@dataclass
class SessionUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    calls: int = 0
    blocked: bool = False
    events: list[str] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class BudgetGuard:
    """按会话维护 token 预算与熔断状态。"""

    def __init__(
        self,
        max_total_tokens: int = 20000,
        soft_ratio: float = 0.8,
        max_calls: int = 20,
    ) -> None:
        self.max_total_tokens = max_total_tokens
        self.soft_ratio = soft_ratio
        self.max_calls = max_calls
        self._sessions: dict[str, SessionUsage] = {}

    def _get(self, session_id: str) -> SessionUsage:
        return self._sessions.setdefault(session_id, SessionUsage())

    def check(self, session_id: str, estimated_tokens: int = 0) -> str:
        """调用前预检，返回状态：``ok`` / ``warning`` / ``blocked``。

        estimated_tokens：本轮预估消耗（prompt 为主）。预检不通过抛异常，
        由上层决定是换模型、缩短上下文还是结束会话。
        """
        usage = self._get(session_id)
        if usage.blocked:
            raise BudgetExceededError(f"会话 {session_id} 已被熔断")

        projected = usage.total_tokens + estimated_tokens
        if projected >= self.max_total_tokens or usage.calls >= self.max_calls:
            usage.blocked = True
            usage.events.append(
                f"熔断：累计 {usage.total_tokens} token / {usage.calls} 次调用"
            )
            raise BudgetExceededError(
                f"会话 {session_id} 预算耗尽：累计 {usage.total_tokens} token，"
                f"本轮预估 {estimated_tokens}，上限 {self.max_total_tokens}"
            )

        if projected >= self.max_total_tokens * self.soft_ratio:
            usage.events.append(
                f"软阈值告警：已用 {usage.total_tokens}/{self.max_total_tokens} token"
            )
            return "warning"
        return "ok"

    def record(self, session_id: str, prompt_tokens: int, completion_tokens: int) -> None:
        """模型返回后回填真实 usage。"""
        usage = self._get(session_id)
        usage.prompt_tokens += prompt_tokens
        usage.completion_tokens += completion_tokens
        usage.calls += 1
        if usage.total_tokens >= self.max_total_tokens:
            usage.blocked = True
            usage.events.append("回填后触达硬阈值，熔断")

    def snapshot(self, session_id: str) -> dict:
        usage = self._get(session_id)
        return {
            "session_id": session_id,
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "calls": usage.calls,
            "blocked": usage.blocked,
            "remaining_tokens": max(0, self.max_total_tokens - usage.total_tokens),
            "events": usage.events,
        }


def _demo() -> None:
    guard = BudgetGuard(max_total_tokens=1000, soft_ratio=0.8, max_calls=10)
    session = "demo-session"

    # 模拟多轮对话：每轮 prompt 200、completion 60，看软告警与熔断时机
    for turn in range(6):
        try:
            status = guard.check(session, estimated_tokens=200)
            print(f"第 {turn + 1} 轮：预检 {status}")
            guard.record(session, prompt_tokens=200, completion_tokens=60)
        except BudgetExceededError as exc:
            print(f"第 {turn + 1} 轮：熔断 → {exc}")
            break

    print("\n最终快照：")
    for key, value in guard.snapshot(session).items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    _demo()
