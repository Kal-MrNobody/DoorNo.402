/**
 * DoorNo.402 MCP (Model Context Protocol) interceptor for KeeperHub.
 *
 * All 4 security checks run before KeeperHub ever sees the request:
 *   VULN-01: Price inflation
 *   VULN-02: ENS trust scoring
 *   VULN-04: Prompt injection scan
 *   VULN-05: Budget enforcement
 */

import { appendFileSync } from "fs";
import { validatePrice, ValidationResult } from "./validators/price";
import { calculateTrustScore } from "./validators/ens";
import { validateInjection } from "./validators/injection";
import { BudgetTracker } from "./validators/budget";
import { PaymentBlockedError } from "./index";

export interface McpClient {
  execute: (request: unknown) => Promise<unknown>;
}

export interface InterceptOptions {
  dailyBudget?: number;
  mainnetRpcUrl?: string;
}

function logBlocked(reason: string): void {
  const ts = new Date().toISOString();
  const line = `${ts} | mcp | reason=${reason}\n`;
  try {
    appendFileSync("blocked_payments.log", line);
  } catch {}
}

function logInjection(patterns: string[]): void {
  const ts = new Date().toISOString();
  const line = `${ts} | mcp | INJECTION | patterns=${patterns.join(", ")}\n`;
  try {
    appendFileSync("blocked_payments.log", line);
  } catch {}
}

function convertRawToUsd(raw: number, decimals = 6): number {
  return raw / 10 ** decimals;
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- request shape varies
function extractPayload(request: any): Record<string, unknown> | null {
  if (request?.x402Version && request?.accepts) return request;
  if (request?.payment?.x402Version) return request.payment;
  if (request?.response?.x402Version) return request.response;
  return null;
}

export function interceptAndForward(
  mcpClient: McpClient,
  options?: InterceptOptions
): McpClient {
  const budgetTracker = options?.dailyBudget
    ? new BudgetTracker(options.dailyBudget)
    : null;

  return {
    async execute(request: unknown): Promise<unknown> {
      const payload = extractPayload(request);

      if (payload) {
        const accepts =
          (payload.accepts as Record<string, unknown>[]) || [];
        const req = accepts.length ? accepts[0] : null;

        if (req) {
          // ── VULN-04: Prompt Injection ──
          const injectionResult = validateInjection(payload);
          if (injectionResult.injectionDetected) {
            logInjection(injectionResult.patternsMatched || []);
            console.warn(injectionResult.reason);
            (req as Record<string, unknown>).description =
              injectionResult.sanitizedDescription;
          }
        }

        // ── VULN-01: Price Inflation ──
        const priceResult = validatePrice(payload);
        if (!priceResult.valid) {
          logBlocked(priceResult.reason);
          console.error(priceResult.reason);
          throw new PaymentBlockedError({
            valid: false,
            reason: priceResult.reason,
          });
        }

        if (req) {

          // ── VULN-02: ENS Trust Score ──
          const payTo = String(req.payTo || "");
          if (payTo) {
            const trust = await calculateTrustScore(
              payTo,
              priceResult.valid,
              options?.mainnetRpcUrl
            );

            if (trust.action === "block") {
              const reason =
                trust.warning ||
                `low trust score: ${trust.trustScore}/90`;
              logBlocked(reason);
              console.error(reason);
              throw new PaymentBlockedError({
                valid: false,
                reason,
                trustScore: trust,
              });
            }

            if (trust.action === "flag") {
              console.warn(
                `[DoorNo.402] WARNING -- ${trust.warning}`
              );
            }
          }

          // ── VULN-05: Budget Drain ──
          if (budgetTracker) {
            const raw = parseInt(
              String(req.maxAmountRequired || "0"),
              10
            );
            const demandedUsd = convertRawToUsd(raw);
            const budgetStatus = budgetTracker.check(demandedUsd);

            if (!budgetStatus.allowed) {
              logBlocked(budgetStatus.reason);
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
        }
      }

      return mcpClient.execute(request);
    },
  };
}
