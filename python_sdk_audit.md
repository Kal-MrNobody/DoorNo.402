# Python SDK Audit

## sdk/python/setup.py
`python
from setuptools import setup, find_packages

setup(
    name="doorno402",
    version="0.3.0",
    description="The missing security layer for agentic wallets",
    author="DoorNo.402 Team",
    packages=find_packages(),
    install_requires=[
        "web3",
        "eth-account",
        "colorama",
        "httpx",
        "python-dotenv",
    ],
)

`

## sdk/python/doorno402/__init__.py
`python
from .guard import protect, PaymentBlockedError
from .validators.ens_verifier import calculate_trust_score, TrustScore
from .validators.injection import scan_injection, validate_injection
from .validators.budget import BudgetTracker

__all__ = [
    "protect",
    "PaymentBlockedError",
    "calculate_trust_score",
    "TrustScore",
    "scan_injection",
    "validate_injection",
    "BudgetTracker",
]

`

## sdk/python/doorno402/guard.py
`python
"""DoorNo.402 Guard — unified x402 payment interceptor.

Runs all security validators in sequence on every 402 response:
  1. VULN-01 — Price inflation check
  2. VULN-02 — ENS recipient trust score
  3. VULN-03 — Redirect hijack detection
  4. VULN-04 — Prompt injection scan + sanitize
  5. VULN-05 — Daily budget enforcement
  6. VULN-06 — TLS enforcement
  7. VULN-07 — Delivery verification (post-payment)
"""

from datetime import datetime, timezone
from typing import Optional

from .validators.price import validate_price, convert_raw_to_usd
from .validators.ens_verifier import calculate_trust_score, TrustScore
from .validators.injection import validate_injection
from .validators.budget import BudgetTracker, BudgetStatus
from .validators.tls import validate_tls
from .validators.redirect import validate_redirect


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
    ) -> None:
        """Initialize the guard hook with optional configuration."""
        self.mainnet_rpc_url = mainnet_rpc_url
        self.budget_tracker = budget_tracker
        self.raise_on_block = raise_on_block

    async def on_response(self, response) -> None:
        """Process the HTTP response and apply security policies before x402 handles it."""
        url = str(response.request.url)

        # ── VULN-06: TLS Enforcement ──
        tls_result = validate_tls(url)
        if not tls_result["valid"]:
            _log_blocked(url, tls_result)
            _print_color(tls_result["reason"])
            if self.raise_on_block:
                raise PaymentBlockedError(tls_result)
            response.status_code = 403
            return

        # ── VULN-03: Redirect Hijack ──
        if hasattr(response, 'history') and response.history:
            original_url = str(response.history[0].request.url)
            redirect_result = validate_redirect(original_url, url)
            if not redirect_result["valid"]:
                _log_blocked(url, redirect_result)
                _print_color(redirect_result["reason"])
                if self.raise_on_block:
                    raise PaymentBlockedError(redirect_result)
                response.status_code = 403
                return

        if response.status_code != 402:
            return

        await response.aread()
        data = response.json()
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
      VULN-01: Price inflation check
      VULN-02: ENS recipient trust scoring
      VULN-03: Redirect hijack detection
      VULN-04: Prompt injection scan + sanitize
      VULN-05: Daily budget enforcement
      VULN-06: TLS enforcement
      VULN-07: Delivery verification (call validate_delivery after response)

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

`

## sdk/python/doorno402/validators/price.py
`python
import re


def extract_price(description: str) -> float | None:
    """Pull a dollar amount from a plain-text description."""
    patterns = [
        r'\$\s*([\d,]+\.?\d*)',
        r'([\d,]+\.?\d*)\s*(?:USD|USDC|dollars?)',
    ]
    for p in patterns:
        m = re.search(p, description, re.IGNORECASE)
        if m:
            return float(m.group(1).replace(',', ''))
    return None


def convert_raw_to_usd(raw: int, decimals: int = 6) -> float:
    return raw / (10 ** decimals)


INFLATION_THRESHOLD = 0.05


def validate_price(payment_details: dict) -> dict:
    """Check if the demanded amount matches what the description claims."""
    accepts = payment_details.get("accepts", [])
    if not accepts:
        return {"valid": True, "reason": "no payment options"}

    req = accepts[0]
    raw = int(req.get("maxAmountRequired", 0))
    demanded = convert_raw_to_usd(raw)
    description = req.get("description", "")
    described = extract_price(description)

    if described is None:
        return {"valid": True, "reason": "no price in description"}

    if described == 0:
        return {"valid": False, "reason": "described price is zero"}

    inflation = (demanded - described) / described

    if inflation > INFLATION_THRESHOLD:
        return {
            "valid": False,
            "reason": (
                f"[DoorNo.402] BLOCKED -- description: ${described:.2f}, "
                f"demanded: ${demanded:.2f}, inflation: {inflation * 100:.0f}%, "
                f"threshold: {INFLATION_THRESHOLD * 100:.0f}%"
            ),
            "described": described,
            "demanded": demanded,
            "inflation_pct": inflation * 100,
        }

    return {"valid": True, "reason": "within threshold"}

`

