"""
DoorNo.402 x KeeperHub Standalone Integration Example

This script demonstrates exactly how an AI Agent developer uses 
KeeperHub to execute x402 payments, and how DoorNo.402 secures it.

To make this agent SECURE, simply uncomment the DoorNo.402 protection block.
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

async def execute_keeperhub_payment(recipient: str, amount_usd: float, token_address: str):
    """Executes a transaction via KeeperHub Direct Execution API."""
    api_key = os.environ.get("KEEPERHUB_API_KEY", "")
    if not api_key:
        return {"success": False, "error": "KEEPERHUB_API_KEY not set in .env"}

    headers = {"Authorization": f"Bearer {api_key}"}

    # 1. Initiate Transfer
    async with httpx.AsyncClient(timeout=30) as kh_client:
        resp = await kh_client.post(
            "https://app.keeperhub.com/api/execute/transfer",
            headers=headers,
            json={
                "network": "base-sepolia",
                "recipientAddress": recipient,
                "amount": f"{amount_usd:.6f}",
                "tokenAddress": token_address.lower(),
            }
        )
        data = resp.json()
        execution_id = data.get("executionId")

        if not execution_id:
            return {"success": False, "error": data.get("error", "Failed to start execution")}

        # 2. Poll for Completion (up to 90 seconds)
        for _ in range(30):
            await asyncio.sleep(3)
            status_resp = await kh_client.get(
                f"https://app.keeperhub.com/api/execute/{execution_id}/status",
                headers=headers
            )
            status_data = status_resp.json()
            status = status_data.get("status")

            if status in ("completed", "failed"):
                return {
                    "success": status == "completed",
                    "tx_hash": status_data.get("transactionHash"),
                    "tx_link": status_data.get("transactionLink"),
                    "error": status_data.get("error")
                }

        return {"success": False, "error": "Timed out waiting for KeeperHub"}



async def run_agent_task(target_url: str):
    print("\n[ Agent Started ]")
    print(f"Agent: Requesting resource from {target_url}")
    
    try:
        client = httpx.AsyncClient(timeout=5)
        
        # =====================================================================
        # DOORNO.402 PROTECTION LAYER
        # =====================================================================
        #from doorno402 import protect
        #client = protect(client, daily_budget=5.00)
        
        resp = await client.get(target_url)
    except Exception as e:
        print(f"Agent: Failed to connect or blocked - {e}")
        return
    finally:
        await client.aclose()

    # 1. Agent intercepts 402 Payment Required
    if resp.status_code == 402:
        print("Agent: HTTP 402 Payment Required intercepted.")
        payload = resp.json()
        
        # Extract fields from standard x402 payload
        accepts = payload.get("accepts", [{}])
        req = accepts[0] if accepts else {}
        raw_amount = int(req.get("maxAmountRequired", 0))
        amount_usd = raw_amount / 1000000.0 if raw_amount else 5.0
        recipient = req.get("payTo", "")
        token_address = req.get("asset", "") or req.get("token", "") or "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        
        print(f"Agent: Protocol demands ${amount_usd:.2f} USDC.")
        print("Agent: Forwarding payment request to KeeperHub...")
        
        # 2. Agent executes the payment via KeeperHub
        result = await execute_keeperhub_payment(recipient, amount_usd, token_address)
        
        if result["success"]:
            print(f"Agent: ✅ Payment executed!")
            print(f"Agent: 🔗 Basescan Link: {result['tx_link']}")
        else:
            print(f"Agent: ❌ KeeperHub Error: {result['error']}")
            
    elif resp.status_code == 403:
        print("Agent: 🛑 DoorNo.402 BLOCKED the payment request (Security Policy Violation).")
    elif resp.status_code == 200:
        print("Agent: Successfully fetched data without payment.")
    else:
        print(f"Agent: Unexpected response HTTP {resp.status_code}")


if __name__ == "__main__":
    # Test against the malicious Price Inflation server
    # Note: Make sure the server is running (node demo/servers/cryptoinsider/server.js)
    test_url = "http://localhost:3001/api/articles/bitcoin-etf-flows"
    asyncio.run(run_agent_task(test_url))
