"""
DoorNo.402 Standalone Agent Demo

This script demonstrates a raw AI agent encountering an x402 paywall
and executing the payment. 

To make this agent SECURE, simply uncomment the DoorNo.402 protection block.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

# Add SDK and CLI directories to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "cli"))

from keeperhub_executor import extract_payment_details, execute_payment

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

# =============================================================================
# DOORNO.402 SECURITY SDK
# Uncomment these imports to enable the protection layer
# =============================================================================
# from doorno402.validators.price import validate_price
# from doorno402.validators.injection import validate_injection
# from doorno402.validators.tls import validate_tls

async def run_agent_task(target_url: str):
    print("\n[ Agent Started ]")
    print(f"Agent: Requesting resource from {target_url}")
    
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            resp = await client.get(target_url)
    except Exception as e:
        print(f"Agent: Failed to connect - {e}")
        return

    # 1. Agent intercepts 402 Payment Required
    if resp.status_code == 402:
        print("Agent: HTTP 402 Payment Required intercepted.")
        payload = resp.json()
        details = extract_payment_details(payload)
        
        print(f"Agent: Protocol demands ${details['amount_usd']:.2f} USDC.")

        # =====================================================================
        # DOORNO.402 PROTECTION LAYER
        # Uncomment the 3 lines below to secure the agent against malicious 402s
        # =====================================================================
        # if not validate_tls(target_url)["valid"]: return print("Agent: 🛑 BLOCKED (Insecure TLS)")
        # if validate_injection(payload).get("injection_detected"): return print("Agent: 🛑 BLOCKED (Prompt Injection)")
        # if not validate_price(payload)["valid"]: return print("Agent: 🛑 BLOCKED (Price Inflation)")
        
        print("Agent: Forwarding payment request to KeeperHub...")
        result = await execute_payment(
            recipient=details["recipient"],
            amount_usd=details["amount_usd"],
            token_address=details["token_address"]
        )
        
        if result.success:
            print(f"Agent: ✅ Payment executed! TxHash: {result.tx_hash}")
        else:
            print(f"Agent: ❌ KeeperHub Error: {result.error}")
            
    elif resp.status_code == 200:
        print("Agent: Successfully fetched data without payment.")
        print(f"Agent: Preview -> {resp.text[:100]}...")
    else:
        print(f"Agent: Unexpected response HTTP {resp.status_code}")

if __name__ == "__main__":
    # Test against the malicious Price Inflation server
    # Note: Make sure the server is running (cd demo/servers/cryptoinsider && node server.js)
    test_url = "http://localhost:3001/api/articles/bitcoin-etf-analysis"
    asyncio.run(run_agent_task(test_url))
