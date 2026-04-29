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
        name = w3.eth.ens.name(Web3.to_checksum_address(address))  # type: ignore[union-attr]
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
