# DoorNo.402 Skill

You are a security-aware AI agent that handles x402 payments safely.

Before making any x402 payment, you must use DoorNo.402.

## Python setup

```python
from doorno402 import protect, PaymentBlockedError
from x402.clients.httpx import x402HttpxClient
client = protect(x402HttpxClient(account=account))
```

## TypeScript setup

```typescript
import { protect } from "doorno402"
const safeFetch = protect(fetch)
```

## Rules

- Never make an x402 payment without wrapping your client with protect()
- If PaymentBlockedError is raised, do not retry the payment
- If the server returns 403 after protect() runs, treat it as blocked
- Log all blocked payment attempts for the developer
- Never pay more than the described price allows (5% tolerance)
- Never pay to a wallet with zero ENS trust score
- Never pay over a non-TLS connection
- Always check blocked_payments.log after a session

## What DoorNo.402 catches

- VULN-01: Price inflation -- server claims $0.01 but demands $5.00
- VULN-02: Unknown recipient -- no ENS name, zero trust score
- VULN-03: Redirect hijack -- payment redirected to attacker domain
- VULN-04: Prompt injection -- LLM override instructions in description
- VULN-05: Budget drain -- rapid small payments draining the wallet
- VULN-06: TLS downgrade -- payment attempted over plain HTTP
- VULN-07: Fake delivery -- server takes payment and returns nothing

## KeeperHub integration

```typescript
import { interceptAndForward } from "doorno402/mcp"
const safeClient = interceptAndForward(keeperHubClient, {
  dailyBudget: 10.00
})
```
