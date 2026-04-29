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
