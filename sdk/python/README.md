# doorno402 — Python SDK

Security middleware for x402 payment protocol. Validates 402 responses before agents pay them.

## Install

```bash
pip install -e .
```

## Usage

```python
from doorno402 import protect, PaymentBlockedError
from x402.clients.httpx import x402HttpxClient
from eth_account import Account

account = Account.from_key(os.environ["AGENT_PRIVATE_KEY"])

async with x402HttpxClient(account=account) as client:
    client = protect(client)
    try:
        resp = await client.get("https://api.example.com/resource")
    except PaymentBlockedError as e:
        print(f"Blocked: {e.result['reason']}")
```

## What it catches

- Price inflation: description claims $0.01, actual charge is $50
- Logs all blocked payments to `blocked_payments.log`
- 5% inflation threshold (configurable)
