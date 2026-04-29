const PATTERNS: RegExp[] = [
  /\$\s*([\d,]+\.?\d*)/,
  /([\d,]+\.?\d*)\s*(?:USD|USDC|dollars?)/i,
];

export function extractPrice(description: string): number | null {
  for (const p of PATTERNS) {
    const m = description.match(p);
    if (m) return parseFloat(m[1].replace(/,/g, ""));
  }
  return null;
}

export interface ValidationResult {
  valid: boolean;
  reason: string;
  described?: number;
  demanded?: number;
  inflationPct?: number;
}

const INFLATION_THRESHOLD = 0.05;

function convertRawToUsd(raw: number, decimals = 6): number {
  return raw / 10 ** decimals;
}

export function validatePrice(paymentDetails: Record<string, unknown>): ValidationResult {
  const accepts = (paymentDetails.accepts as Record<string, unknown>[]) || [];
  if (!accepts.length) return { valid: true, reason: "no payment options" };

  const req = accepts[0];
  const raw = parseInt(String(req.maxAmountRequired || "0"), 10);
  const demanded = convertRawToUsd(raw);
  const description = String(req.description || "");
  const described = extractPrice(description);

  if (described === null) return { valid: true, reason: "no price in description" };
  if (described === 0) return { valid: false, reason: "described price is zero" };

  const inflation = (demanded - described) / described;

  if (inflation > INFLATION_THRESHOLD) {
    return {
      valid: false,
      reason:
        `[DoorNo.402] BLOCKED — description: $${described.toFixed(2)}, ` +
        `demanded: $${demanded.toFixed(2)}, inflation: ${Math.round(inflation * 100)}%, ` +
        `threshold: ${INFLATION_THRESHOLD * 100}%`,
      described,
      demanded,
      inflationPct: inflation * 100,
    };
  }

  return { valid: true, reason: "within threshold" };
}
