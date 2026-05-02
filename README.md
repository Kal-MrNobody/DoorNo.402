# DoorNo.402

Security middleware for the x402 payment protocol. Intercepts and validates 402 Payment Required responses before autonomous agents pay them.

## The vulnerability

x402 lets servers charge AI agents for resources over HTTP. The problem: nothing stops a malicious server from claiming a resource costs $0.01 in the description while demanding $50 in the actual payment amount. Coinbase's official `x402HttpxClient` pays whatever the server asks no validation, no warning, no human in the loop.

We confirmed this with real on-chain transactions using Coinbase's own SDK on Base Sepolia testnet. The agent paid $5.00 for a resource advertised at $0.01. Transaction hashes are in the research docs.

DoorNo.402 sits between the agent and the payment. It catches the fraud before any money leaves the wallet.

## What it covers

| # | Vulnerability | Status |
|---|---|---|
| 01 | Price inflation | covered |
| 02 | Unknown recipient (ENS) | covered |
| 03 | Redirect hijack | covered |
| 04 | Prompt injection | covered |
| 05 | Budget drain | covered |
| 06 | TLS downgrade | covered |
| 07 | Fake delivery | covered |

## Quickstart

Clone and run the demo locally in under 10 minutes.

```bash
git clone https://github.com/Kal-MrNobody/DoorNo.402.git
cd DoorNo.402
```

Start the malicious blog server:

```bash
cd demo/blog/backend
npm install
ATTACKER_WALLET=0xYourWallet node server.js
```

Run the agent (unprotected — will pay the fraudulent amount):

```bash
cd demo/agent
pip install -r requirements.txt
# set AGENT_PRIVATE_KEY, AGENT_ADDRESS in .env
python agent.py
```

Now flip the switch — edit `agent.py`, set `PROTECTED = True`, run again. DoorNo.402 blocks the payment.

## Installation

Python (v0.3.0):

```bash
cd sdk/python
pip install -e .
```

TypeScript (v0.3.0):

```bash
cd sdk/ts
npm install
npm run build
```

## Usage — Python

```python
from eth_account import Account
from x402.clients.httpx import x402HttpxClient
from doorno402 import protect, PaymentBlockedError

account = Account.from_key(private_key)

async with x402HttpxClient(account=account) as client:
    client = protect(client)
    try:
        resp = await client.get("https://some-x402-api.com/resource")
    except PaymentBlockedError as e:
        print(e.result)
        # payment was blocked — wallet untouched
```

## Usage — TypeScript

```typescript
import { protect, PaymentBlockedError } from "doorno402";

const safeFetch = protect(fetch);

try {
  const resp = await safeFetch("https://some-x402-api.com/resource");
} catch (e) {
  if (e instanceof PaymentBlockedError) {
    console.log(e.result);
    // payment was blocked
  }
}
```

## KeeperHub integration

DoorNo.402 validates. KeeperHub executes. Together they form a complete secure payment pipeline.

```typescript
import { interceptAndForward } from "doorno402/mcp";
import { KeeperHubClient } from "@keeperhub/mcp";

const rawClient = new KeeperHubClient();
const safeClient = interceptAndForward(rawClient);

// safeClient validates all x402 payments before KeeperHub executes them
// malicious 402 responses are blocked — KeeperHub never sees them
await safeClient.execute(request);
```

See [demo/agent/KEEPERHUB.md](demo/agent/KEEPERHUB.md) for the full integration guide.

## Skills

AI agents can load [skills/doorno402.md](skills/doorno402.md) to automatically know how to use DoorNo.402 for safe x402 payments.

## How the demo works

The demo has two parts:

1. **Cryptology blog** — a realistic-looking crypto news site. Premium articles sit behind an x402 paywall. The server claims the price is $0.01 but the `maxAmountRequired` field demands $5.00. This is the attack.

2. **Agent** — uses Coinbase's `x402HttpxClient` to read the blog. In unprotected mode, the agent pays $5.00 without noticing the mismatch. In protected mode, DoorNo.402 intercepts the 402 response, detects the 49,900% price inflation, and blocks the payment before any transaction is signed.

## Project structure

```
DoorNo.402/
├── sdk/
│   ├── python/              # Python SDK (v0.3.0)
│   │   ├── doorno402/
│   │   │   ├── guard.py     # protect() wrapper + PaymentBlockedError
│   │   │   └── validators/
│   │   │       ├── price.py     # VULN-01: price inflation
│   │   │       ├── ens_verifier.py  # VULN-02: ENS trust scoring
│   │   │       ├── redirect.py  # VULN-03: redirect hijack
│   │   │       ├── injection.py # VULN-04: prompt injection
│   │   │       ├── budget.py    # VULN-05: budget drain
│   │   │       ├── tls.py       # VULN-06: TLS enforcer
│   │   │       └── delivery.py  # VULN-07: delivery verification
│   │   └── setup.py
│   └── ts/                  # TypeScript SDK (v0.3.0)
│       └── src/
│           ├── index.ts     # protect() + PaymentBlockedError
│           ├── mcp.ts       # KeeperHub MCP integration
│           ├── types.ts     # shared interfaces
│           └── validators/
├── demo/
│   ├── blog/                # Malicious blog with x402 paywall
│   ├── attack-server/       # Multi-vuln attack simulation server
│   ├── cli/                 # Interactive terminal demo
│   └── agent/               # Demo agents + KeeperHub integration
├── skills/
│   └── doorno402.md         # Agent skill prompt
├── FEEDBACK.md              # KeeperHub developer feedback
└── README.md
```
