"""DoorNo.402 + KeeperHub Integration Demo

Flow: DoorNo.402 validates -> KeeperHub executes
"""
import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv
from eth_account import Account

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), "..", "..", "sdk", "python"
))
from doorno402 import protect, PaymentBlockedError

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

KEEPERHUB_API_KEY = os.environ.get("KEEPERHUB_API_KEY", "")
KEEPERHUB_MCP_URL = "https://mcp.keeperhub.com/sse"
BLOG_URL = os.getenv("BLOG_URL", "http://localhost:3000")
PRIVATE_KEY = os.environ["AGENT_PRIVATE_KEY"]
AGENT_ADDRESS = os.environ["AGENT_ADDRESS"]

account = Account.from_key(PRIVATE_KEY)


async def execute_via_keeperhub(payment_details: dict) -> dict:
    """Forward a validated payment to KeeperHub for execution."""
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{KEEPERHUB_MCP_URL}/execute",
            json={"payment": payment_details},
            headers={"Authorization": f"Bearer {KEEPERHUB_API_KEY}"},
            timeout=30,
        )
        return resp.json()


async def main():
    print("[demo] DoorNo.402 + KeeperHub Integration")
    print("[demo] Flow: validate with DoorNo.402 -> execute with KeeperHub")
    print()

    async with httpx.AsyncClient() as client:
        client = protect(
            client,
            daily_budget=10.00,
            raise_on_block=True,
        )
        try:
            print("[demo] Fetching premium article...")
            resp = await client.get(
                f"{BLOG_URL}/api/articles/bitcoin-etf-analysis"
            )
            print(f"[demo] DoorNo.402 approved payment")
            print(f"[demo] Forwarding to KeeperHub for execution...")
            result = await execute_via_keeperhub({
                "url": f"{BLOG_URL}/api/articles/bitcoin-etf-analysis",
                "status": "validated",
                "agent": AGENT_ADDRESS,
            })
            print(f"[demo] KeeperHub executed: {result}")
            print(f"[demo] Response: {resp.status_code}")
        except PaymentBlockedError as e:
            print(f"[demo] DoorNo.402 blocked before KeeperHub: {e}")
            print("[demo] KeeperHub never saw the malicious request")


if __name__ == "__main__":
    asyncio.run(main())
