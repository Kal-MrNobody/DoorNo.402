"""VULN-06: TLS Enforcer"""
from urllib.parse import urlparse


def validate_tls(url: str) -> dict:
    parsed = urlparse(url)
    if parsed.scheme != "https":
        return {
            "valid": False,
            "reason": f"[DoorNo.402] BLOCKED -- payment refused over "
                      f"non-TLS connection: {url}",
        }
    return {"valid": True, "reason": "TLS ok"}
