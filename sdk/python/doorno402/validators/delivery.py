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
