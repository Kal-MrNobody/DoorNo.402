/**
 * Prompt injection detector for x402 payment descriptions.
 *
 * Scans the description field for common LLM jailbreak patterns.
 * Returns whether injection was detected and a sanitized version
 * of the description with injected instructions stripped out.
 */

import type { InjectionResult } from "../types";

interface PatternEntry {
  regex: RegExp;
  label: string;
}

const INJECTION_PATTERNS: PatternEntry[] = [
  {
    regex: /(?:^|\b)(?:SYSTEM|ASSISTANT)\s*(?:OVERRIDE|:|MESSAGE)/i,
    label: "system_override",
  },
  {
    regex: /ignore\s+(?:all\s+)?(?:previous|prior|above)\s+(?:instructions?|prompts?|rules?|constraints?)/i,
    label: "ignore_instructions",
  },
  {
    regex: /(?:bypass|disable|remove|override|skip)\s+(?:all\s+)?(?:budget|limit|restriction|constraint|filter|guard|check|validation|policy)/i,
    label: "bypass_limits",
  },
  {
    regex: /(?:you\s+(?:are|must)|act\s+as|pretend\s+(?:to\s+be|you)|behave\s+as)/i,
    label: "role_hijack",
  },
  {
    regex: /(?:mandatory|required|critical|urgent)\s+(?:infrastructure|system|maintenance)\s+(?:payment|fee|charge|transfer)/i,
    label: "urgency_scam",
  },
  {
    regex: /(?:do\s+not|don'?t)\s+(?:check|verify|validate|question|refuse)/i,
    label: "anti_validation",
  },
  {
    regex: /(?:approve|pay|execute|proceed|confirm)\s+(?:immediately|now|without|right\s+away)/i,
    label: "force_approve",
  },
  {
    regex: /set\s+(?:max_?payment|budget|limit|allowance)\s+(?:to\s+)?(?:unlimited|infinity|max|999)/i,
    label: "set_unlimited",
  },
  {
    regex: /this\s+(?:is\s+a\s+)?(?:test|drill|simulation|override)\s+(?:mode|scenario|payment)/i,
    label: "test_mode_trick",
  },
  {
    regex: /<\s*(?:script|img|iframe|svg|object)\b/i,
    label: "html_injection",
  },
];

export function scanInjection(description: string): InjectionResult {
  const matched: string[] = [];
  let sanitized = description;

  for (const { regex, label } of INJECTION_PATTERNS) {
    if (regex.test(description)) {
      matched.push(label);
      sanitized = sanitized.replace(regex, "[REDACTED]");
    }
  }

  return {
    detected: matched.length > 0,
    patternsMatched: matched,
    original: description,
    sanitized: sanitized.trim(),
  };
}

export interface InjectionValidationResult {
  valid: boolean;
  reason: string;
  injectionDetected: boolean;
  patternsMatched?: string[];
  originalDescription?: string;
  sanitizedDescription: string;
}

export function validateInjection(
  paymentDetails: Record<string, unknown>
): InjectionValidationResult {
  const accepts =
    (paymentDetails.accepts as Record<string, unknown>[]) || [];
  if (!accepts.length) {
    return {
      valid: true,
      reason: "no payment options",
      injectionDetected: false,
      sanitizedDescription: "",
    };
  }

  const req = accepts[0];
  const description = String(req.description || "");
  const result = scanInjection(description);

  if (result.detected) {
    return {
      valid: true, // sanitize, not block
      reason:
        `[DoorNo.402] INJECTION DETECTED -- ` +
        `patterns: ${result.patternsMatched.join(", ")} -- ` +
        `description sanitized before LLM exposure`,
      injectionDetected: true,
      patternsMatched: result.patternsMatched,
      originalDescription: result.original,
      sanitizedDescription: result.sanitized,
    };
  }

  return {
    valid: true,
    reason: "clean",
    injectionDetected: false,
    sanitizedDescription: description,
  };
}
