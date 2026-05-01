# KeeperHub Integration

DoorNo.402 sits in front of KeeperHub as a validation layer.
Agents use KeeperHub for reliable onchain execution.
DoorNo.402 ensures every payment is legitimate before KeeperHub sees it.

## Flow

```
Without DoorNo.402:
  Agent → KeeperHub executes blindly → wallet drained

With DoorNo.402:
  Agent → DoorNo.402 validates (7 checks) → KeeperHub executes safely
  Agent → DoorNo.402 blocks fraud → KeeperHub never called
```

## API Endpoint

KeeperHub Direct Execution API:

```
POST https://api.keeperhub.com/api/execute/transfer
Authorization: Bearer kh_your_api_key

{
  "network": "base-sepolia",
  "recipientAddress": "0x...",
  "amount": "5.000000",
  "tokenAddress": "0x036CbD53842c5426634e7929541eC2318f3dCF7e",
  "tokenConfig": "{\"decimals\":6,\"symbol\":\"USDC\"}"
}
```

## Three Demo Modes

### MODE 1 — Unprotected (KeeperHub executes blindly)

No DoorNo.402. Agent forwards the malicious $5.00 payment
directly to KeeperHub. Wallet is drained.

### MODE 2 — Protected + Blocked

DoorNo.402 intercepts the 402 response, detects price inflation
(description says $0.01, protocol demands $5.00), and raises
`PaymentBlockedError`. KeeperHub is never called.

### MODE 3 — Protected + Approved + Executed

Agent hits an honest endpoint where description and amount match.
DoorNo.402 validates and approves. Payment is forwarded to KeeperHub
which executes the USDC transfer on Base Sepolia.

## How to Run

Set `KEEPERHUB_API_KEY` and `KEEPERHUB_WALLET` in `.env`.

```bash
# Start the blog server
cd demo/blog/backend && node server.js

# MODE 1: unprotected — KeeperHub drains wallet
# Edit MODE=1 in keeperhub_demo.py
python demo/agent/keeperhub_demo.py

# MODE 2: protected — DoorNo.402 blocks
# Edit MODE=2 in keeperhub_demo.py
python demo/agent/keeperhub_demo.py

# MODE 3: approved — DoorNo.402 + KeeperHub together
# Edit MODE=3 in keeperhub_demo.py
python demo/agent/keeperhub_demo.py
```

## MCP Integration

The MCP demo uses sdk/ts/src/keeperhub_mcp.ts which instantiates
a KeeperHub MCP client directly from the SDK — no Claude Code needed.

Run Mode 2 (blocked):
  MODE=2 npm run demo:mcp

Run Mode 3 (approved + MCP executes):
  MODE=3 npm run demo:mcp

The SDK calls these KeeperHub MCP tools in sequence:
  get_wallet_integration — fetch walletId
  ai_generate_workflow   — build transfer workflow from prompt
  execute_workflow       — trigger execution
  get_execution_status   — poll for txHash

## Why This Matters

KeeperHub guarantees reliable onchain execution with retries,
gas management, and SLA-backed settlements.

DoorNo.402 guarantees the payment request is legitimate
before it ever reaches KeeperHub.

Together they form a complete secure payment pipeline for AI agents.
