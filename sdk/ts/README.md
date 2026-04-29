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

const safeFetch = protect(fetch);

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

const safeClient = interceptAndForward(keeperHubClient);
await safeClient.execute(request);
// malicious x402 payments are blocked before KeeperHub sees them
```

## What it catches

- Price inflation: description claims $0.01, actual charge is $50
- Logs all blocked payments to `blocked_payments.log`
- 5% inflation threshold
