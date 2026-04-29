# doorno402 — TypeScript SDK

Security middleware for x402 payment protocol. Validates 402 responses before agents pay them.

## Install

```bash
npm install
npm run build
```

## Usage — fetch wrapper

```typescript
import { protect, PaymentBlockedError } from "doorno402";

const safeFetch = protect(fetch, {
  dailyBudget: 5.00,
  mainnetRpcUrl: "https://cloudflare-eth.com"
});

try {
  const resp = await safeFetch("https://api.example.com/resource");
} catch (e) {
  if (e instanceof PaymentBlockedError) {
    console.log("Blocked:", e.result.reason);
  }
}
```

## Usage — KeeperHub MCP

```typescript
import { interceptAndForward } from "doorno402/mcp";

const safeClient = interceptAndForward(keeperHubClient, {
  dailyBudget: 5.00,
  mainnetRpcUrl: "https://cloudflare-eth.com"
});
await safeClient.execute(request);
// malicious x402 payments are blocked before KeeperHub sees them
```

## Security Features (v0.2.0)

- **VULN-01: Price Inflation Check**: Blocks if demanded price exceeds description price by >5%.
- **VULN-02: ENS Trust Scoring**: Scores recipient wallets based on ENS presence, age, and tx history. Flags or blocks low-trust wallets.
- **VULN-04: Prompt Injection Detection**: Scans description field for LLM jailbreaks and sanitizes before the agent sees it.
- **VULN-05: Budget Drain Enforcement**: Blocks payments that exceed the configured `dailyBudget`.
