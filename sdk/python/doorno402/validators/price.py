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
