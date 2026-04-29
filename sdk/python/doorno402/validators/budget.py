"""Daily budget tracker for x402 payment protection.

Tracks cumulative spending per calendar day (UTC).
If the next payment would exceed the daily limit, the SDK blocks it.
Budget tracking is in-memory and resets each day.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Optional


@dataclass
class BudgetStatus:
    allowed: bool
    daily_limit: float
    spent_today: float
    remaining: float
    requested: float
    reason: str


class BudgetTracker:
    """In-memory daily budget tracker.

    Usage:
        tracker = BudgetTracker(daily_limit=5.00)
        status = tracker.check(amount_usd=0.50)
        if status.allowed:
            tracker.record(0.50)
    """

    def __init__(self, daily_limit: float):
        self.daily_limit = daily_limit
        self._spent: float = 0.0
        self._current_day: str = self._today()

    @staticmethod
    def _today() -> str:
        return datetime.now(timezone.utc).strftime("%Y-%m-%d")

    def _rotate_if_new_day(self):
        today = self._today()
        if today != self._current_day:
            self._spent = 0.0
            self._current_day = today

    def check(self, amount_usd: float) -> BudgetStatus:
        """Check if a payment fits within the daily budget.

        Does NOT record the spend -- call record() after successful payment.
        """
        self._rotate_if_new_day()
        remaining = self.daily_limit - self._spent

        if amount_usd > remaining:
            return BudgetStatus(
                allowed=False,
                daily_limit=self.daily_limit,
                spent_today=self._spent,
                remaining=remaining,
                requested=amount_usd,
                reason=(
                    f"[DoorNo.402] BLOCKED -- daily budget exceeded: "
                    f"spent ${self._spent:.2f} / ${self.daily_limit:.2f}, "
                    f"remaining ${remaining:.2f}, "
                    f"requested ${amount_usd:.2f}"
                ),
            )

        return BudgetStatus(
            allowed=True,
            daily_limit=self.daily_limit,
            spent_today=self._spent,
            remaining=remaining,
            requested=amount_usd,
            reason="within budget",
        )

    def record(self, amount_usd: float):
        """Record a completed payment against today's budget."""
        self._rotate_if_new_day()
        self._spent += amount_usd

    @property
    def spent_today(self) -> float:
        self._rotate_if_new_day()
        return self._spent

    @property
    def remaining(self) -> float:
        self._rotate_if_new_day()
        return self.daily_limit - self._spent
