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
