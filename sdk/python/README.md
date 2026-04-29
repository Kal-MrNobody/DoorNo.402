# doorno402 — Python SDK

Security middleware for x402 payment protocol. Validates 402 responses before agents pay them.

## Install

```bash
pip install -e .
```

## Usage

```python
from doorno402 import protect

# Basic protection
safe_client = protect(x402HttpxClient(account=account))

# Protection with daily budget and ENS verification
safe_client = protect(
    client, 
    daily_budget=5.00,
    mainnet_rpc_url="https://cloudflare-eth.com"
)
```

## Security Features (v0.2.0)

- **VULN-01: Price Inflation Check**
  - Blocks if demanded price exceeds description price by >5%.
- **VULN-02: ENS Trust Scoring**
  - Scores recipient wallets based on ENS presence, age, and tx history. Flags or blocks low-trust wallets.
- **VULN-04: Prompt Injection Detection**
  - Scans description field for LLM jailbreaks and sanitizes before the agent sees it.
- **VULN-05: Budget Drain Enforcement**
  - Blocks payments that exceed the configured `daily_budget`.
