import os
import sys
import json
import asyncio
from datetime import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(__file__), '../../.env'))

# Server URLs
SERVERS = {
    "CryptoInsider": os.environ.get("SERVER_CRYPTOINSIDER", "http://localhost:3001"),
    "ChainPulse": os.environ.get("SERVER_CHAINPULSE", "http://localhost:3002"),
    "BlockBrief": os.environ.get("SERVER_BLOCKBRIEF", "http://localhost:3003"),
    "NodeTimes": os.environ.get("SERVER_NODETIMES", "http://localhost:3004"),
    "Web3Daily": os.environ.get("SERVER_WEB3DAILY", "http://localhost:3005"),
    "ComboAttack": os.environ.get("SERVER_COMBO", "http://localhost:3006"),
}

results = []
summary = {
    "total": 0,
    "blocked": 0,
    "allowed": 0,
    "saved_usd": 0.0
}

from x402.clients.httpx import x402HttpxClient
from eth_account import Account
import httpx
from doorno402 import protect, PaymentBlockedError

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../sdk/python')))

# Dummy account for testing
private_key = os.environ.get("AGENT_PRIVATE_KEY", "5e8dfc0c78ce1e0ad8da59c297cc4633d0f8b19aca9a4dc19041b079f74db261")
account = Account.from_key(private_key)

async def test_server(name: str, url: str, expected_vuln: str):
    print(f"\nTesting {name} ({url}) for {expected_vuln}...")
    summary["total"] += 1
    
    # Setup protected client
    client = protect(
        x402HttpxClient(account=account),
        daily_budget=0.50,
        raise_on_block=True
    )
    
    try:
        # Fetch article list to get a slug
        async with httpx.AsyncClient() as basic_client:
            resp = await basic_client.get(f"{url}/api/articles")
            if resp.status_code != 200:
                raise Exception(f"Failed to fetch articles: {resp.status_code}")
            articles = resp.json()
            if not articles:
                raise Exception("No articles found")
            slug = articles[0]["slug"]
        
        # Test 10 articles for BlockBrief to trigger budget
        if expected_vuln == "VULN-05":
            for a in articles:
                try:
                    await client.get(f"{url}/api/articles/{a['slug']}")
                except PaymentBlockedError as e:
                    reason = e.result.get("reason", str(e))
                    results.append({
                        "site": name, "url": url, "vuln": expected_vuln,
                        "result": "BLOCKED", "reason": reason,
                        "before_sdk": "Agent drained of budget", "after_sdk": "Budget enforced ($0.50 max)",
                        "action": "Blocked multiple micro-txs", "tx": "None"
                    })
                    summary["blocked"] += 1
                    return
            raise Exception("Budget drain did not trigger")
        else:
            # Hit protected endpoint
            await client.get(f"{url}/api/articles/{slug}")
            results.append({
                "site": name, "url": url, "vuln": expected_vuln,
                "result": "ALLOWED", "reason": "Passed validation",
                "before_sdk": "Payment sent", "after_sdk": "Payment sent securely",
                "action": "Allowed execution", "tx": "0xabc123... (Simulation)"
            })
            summary["allowed"] += 1
    except PaymentBlockedError as e:
        reason = e.result.get("reason", str(e))
        raw_usd = 0.0
        if "demanded" in reason.lower() or "price" in expected_vuln.lower():
            # Estimate saved for VULN-01
            raw_usd = 5.0
            summary["saved_usd"] += raw_usd
        elif expected_vuln == "VULN-06":
            raw_usd = 0.01
            summary["saved_usd"] += raw_usd
        elif expected_vuln == "VULN-04":
            raw_usd = 0.01
            summary["saved_usd"] += raw_usd
        
        results.append({
            "site": name, "url": url, "vuln": expected_vuln,
            "result": "BLOCKED", "reason": reason,
            "before_sdk": f"Agent pays malicious amount", "after_sdk": f"Intercepted before tx",
            "action": "Blocked", "tx": "None"
        })
        summary["blocked"] += 1
    except Exception as e:
        print(f"Error testing {name}: {e}")

async def main():
    print("Starting multi-server security scan...")
    await test_server("CryptoInsider", SERVERS["CryptoInsider"], "VULN-01")
    await test_server("ChainPulse", SERVERS["ChainPulse"], "VULN-04")
    await test_server("BlockBrief", SERVERS["BlockBrief"], "VULN-05")
    await test_server("NodeTimes", SERVERS["NodeTimes"], "VULN-02")
    await test_server("Web3Daily", SERVERS["Web3Daily"], "VULN-06")
    await test_server("ComboAttack", SERVERS["ComboAttack"], "VULN-ALL")
    
    # Table output will go here

if __name__ == "__main__":
    asyncio.run(main())
