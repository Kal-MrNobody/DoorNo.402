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
