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


class _GuardHook:
    """Intercepts 402 responses before x402's payment hook runs."""

    async def on_response(self, response):
        if response.status_code != 402:
            return

        await response.aread()
        data = response.json()
        url = str(response.request.url)
        result = validate_price(data)

        if not result["valid"]:
            _log_blocked(url, result)
            try:
                from colorama import Fore, Style
                print(f"{Fore.RED}{result['reason']}{Style.RESET_ALL}")
            except ImportError:
                print(result["reason"])
            raise PaymentBlockedError(result)


def protect(client):
    """Wrap an x402HttpxClient with DoorNo.402 price validation.

    Usage:
        client = protect(x402HttpxClient(account=account))
    """
    guard = _GuardHook()
    existing = client.event_hooks.get("response", [])
    client.event_hooks["response"] = [guard.on_response] + existing
    return client
