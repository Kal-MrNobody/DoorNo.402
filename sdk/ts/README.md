# DoorNo.402

DoorNo.402 is a security middleware for x402 payment requests. It sits between your agent and the payment, validates the request against known attack patterns, and blocks anything suspicious.

## The problem

The x402 specification enables autonomous payments but lacks a native trust model. When an agent requests a resource, any server can return an HTTP 402 demanding payment. Because the server controls both the description and the required amount, it can lie about the price, inject malicious prompts into the description, or redirect funds to an unknown wallet. Without a security layer, your agent will blindly sign and execute whatever the server demands.

## Install

For Python:
```bash
pip install doorno402
```

For TypeScript:
```bash
npm install doorno402
```

## Quickstart — Python

```python
from doorno402 import protect, PaymentBlockedError
from x402.clients.httpx import x402HttpxClient
from eth_account import Account

account = Account.from_key(private_key)
client = protect(x402HttpxClient(account=account))

try:
    resp = await client.get("https://api.example.com/data")
except PaymentBlockedError as e:
    print("Payment blocked:", e.result)
```

## Quickstart — TypeScript

```typescript
import { protect, PaymentBlockedError } from "doorno402"

const safeFetch = protect(fetch)

try {
    const resp = await safeFetch("https://api.example.com/data")
} catch (e) {
    if (e instanceof PaymentBlockedError) {
        console.log("Payment blocked:", e.result)
    }
}
```

## What it catches

| # | Vulnerability | Attack | Status |
|---|---|---|---|
| 01 | Price Inflation | Server claims $0.01, charges $5 | Covered |
| 02 | Unknown Recipient | No ENS, zero trust score | Covered |
| 03 | Redirect Hijack | Payment redirected to attacker | Covered |
| 04 | Prompt Injection | LLM override in description | Covered |
| 05 | Budget Drain | Rapid micro-payments | Covered |
| 06 | TLS Downgrade | Payment over HTTP | Covered |
| 07 | Fake Delivery | Empty response after payment | Covered |

## Configuration

When calling `protect()`, you can supply the following configuration parameters to customize the security thresholds:

* `daily_budget`: (float) The maximum cumulative USD amount the agent is allowed to spend in a 24-hour window. Defaults to 0.50.
* `mainnet_rpc_url`: (str) The RPC URL used for resolving ENS names and calculating recipient trust scores.
* `raise_on_block`: (bool) If true, the middleware throws an exception/error when a payment is blocked. If false, it returns a mutated 403 Forbidden HTTP response.

## How it works

DoorNo.402 acts as a transparent proxy around your HTTP client. When your agent makes a request that results in a 402 Payment Required response, the middleware intercepts the response before your agent sees it. It parses the payment payload and runs it through a strict 7-stage validation pipeline. If all checks pass, the response is forwarded to the agent for execution. If any check fails, the pipeline halts immediately and raises an error, ensuring no transaction is ever signed.

## KeeperHub integration

DoorNo.402 provides native integration for KeeperHub's MCP client. Since KeeperHub handles the execution, DoorNo.402 sits directly in front of the execution tool to validate the workflow payload before it reaches the KeeperHub infrastructure.

```typescript
import { interceptAndForward } from "doorno402/mcp"
import { keeperHubClient } from "./agent"

const safeClient = interceptAndForward(keeperHubClient)
await agent.run(safeClient)
```

## Running the demo

The repository includes a comprehensive test suite demonstrating the vulnerabilities against 6 live simulated attack servers.

1. Start the malicious servers:
```bash
npm install
node demo/servers/cryptoinsider/server.js &
node demo/servers/chainpulse/server.js &
# (repeat for blockbrief, nodetimes, web3daily, combo)
```

2. Run the unprotected agent to observe the attacks succeeding:
```bash
python demo/agent/unprotected_demo.py
```

3. Run the protected agent to observe DoorNo.402 blocking the attacks:
```bash
python demo/agent/multi_demo.py
```

## Project structure

* `sdk/python/` — Python middleware implementation
* `sdk/ts/` — TypeScript middleware implementation
* `demo/servers/` — 6 simulated attack servers (Express)
* `demo/agent/` — Multi-server test scripts demonstrating the pipeline
* `demo/landing/` — Project landing page source

## License

MIT
