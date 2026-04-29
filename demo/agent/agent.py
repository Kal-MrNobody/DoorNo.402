import os
import sys
import asyncio
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

load_dotenv()

BLOG_URL = os.getenv("BLOG_URL", "http://localhost:3000")
PRIVATE_KEY = os.environ["AGENT_PRIVATE_KEY"]
AGENT_ADDRESS = os.environ["AGENT_ADDRESS"]
PROTECTED = False

USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC_URL = "https://sepolia.base.org"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)

USDC_ABI = [
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "a", "type": "address"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view"},
]
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=USDC_ABI)


def get_balance():
    raw = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    return raw / 1_000_000


async def run_unprotected():
    from x402.clients.httpx import x402HttpxClient

    print(f"[agent] mode: UNPROTECTED")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {BLOG_URL}/api/articles/bitcoin-etf-analysis")
    print()

    async with x402HttpxClient(account=account) as client:
        resp = await client.get(f"{BLOG_URL}/api/articles/bitcoin-etf-analysis")
        print(f"[agent] response: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"[agent] article: {data.get('title', 'unknown')}")
            print(f"[agent] content: {data.get('content', '')[:120]}...")
        print()
        print(f"[agent] balance after: {get_balance():.2f} USDC")
        print(f"[agent] Agent paid $5.00. Description claimed $0.01. No validation was done.")


async def run_protected():
    from x402.clients.httpx import x402HttpxClient

    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))
    from doorno402 import protect, PaymentBlockedError

    print(f"[agent] mode: PROTECTED by DoorNo.402")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {BLOG_URL}/api/articles/bitcoin-etf-analysis")
    print()

    async with x402HttpxClient(account=account) as client:
        client = protect(client)
        try:
            resp = await client.get(f"{BLOG_URL}/api/articles/bitcoin-etf-analysis")
            print(f"[agent] response: {resp.status_code}")
        except PaymentBlockedError as e:
            print(f"\n[agent] DoorNo.402 stopped a fraudulent payment. $5.00 was NOT sent.")
            print(f"[agent] balance: {get_balance():.2f} USDC — unchanged")


if __name__ == "__main__":
    if PROTECTED:
        asyncio.run(run_protected())
    else:
        asyncio.run(run_unprotected())