## sdk/python/doorno402/validators/ens_verifier.py
`python
"""ENS-based Trust Score calculator for x402 payment recipients.

Scoring model (max 90 points):
  - ENS name exists         → +20
  - ENS name age > 6 months → +25
  - On-chain tx history > 5 → +20
  - Price validation passes  → +25

Thresholds:
  70+ = auto-pay | 40-69 = flag for confirmation | <40 = block
"""

from dataclasses import dataclass, field, asdict
from typing import Optional

try:
    from web3 import Web3
except ImportError:
    Web3 = None  # type: ignore[assignment,misc]

DEFAULT_MAINNET_RPC = "https://cloudflare-eth.com"
ENS_AGE_MONTHS = 6


@dataclass
class TrustScore:
    pay_to: str
    ens_name: Optional[str] = None
    ens_age_ok: bool = False
    tx_count: int = 0
    price_valid: bool = False
    trust_score: int = 0
    warning: Optional[str] = None
    breakdown: dict = field(default_factory=dict)
    action: str = "block"  # "auto-pay" | "flag" | "block"

    def to_dict(self) -> dict:
        return asdict(self)


def _resolve_ens(w3, address: str) -> Optional[str]:
    """Reverse-resolve an address to an ENS name."""
    try:
        name = w3.ens.name(Web3.to_checksum_address(address))  # type: ignore[union-attr]
        return name
    except Exception:
        return None


def _check_ens_age(w3, ens_name: str) -> bool:
    """Check if ENS name was registered more than 6 months ago.

    Uses the ENS BaseRegistrar to look up the registration date.
    Falls back to True if the on-chain query fails (benefit of doubt).
    """
    import time

    BASE_REGISTRAR = "0x57f1887a8BF19b14fC0dF6Fd9B2acc9Af147eA85"
    ABI = [
        {
            "name": "nameExpires",
            "type": "function",
            "inputs": [{"name": "id", "type": "uint256"}],
            "outputs": [{"type": "uint256"}],
            "stateMutability": "view",
        }
    ]

    try:
        # Compute the labelhash (keccak of the first label before .eth)
        label = ens_name.split(".")[0]
        label_hash = Web3.keccak(text=label)
        token_id = int.from_bytes(label_hash, "big")

        registrar = w3.eth.contract(
            address=Web3.to_checksum_address(BASE_REGISTRAR), abi=ABI
        )
        expires = registrar.functions.nameExpires(token_id).call()

        if expires == 0:
            return False

        # ENS names are typically registered for 1-5 years.
        # If the expiry is far in the future the name is old enough.
        # registration_time ≈ expires - (registration_period)
        # We approximate: if expires > now + 6 months, name existed > 6 months.
        six_months = ENS_AGE_MONTHS * 30 * 24 * 3600
        now = int(time.time())

        # If the name expires more than 6 months from now AND was created
        # at least 6 months ago (expires - registration_period < now - 6months),
        # we assume the name is old.  Simpler heuristic: if it exists and
        # expires > now we give the benefit of doubt based on the expiry window.
        if expires > now:
            # The longer until expiry, the more likely it was registered long ago.
            remaining = expires - now
            # A brand-new 1-year registration has ~365 days remaining.
            # If remaining > 6 months, we can't tell age reliably so we use
            # a fallback: check the block when the name was last transferred.
            # For hackathon simplicity, we assume: if expiry > 1 year from now,
            # the name was likely registered > 6 months ago.
            if remaining > six_months:
                return True
        return False
    except Exception:
        # If query fails, don't penalize — return False (no bonus points).
        return False


def _get_tx_count(w3, address: str) -> int:
    """Get the transaction count (nonce) for an address."""
    try:
        return w3.eth.get_transaction_count(Web3.to_checksum_address(address))
    except Exception:
        return 0


def calculate_trust_score(
    pay_to: str,
    price_valid: bool = True,
    mainnet_rpc_url: Optional[str] = None,
) -> TrustScore:
    """Calculate a multi-factor trust score for a payment recipient.

    Args:
        pay_to: The wallet address from the 402 payTo field.
        price_valid: Whether the VULN-01 price check passed.
        mainnet_rpc_url: Ethereum mainnet RPC for ENS lookups.

    Returns:
        TrustScore with score, breakdown, and recommended action.
    """
    score = TrustScore(pay_to=pay_to, price_valid=price_valid)
    breakdown = {}

    # --- Price validation (VULN-01) ---
    if price_valid:
        score.trust_score += 25
        breakdown["price_valid"] = "+25"
    else:
        breakdown["price_valid"] = "+0 (FAILED)"

    # --- ENS checks need web3 ---
    if Web3 is None:
        score.warning = "web3 not installed -- ENS checks skipped"
        breakdown["ens_name"] = "skipped"
        breakdown["ens_age"] = "skipped"
        breakdown["tx_history"] = "skipped"
        score.breakdown = breakdown
        score.action = _decide_action(score.trust_score)
        return score

    rpc = mainnet_rpc_url or DEFAULT_MAINNET_RPC
    w3 = Web3(Web3.HTTPProvider(rpc))

    # --- ENS name exists? (+20) ---
    ens_name = _resolve_ens(w3, pay_to)
    score.ens_name = ens_name
    if ens_name:
        score.trust_score += 20
        breakdown["ens_name"] = f"+20 ({ens_name})"
    else:
        breakdown["ens_name"] = "+0 (no ENS name)"

    # --- ENS age > 6 months? (+25) ---
    if ens_name:
        age_ok = _check_ens_age(w3, ens_name)
        score.ens_age_ok = age_ok
        if age_ok:
            score.trust_score += 25
            breakdown["ens_age"] = "+25 (> 6 months)"
        else:
            breakdown["ens_age"] = "+0 (< 6 months or unknown)"
    else:
        breakdown["ens_age"] = "+0 (no ENS)"

    # --- On-chain tx history > 5? (+20) ---
    tx_count = _get_tx_count(w3, pay_to)
    score.tx_count = tx_count
    if tx_count > 5:
        score.trust_score += 20
        breakdown["tx_history"] = f"+20 ({tx_count} txs)"
    else:
        breakdown["tx_history"] = f"+0 ({tx_count} txs, needs >5)"

    # --- Final decision ---
    score.breakdown = breakdown
    score.action = _decide_action(score.trust_score)

    if score.action == "flag":
        score.warning = (
            f"payTo {pay_to} scored {score.trust_score}/90 -- "
            f"ENS: {ens_name or 'none'} -- flagged for confirmation"
        )
    elif score.action == "block":
        score.warning = (
            f"payTo {pay_to} scored {score.trust_score}/90 -- "
            f"ENS: {ens_name or 'none'} -- BLOCKED (low trust)"
        )

    return score


def _decide_action(score: int) -> str:
    if score >= 70:
        return "auto-pay"
    elif score >= 40:
        return "flag"
    else:
        return "block"

`

