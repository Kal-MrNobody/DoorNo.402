import { appendFileSync } from "fs";
import { validatePrice, ValidationResult } from "./validators/price";
import { PaymentBlockedError } from "./index";

export interface McpClient {
  execute: (request: unknown) => Promise<unknown>;
}

function logBlocked(result: ValidationResult): void {
  const ts = new Date().toISOString();
  const line =
    `${ts} | mcp | ` +
    `described=$${result.described?.toFixed(2) ?? "?"} | ` +
    `demanded=$${result.demanded?.toFixed(2) ?? "?"} | ` +
    `inflation=${Math.round(result.inflationPct ?? 0)}%\n`;
  appendFileSync("blocked_payments.log", line);
}

// eslint-disable-next-line @typescript-eslint/no-explicit-any -- request shape varies by MCP provider
function extractPayload(request: any): Record<string, unknown> | null {
  if (request?.x402Version && request?.accepts) return request;
  if (request?.payment?.x402Version) return request.payment;
  if (request?.response?.x402Version) return request.response;
  return null;
}

export function interceptAndForward(mcpClient: McpClient): McpClient {
  return {
    async execute(request: unknown): Promise<unknown> {
      const payload = extractPayload(request);

      if (payload) {
        const result = validatePrice(payload);
        if (!result.valid) {
          logBlocked(result);
          console.error(result.reason);
          throw new PaymentBlockedError(result);
        }
      }

      return mcpClient.execute(request);
    },
  };
}
