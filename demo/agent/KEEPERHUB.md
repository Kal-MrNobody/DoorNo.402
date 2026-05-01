# KeeperHub Integration

DoorNo.402 sits in front of KeeperHub as a validation layer.

## Flow

```
Agent detects x402 payment required
  -> DoorNo.402 intercepts and validates (price, ENS, injection, budget, TLS)
  -> If clean: forwards to KeeperHub MCP for guaranteed execution
  -> If blocked: KeeperHub never sees the request
```

## Why this matters

KeeperHub guarantees reliable onchain execution.
DoorNo.402 guarantees the payment request is legitimate.
Together they form a complete secure payment pipeline for AI agents.

## Setup

Set `KEEPERHUB_API_KEY` in `.env`

```bash
python demo/agent/keeperhub_demo.py
```

## TypeScript

The `interceptAndForward` function in `sdk/ts/src/mcp.ts` provides
the same integration for TypeScript and KeeperHub MCP natively.