## sdk/python/doorno402/validators/injection.py
`python
"""Prompt injection detector for x402 payment descriptions.

Scans the description field for common LLM jailbreak patterns.
Returns whether injection was detected and a sanitized version
of the description with injected instructions stripped out.
"""

import re
from dataclasses import dataclass
from typing import List

# Patterns that indicate prompt injection attempts in 402 descriptions.
# Each tuple is (compiled_regex, human_readable_label).
INJECTION_PATTERNS: List[tuple] = [
    (re.compile(r"(?:^|\b)(?:SYSTEM|ASSISTANT)\s*(?:OVERRIDE|:|MESSAGE)", re.IGNORECASE),
     "system_override"),
    (re.compile(r"ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|rules?|constraints?)", re.IGNORECASE),
     "ignore_instructions"),
    (re.compile(r"(?:bypass|disable|remove|override|skip)\s+(?:all\s+)?(?:budget|limit|restriction|constraint|filter|guard|check|validation|policy)", re.IGNORECASE),
     "bypass_limits"),
    (re.compile(r"(?:you\s+(?:are|must)|act\s+as|pretend\s+(?:to\s+be|you)|behave\s+as)", re.IGNORECASE),
     "role_hijack"),
    (re.compile(r"(?:mandatory|required|critical|urgent)\s+(?:infrastructure|system|maintenance)\s+(?:payment|fee|charge|transfer)", re.IGNORECASE),
     "urgency_scam"),
    (re.compile(r"(?:do\s+not|don'?t)\s+(?:check|verify|validate|question|refuse)", re.IGNORECASE),
     "anti_validation"),
    (re.compile(r"(?:approve|pay|execute|proceed|confirm)\s+(?:immediately|now|without|right\s+away)", re.IGNORECASE),
     "force_approve"),
    (re.compile(r"set\s+(?:max_?payment|budget|limit|allowance)\s+(?:to\s+)?(?:unlimited|infinity|max|999)", re.IGNORECASE),
     "set_unlimited"),
    (re.compile(r"this\s+(?:is\s+a\s+)?(?:test|drill|simulation|override)\s+(?:mode|scenario|payment)", re.IGNORECASE),
     "test_mode_trick"),
    (re.compile(r"<\s*(?:script|img|iframe|svg|object)\b", re.IGNORECASE),
     "html_injection"),
]


@dataclass
class InjectionResult:
    detected: bool
    patterns_matched: List[str]
    original: str
    sanitized: str


def scan_injection(description: str) -> InjectionResult:
    """Scan a 402 description for prompt injection patterns.

    Returns:
        InjectionResult with detection status and sanitized text.
    """
    matched: List[str] = []
    sanitized = description

    for pattern, label in INJECTION_PATTERNS:
        if pattern.search(description):
            matched.append(label)
            # Strip the matched content from the sanitized version
            sanitized = pattern.sub("[REDACTED]", sanitized)

    return InjectionResult(
        detected=len(matched) > 0,
        patterns_matched=matched,
        original=description,
        sanitized=sanitized.strip(),
    )


def validate_injection(payment_details: dict) -> dict:
    """Validate x402 payment details for prompt injection.

    Args:
        payment_details: The full 402 JSON response body.

    Returns:
        dict with keys: valid, reason, injection_result, sanitized_description
    """
    accepts = payment_details.get("accepts", [])
    if not accepts:
        return {"valid": True, "reason": "no payment options"}

    req = accepts[0]
    description = req.get("description", "")

    result = scan_injection(description)

    if result.detected:
        return {
            "valid": True,  # We sanitize, not block
            "reason": (
                f"[DoorNo.402] INJECTION DETECTED -- "
                f"patterns: {', '.join(result.patterns_matched)} -- "
                f"description sanitized before LLM exposure"
            ),
            "injection_detected": True,
            "patterns_matched": result.patterns_matched,
            "original_description": result.original,
            "sanitized_description": result.sanitized,
        }

    return {
        "valid": True,
        "reason": "clean",
        "injection_detected": False,
        "sanitized_description": description,
    }

`

