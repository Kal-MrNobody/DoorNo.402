import { writeFileSync, appendFileSync } from "fs";
import { validatePrice, ValidationResult } from "./validators/price";

export { extractPrice, validatePrice, ValidationResult } from "./validators/price";

export class PaymentBlockedError extends Error {
  constructor(public result: ValidationResult) {
    super(result.reason);
    this.name = "PaymentBlockedError";
  }
}

function logBlocked(url: string, result: ValidationResult): void {
  const ts = new Date().toISOString();
  const line =
    `${ts} | ${url} | ` +
    `described=$${result.described?.toFixed(2) ?? "?"} | ` +
    `demanded=$${result.demanded?.toFixed(2) ?? "?"} | ` +
    `inflation=${Math.round(result.inflationPct ?? 0)}%\n`;
  appendFileSync("blocked_payments.log", line);
}

export function protect(fetchFn: typeof fetch): typeof fetch {
  return async (input: RequestInfo | URL, init?: RequestInit): Promise<Response> => {
    const resp = await fetchFn(input, init);

    if (resp.status !== 402) return resp;

    const clone = resp.clone();
    const data = await clone.json();
    const result = validatePrice(data);

    if (!result.valid) {
      const url = typeof input === "string" ? input : input.toString();
      logBlocked(url, result);
      console.error(result.reason);
      throw new PaymentBlockedError(result);
    }

    return resp;
  };
}
