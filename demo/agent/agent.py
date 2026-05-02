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

async def run_agent_task(target_url: str):
    print("\n[ Agent Started ]")
    print(f"Agent: Requesting resource from {target_url}")
    
    try:
        client = httpx.AsyncClient(timeout=5)
        
        # =====================================================================
        # DOORNO.402 PROTECTION LAYER
        # Uncomment the 2 lines below to secure the agent against malicious 402s
        # =====================================================================
        # from doorno402 import protect
        # client = protect(client, daily_budget=5.00)
        
        resp = await client.get(target_url)
    except Exception as e:
        print(f"Agent: Failed to connect - {e}")
        return
    finally:
        await client.aclose()

    # 1. Agent intercepts 402 Payment Required
    if resp.status_code == 402:
        print("Agent: HTTP 402 Payment Required intercepted.")
        payload = resp.json()
        details = extract_payment_details(payload)
        
        print(f"Agent: Protocol demands ${details['amount_usd']:.2f} USDC.")
        
        print("Agent: Forwarding payment request to KeeperHub...")
        result = await execute_payment(
            recipient=details["recipient"],
            amount_usd=details["amount_usd"],
            token_address=details["token_address"]
        )
        
        if result.success:
            print(f"Agent: ✅ Payment executed!")
            print(f"Agent: 🔗 Basescan Link: {result.tx_link}")
        else:
            print(f"Agent: ❌ KeeperHub Error: {result.error}")
            
    elif resp.status_code == 403:
        print("Agent: 🛑 DoorNo.402 BLOCKED the payment request (Security Policy Violation).")
    elif resp.status_code == 200:
        print("Agent: Successfully fetched data without payment.")
        print(f"Agent: Preview -> {resp.text[:100]}...")
    else:
        print(f"Agent: Unexpected response HTTP {resp.status_code}")

if __name__ == "__main__":
    # Test against the malicious Price Inflation server
    # Note: Make sure the server is running (cd demo/servers/cryptoinsider && node server.js)
    test_url = "http://localhost:3001/api/articles/bitcoin-etf-flows"
    asyncio.run(run_agent_task(test_url))
