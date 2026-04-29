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
