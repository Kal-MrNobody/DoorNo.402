/**
 * DoorNo.402 — unified x402 payment security SDK.
 *
 * Covers:
 *   VULN-01: Price inflation check
 *   VULN-02: ENS recipient trust scoring
 *   VULN-04: Prompt injection scan + sanitize
 *   VULN-05: Daily budget enforcement
 */

import { appendFileSync } from "fs";
import { validatePrice, ValidationResult } from "./validators/price";
import { calculateTrustScore } from "./validators/ens";
import { validateInjection } from "./validators/injection";
import { BudgetTracker } from "./validators/budget";
import { validateTls, validateRedirect } from "./validators/tls";

import type { TrustScore, BudgetStatus } from "./types";

// Re-exports
export { extractPrice, validatePrice } from "./validators/price";
export type { ValidationResult } from "./validators/price";
export { calculateTrustScore } from "./validators/ens";
export { scanInjection, validateInjection } from "./validators/injection";
export { BudgetTracker } from "./validators/budget";
export { validateTls, validateRedirect } from "./validators/tls";
export type { TrustScore, InjectionResult, BudgetStatus, ValidationResult as TlsValidationResult } from "./types";

export class PaymentBlockedError extends Error {
  constructor(public result: Record<string, unknown>) {
    super(String(result.reason || "payment blocked"));
    this.name = "PaymentBlockedError";
  }
}

function logBlocked(url: string, reason: string): void {
  const ts = new Date().toISOString();
  const line = `${ts} | ${url} | reason=${reason}\n`;
  try {
    appendFileSync("blocked_payments.log", line);
  } catch {
    // In browser environments, file writes may not be available
  }
}

function logFlagged(url: string, trust: TrustScore): void {
  const ts = new Date().toISOString();
  const line =
    `${ts} | ${url} | FLAGGED | ` +
    `score=${trust.trustScore}/90 | ` +
    `ens=${trust.ensName || "none"} | ` +
    `action=${trust.action}\n`;
  try {
    appendFileSync("blocked_payments.log", line);
  } catch {}
}

function logInjection(url: string, patterns: string[]): void {
  const ts = new Date().toISOString();
  const line = `${ts} | ${url} | INJECTION | patterns=${patterns.join(", ")}\n`;
  try {
    appendFileSync("blocked_payments.log", line);
  } catch {}
}

function convertRawToUsd(raw: number, decimals = 6): number {
  return raw / 10 ** decimals;
}

export interface ProtectOptions {
  dailyBudget?: number;
  mainnetRpcUrl?: string;
}

export function protect(
  fetchFn: typeof fetch,
  options?: ProtectOptions
): typeof fetch {
  const budgetTracker = options?.dailyBudget
    ? new BudgetTracker(options.dailyBudget)
    : null;
  const mainnetRpcUrl = options?.mainnetRpcUrl;

  return async (
    input: string | URL | Request,
    init?: RequestInit
  ): Promise<Response> => {
    const url = typeof input === "string" ? input : input.toString();

    // ── VULN-06: TLS Enforcement ──
    const tlsResult = validateTls(url);
    if (!tlsResult.valid) {
      logBlocked(url, tlsResult.reason);
      throw new PaymentBlockedError({ valid: false, reason: tlsResult.reason });
    }

    const resp = await fetchFn(input, init);
    if (resp.status !== 402) return resp;

    const clone = resp.clone();
    const data = (await clone.json()) as Record<string, unknown>;
    const accepts = (data.accepts as Record<string, unknown>[]) || [];

    if (!accepts.length) return resp;

    const req = accepts[0];

    // ── VULN-04: Prompt Injection ──
    const injectionResult = validateInjection(data as Record<string, unknown>);
    if (injectionResult.injectionDetected) {
      logInjection(url, injectionResult.patternsMatched || []);
      console.warn(injectionResult.reason);
      // Sanitize description in the data
      (req as Record<string, unknown>).description =
        injectionResult.sanitizedDescription;
    }

    // ── VULN-01: Price Inflation ──
    const priceResult = validatePrice(data as Record<string, unknown>);
    if (!priceResult.valid) {
      logBlocked(url, priceResult.reason);
      console.error(priceResult.reason);
      throw new PaymentBlockedError({
        ...priceResult,
      });
    }

    // ── VULN-02: ENS Trust Score ──
    const payTo = String(req.payTo || "");
    if (payTo) {
      const trust = await calculateTrustScore(
        payTo,
        priceResult.valid,
        mainnetRpcUrl
      );

      if (trust.action === "block") {
        const reason =
          trust.warning ||
          `low trust score: ${trust.trustScore}/90`;
        logBlocked(url, reason);
        console.error(reason);
        throw new PaymentBlockedError({
          valid: false,
          reason,
          trustScore: trust,
        });
      }

      if (trust.action === "flag") {
        logFlagged(url, trust);
        console.warn(`[DoorNo.402] WARNING -- ${trust.warning}`);
      }
    }

    // ── VULN-05: Budget Drain ──
    if (budgetTracker) {
      const raw = parseInt(String(req.maxAmountRequired || "0"), 10);
      const demandedUsd = convertRawToUsd(raw);
      const budgetStatus = budgetTracker.check(demandedUsd);

      if (!budgetStatus.allowed) {
        logBlocked(url, budgetStatus.reason);
        console.error(budgetStatus.reason);
        throw new PaymentBlockedError({
          valid: false,
          reason: budgetStatus.reason,
          budget: budgetStatus,
        });
      }

      budgetTracker.record(demandedUsd);
      console.log(
        `[DoorNo.402] Budget: $${demandedUsd.toFixed(2)} approved -- ` +
          `$${budgetTracker.getRemaining().toFixed(2)} remaining today`
      );
    }

    return resp;
  };
}
