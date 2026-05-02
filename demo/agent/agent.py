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

# Add SDK to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

async def execute_keeperhub_payment(recipient: str, amount_usd: float, token_address: str):
    """Executes a transaction via KeeperHub Direct Execution API."""
    api_key = os.environ.get("KEEPERHUB_API_KEY", "")
    
    # 1. Initiate Transfer
    async with httpx.AsyncClient() as kh_client:
        resp = await kh_client.post(
            "https://app.keeperhub.com/api/execute/transfer",
            headers={"Authorization": f"Bearer {api_key}"},
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

        # 2. Poll for Completion
        while True:
            status_resp = await kh_client.get(
                f"https://app.keeperhub.com/api/execute/{execution_id}/status",
                headers={"Authorization": f"Bearer {api_key}"}
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            
            if status == "completed":
                return {
                    "success": True, 
                    "tx_hash": status_data.get("transactionHash"),
                    "tx_link": status_data.get("transactionLink")
                }
            elif status == "failed":
                return {"success": False, "error": status_data.get("error", "Unknown KeeperHub Error")}
            
            await asyncio.sleep(2)


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
        print(f"Agent: Failed to connect or blocked - {e}")
        return
    finally:
        await client.aclose()

    # 1. Agent intercepts 402 Payment Required
    if resp.status_code == 402:
        print("Agent: HTTP 402 Payment Required intercepted.")
        payload = resp.json()
        
        # Extract fields from standard x402 payload
        amount_usd = float(payload.get("amount", 0)) / 1000000.0 if "amount" in payload else 5.0
        recipient = payload.get("recipient", "")
        token_address = payload.get("asset") or payload.get("token") or "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        
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
