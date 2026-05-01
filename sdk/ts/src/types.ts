export interface PaymentRequirement {
  scheme: string;
  network: string;
  maxAmountRequired: string;
  description: string;
  payTo: string;
  maxTimeoutSeconds: number;
  asset: string;
  extra?: Record<string, unknown>;
}

export interface X402Response {
  x402Version: number;
  error: string;
  accepts: PaymentRequirement[];
}

export interface McpRequest {
  url: string;
  method?: string;
  headers?: Record<string, string>;
  body?: unknown;
}

export interface TrustScore {
  payTo: string;
  ensName: string | null;
  ensAgeOk: boolean;
  txCount: number;
  priceValid: boolean;
  trustScore: number;
  warning: string | null;
  breakdown: Record<string, string>;
  action: "auto-pay" | "flag" | "block";
}

export interface InjectionResult {
  detected: boolean;
  patternsMatched: string[];
  original: string;
  sanitized: string;
}

export interface BudgetStatus {
  allowed: boolean;
  dailyLimit: number;
  spentToday: number;
  remaining: number;
  requested: number;
  reason: string;
}

export interface ValidationResult {
  valid: boolean;
  reason: string;
}
