"""DoorNo.402 Guard — unified x402 payment interceptor.

Runs all security validators in sequence on every 402 response:
  1. VULN-01 — Price inflation check
  2. VULN-02 — ENS recipient trust score
  3. VULN-04 — Prompt injection scan + sanitize
  4. VULN-05 — Daily budget enforcement
"""

from datetime import datetime, timezone
from typing import Optional

from .validators.price import validate_price, convert_raw_to_usd
from .validators.ens_verifier import calculate_trust_score, TrustScore
from .validators.injection import validate_injection
from .validators.budget import BudgetTracker, BudgetStatus


class PaymentBlockedError(Exception):
    def __init__(self, result: dict):
        self.result = result
        super().__init__(result.get("reason", "payment blocked"))


def _log_blocked(url: str, result: dict):
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"{ts} | {url} | "
        f"reason={result.get('reason', 'unknown')}\n"
    )
    with open("blocked_payments.log", "a") as f:
        f.write(line)


def _log_flagged(url: str, trust: TrustScore):
    ts = datetime.now(timezone.utc).isoformat()
    line = (
        f"{ts} | {url} | FLAGGED | "
        f"score={trust.trust_score}/90 | "
        f"ens={trust.ens_name or 'none'} | "
        f"action={trust.action}\n"
    )
    with open("blocked_payments.log", "a") as f:
        f.write(line)


def _log_injection(url: str, result: dict):
    ts = datetime.now(timezone.utc).isoformat()
    patterns = ", ".join(result.get("patterns_matched", []))
    line = (
        f"{ts} | {url} | INJECTION | "
        f"patterns={patterns}\n"
    )
    with open("blocked_payments.log", "a") as f:
        f.write(line)


def _print_color(msg: str, color: str = "red"):
    try:
        from colorama import Fore, Style
        colors = {"red": Fore.RED, "yellow": Fore.YELLOW, "green": Fore.GREEN}
        print(f"{colors.get(color, Fore.RED)}{msg}{Style.RESET_ALL}")
    except ImportError:
        print(msg)


class _GuardHook:
    """Intercepts 402 responses before x402's payment hook runs."""
    def __init__(
        self,
        mainnet_rpc_url: Optional[str] = None,
        budget_tracker: Optional[BudgetTracker] = None,
        raise_on_block: bool = False,
    ):
        self.mainnet_rpc_url = mainnet_rpc_url
        self.budget_tracker = budget_tracker
        self.raise_on_block = raise_on_block

    async def on_response(self, response):
        if response.status_code != 402:
            return

        await response.aread()
        data = response.json()
        url = str(response.request.url)
        accepts = data.get("accepts", [])

        if not accepts:
            return

        req = accepts[0]

        # ── VULN-04: Prompt Injection ──
        injection_result = validate_injection(data)
        if injection_result.get("injection_detected"):
            _log_injection(url, injection_result)
            _print_color(injection_result["reason"], "yellow")
            # Sanitize description in-place so downstream LLMs see clean text
            req["description"] = injection_result["sanitized_description"]

        # ── VULN-01: Price Inflation ──
        price_result = validate_price(data)
        if not price_result["valid"]:
            _log_blocked(url, price_result)
            _print_color(f"[DoorNo.402] [BLOCKED] PAYMENT BLOCKED: {price_result['reason']}")
            if self.raise_on_block:
                raise PaymentBlockedError(price_result)
            response.status_code = 403
            return

        # ── VULN-02: ENS Trust Score ──
        pay_to = req.get("payTo", "")
        if pay_to:
            trust = calculate_trust_score(
                pay_to=pay_to,
                price_valid=price_result["valid"],
                mainnet_rpc_url=self.mainnet_rpc_url,
            )

            if trust.action == "block":
                result = {
                    "valid": False,
                    "reason": trust.warning or f"low trust score: {trust.trust_score}/90",
                    "trust_score": trust.to_dict(),
                }
                _log_blocked(url, result)
                _print_color(f"[DoorNo.402] [BLOCKED] PAYMENT BLOCKED: {result['reason']}")
                if self.raise_on_block:
                    raise PaymentBlockedError(result)
                response.status_code = 403
                return

            if trust.action == "flag":
                _log_flagged(url, trust)
                _print_color(
                    f"[DoorNo.402] WARNING -- {trust.warning}",
                    "yellow"
                )
                # Flag but allow -- developer can inspect trust_score
                # Attach trust score to response headers for inspection
                response.headers["X-DoorNo402-Trust-Score"] = str(trust.trust_score)
                response.headers["X-DoorNo402-ENS"] = trust.ens_name or "none"

        # ── VULN-05: Budget Drain ──
        if self.budget_tracker:
            raw = int(req.get("maxAmountRequired", 0))
            demanded_usd = convert_raw_to_usd(raw)
            budget_status = self.budget_tracker.check(demanded_usd)

            if not budget_status.allowed:
                result = {
                    "valid": False,
                    "reason": budget_status.reason,
                    "budget": {
                        "daily_limit": budget_status.daily_limit,
                        "spent_today": budget_status.spent_today,
                        "remaining": budget_status.remaining,
                        "requested": budget_status.requested,
                    },
                }
                _log_blocked(url, result)
                _print_color(f"[DoorNo.402] [BLOCKED] PAYMENT BLOCKED: {budget_status.reason}")
                if self.raise_on_block:
                    raise PaymentBlockedError(result)
                response.status_code = 403
                return

            # Record the spend (payment will proceed)
            self.budget_tracker.record(demanded_usd)
            remaining = self.budget_tracker.remaining
            _print_color(
                f"[DoorNo.402] Budget: ${demanded_usd:.2f} approved -- "
                f"${remaining:.2f} remaining today",
                "green"
            )


def protect(
    client,
    daily_budget: Optional[float] = None,
    mainnet_rpc_url: Optional[str] = None,
    raise_on_block: bool = False,
):
    """Wrap an x402HttpxClient with DoorNo.402 security.

    Covers:
      - VULN-01: Price inflation check
      - VULN-02: ENS recipient trust scoring
      - VULN-04: Prompt injection scan + sanitize
      - VULN-05: Daily budget enforcement (optional)

    Usage:
        client = protect(x402HttpxClient(account=account))
        client = protect(client, daily_budget=5.00)

    Args:
        client: An httpx client (typically x402HttpxClient).
        daily_budget: Optional daily spending limit in USD.
        mainnet_rpc_url: Ethereum mainnet RPC for ENS lookups.
        raise_on_block: If True, raises PaymentBlockedError. If False, silently converts to HTTP 403.
    """
    tracker = BudgetTracker(daily_budget) if daily_budget else None
    guard = _GuardHook(
        mainnet_rpc_url=mainnet_rpc_url,
        budget_tracker=tracker,
        raise_on_block=raise_on_block,
    )
    existing = client.event_hooks.get("response", [])
    client.event_hooks["response"] = [guard.on_response] + existing
    return client