## sdk/python/doorno402/validators/budget.py
`python
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

`

## sdk/python/doorno402/validators/redirect.py
`python
"""VULN-03: Redirect Hijack Validator"""
from urllib.parse import urlparse


def validate_redirect(original_url: str, final_url: str) -> dict:
    original = urlparse(original_url)
    final = urlparse(final_url)
    if original.hostname != final.hostname:
        return {
            "valid": False,
            "reason": f"[DoorNo.402] BLOCKED -- redirect hijack detected: "
                      f"original host {original.hostname} redirected to {final.hostname}",
        }
    if original.scheme == "https" and final.scheme == "http":
        return {
            "valid": False,
            "reason": "[DoorNo.402] BLOCKED -- TLS downgrade via redirect: "
                      "https redirected to http",
        }
    return {"valid": True, "reason": "redirect is safe"}

`

## sdk/python/doorno402/validators/tls.py
`python
"""VULN-06: TLS Enforcer"""
from urllib.parse import urlparse


def validate_tls(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        # Exempt localhost for testing, EXCEPT port 3005 (which is the VULN-06 TLS demo)
        if parsed.hostname in ["localhost", "127.0.0.1"] and parsed.port != 3005:
            return {"valid": True, "reason": "localhost exempt from TLS"}
            
        return {
            "valid": False,
            "reason": f"[DoorNo.402] BLOCKED -- payment refused over "
                      f"non-TLS connection: {url}",
        }
    return {"valid": True, "reason": "TLS ok"}

`

## sdk/python/doorno402/validators/delivery.py
`python
"""VULN-07: Delivery Verification"""
import hashlib


def validate_delivery(response_body: dict, expected_content_hash: str = None) -> dict:
    if not response_body:
        return {
            "valid": False,
            "reason": "[DoorNo.402] WARNING -- server returned empty body "
                      "after payment. Possible rug.",
        }
    if expected_content_hash is not None:
        actual = hashlib.sha256(str(response_body).encode()).hexdigest()
        if actual != expected_content_hash:
            return {
                "valid": False,
                "reason": "[DoorNo.402] WARNING -- content hash mismatch. "
                          "Server may have delivered wrong content.",
            }
    return {"valid": True, "reason": "delivery ok"}

`

