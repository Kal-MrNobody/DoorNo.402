from datetime import datetime, timezone

from .validators.price import validate_price


class PaymentBlockedError(Exception):
    def __init__(self, result: dict):
        self.result = result
        super().__init__(result["reason"])


def _log_blocked(url: str, result: dict):
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"{ts} | {url} | "
        f"described=${result.get('described', '?'):.2f} | "
        f"demanded=${result.get('demanded', '?'):.2f} | "
        f"inflation={result.get('inflation_pct', 0):.0f}%\n"
    )
    with open("blocked_payments.log", "a") as f:
        f.write(line)
