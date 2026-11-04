"""Spending guard for metered APIs: stop before a request would pass a cap."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

_EPS = 1e-9


class BudgetExceeded(RuntimeError):
    """The next request would pass the run cap or the daily cap."""


def _today() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%d")


@dataclass
class BudgetGuard:
    """Tracks spend for this run and, through a ledger file, across runs on the same UTC day.

    The ledger only knows about spend made through this guard. Other use of the same key or
    IP address counts against the real OpenAlex allowance and is invisible here.
    """

    run_cap_usd: float
    daily_cap_usd: float
    ledger_path: Path | None = None
    spent_run_usd: float = 0.0
    _spent_today_usd: float = field(default=0.0, init=False)

    def __post_init__(self) -> None:
        self._spent_today_usd = self._read_ledger().get(_today(), 0.0)

    def _read_ledger(self) -> dict[str, float]:
        if self.ledger_path is None or not self.ledger_path.exists():
            return {}
        return json.loads(self.ledger_path.read_text(encoding="utf-8"))

    def check(self, estimated_usd: float) -> None:
        if self.spent_run_usd + estimated_usd > self.run_cap_usd + _EPS:
            raise BudgetExceeded(
                f"run cap ${self.run_cap_usd:.4f}: spent ${self.spent_run_usd:.4f}, "
                f"next call about ${estimated_usd:.4f}"
            )
        if self._spent_today_usd + estimated_usd > self.daily_cap_usd + _EPS:
            raise BudgetExceeded(
                f"daily cap ${self.daily_cap_usd:.4f}: spent ${self._spent_today_usd:.4f} "
                f"today, next call about ${estimated_usd:.4f}"
            )

    def charge(self, usd: float) -> None:
        self.spent_run_usd += usd
        self._spent_today_usd += usd
        if self.ledger_path is not None:
            ledger = self._read_ledger()
            ledger[_today()] = round(self._spent_today_usd, 6)
            self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
            self.ledger_path.write_text(json.dumps(ledger, indent=2) + "\n", encoding="utf-8")
