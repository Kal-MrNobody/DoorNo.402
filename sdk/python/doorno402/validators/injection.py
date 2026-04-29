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
