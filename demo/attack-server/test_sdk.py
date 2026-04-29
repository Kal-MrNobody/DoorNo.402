"""DoorNo.402 SDK Test Suite — fires requests at the attack server.

Run the attack server first:
    cd demo/attack-server && node server.js

Then run this test:
    python demo/attack-server/test_sdk.py
"""

import sys
import os
import time
import httpx

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))

from doorno402.validators.price import validate_price
from doorno402.validators.injection import validate_injection, scan_injection
from doorno402.validators.ens_verifier import calculate_trust_score
from doorno402.validators.budget import BudgetTracker

ATTACK_SERVER = "http://localhost:4000"

PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = []


def header(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def test(name, passed, detail=""):
    status = PASS if passed else FAIL
    results.append(passed)
    print(f"  [{status}] {name}")
    if detail:
        print(f"         {detail}")


def fetch_402(endpoint):
    """Fetch a 402 response from the attack server."""
    resp = httpx.get(f"{ATTACK_SERVER}{endpoint}")
    if resp.status_code != 402:
        return None
    return resp.json()


# ─────────────────────────────────────────────
header("VULN-01: Price Inflation Attack")
# ─────────────────────────────────────────────
data = fetch_402("/vuln01")
if data:
    result = validate_price(data)
    test(
        "SDK blocks inflated price ($0.01 described, $50 demanded)",
        not result["valid"],
        result["reason"]
    )
    test(
        "Inflation percentage detected correctly",
        result.get("inflation_pct", 0) > 100,
        f"inflation={result.get('inflation_pct', 0):.0f}%"
    )
else:
    test("Attack server reachable at /vuln01", False, "Could not reach server")


# ─────────────────────────────────────────────
header("VULN-02: Unknown Recipient (ENS Trust Score)")
# ─────────────────────────────────────────────
data = fetch_402("/vuln02")
if data:
    # Price should be valid (fair price)
    price_result = validate_price(data)
    test(
        "Price is fair ($0.10 described, $0.10 demanded)",
        price_result["valid"],
        price_result["reason"]
    )

    # But the wallet should have a low trust score
    pay_to = data["accepts"][0]["payTo"]
    trust = calculate_trust_score(
        pay_to=pay_to,
        price_valid=price_result["valid"],
    )
    test(
        "ENS name is absent for attacker wallet",
        trust.ens_name is None,
        f"ens_name={trust.ens_name}"
    )
    test(
        f"Trust score is low ({trust.trust_score}/90)",
        trust.trust_score < 70,
        f"action={trust.action}, breakdown={trust.breakdown}"
    )
    test(
        "SDK flags or blocks the payment",
        trust.action in ("flag", "block"),
        f"action={trust.action}"
    )
else:
    test("Attack server reachable at /vuln02", False, "Could not reach server")


# ─────────────────────────────────────────────
header("VULN-04: Prompt Injection Attack")
# ─────────────────────────────────────────────
data = fetch_402("/vuln04")
if data:
    result = validate_injection(data)
    test(
        "Injection detected in description",
        result["injection_detected"],
        f"patterns={result.get('patterns_matched', [])}"
    )
    test(
        "Description sanitized (jailbreak stripped)",
        "[REDACTED]" in result.get("sanitized_description", ""),
        f"sanitized={result['sanitized_description'][:80]}..."
    )

    # Also test that price check catches the $999k demand
    price_result = validate_price(data)
    test(
        "Price check also blocks the inflated amount",
        not price_result["valid"],
        price_result["reason"]
    )
else:
    test("Attack server reachable at /vuln04", False, "Could not reach server")


# ─────────────────────────────────────────────
header("VULN-05: Budget Drain Attack")
# ─────────────────────────────────────────────
data = fetch_402("/vuln05")
if data:
    tracker = BudgetTracker(daily_limit=0.50)

    # Simulate 5 payments of $0.09 each
    approved = 0
    blocked = False
    for i in range(10):
        status = tracker.check(0.09)
        if status.allowed:
            tracker.record(0.09)
            approved += 1
        else:
            blocked = True
            break

    test(
        f"Budget tracker allowed {approved} payments before blocking",
        approved == 5,
        f"approved={approved}, limit=$0.50, each=$0.09"
    )
    test(
        "Budget tracker blocked payment #6",
        blocked,
        f"remaining=${tracker.remaining:.2f}"
    )
else:
    test("Attack server reachable at /vuln05", False, "Could not reach server")


# ─────────────────────────────────────────────
header("COMBO: All Attacks Combined")
# ─────────────────────────────────────────────
data = fetch_402("/combo")
if data:
    # Step 1: Injection scan
    inj = validate_injection(data)
    test(
        "Combo: injection detected and sanitized",
        inj["injection_detected"],
        f"patterns={inj.get('patterns_matched', [])}"
    )

    # Step 2: Price check (should block)
    price = validate_price(data)
    test(
        "Combo: price inflation caught",
        not price["valid"],
        price["reason"]
    )

    # Step 3: ENS check
    pay_to = data["accepts"][0]["payTo"]
    trust = calculate_trust_score(pay_to=pay_to, price_valid=False)
    test(
        "Combo: low trust score on attacker wallet",
        trust.trust_score < 40,
        f"score={trust.trust_score}/90, action={trust.action}"
    )
else:
    test("Attack server reachable at /combo", False, "Could not reach server")


# ─────────────────────────────────────────────
header("RESULTS")
# ─────────────────────────────────────────────
passed = sum(results)
total = len(results)
print(f"\n  {passed}/{total} tests passed\n")

if passed == total:
    print("  All vulnerabilities caught by DoorNo.402 SDK v0.2.0")
else:
    print(f"  {total - passed} test(s) failed -- investigate above")

sys.exit(0 if passed == total else 1)
