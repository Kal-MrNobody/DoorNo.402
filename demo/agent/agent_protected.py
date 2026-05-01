"""DoorNo.402 — Protected Agent Demo

The ONLY difference from agent_vulnerable.py is TWO lines:
  1. from doorno402 import protect, PaymentBlockedError
  2. client = protect(client)

That's it. The SDK handles injection scanning, price validation,
ENS trust scoring, and budget enforcement automatically.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# ─── THIS IS THE ONLY IMPORT YOU ADD ───
from doorno402 import protect, PaymentBlockedError

load_dotenv()

BLOG_URL = os.getenv("BLOG_URL", "http://localhost:3000")
PRIVATE_KEY = os.environ["AGENT_PRIVATE_KEY"]
AGENT_ADDRESS = os.environ["AGENT_ADDRESS"]

USDC_CONTRACT = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
RPC_URL = "https://sepolia.base.org"

w3 = Web3(Web3.HTTPProvider(RPC_URL))
account = Account.from_key(PRIVATE_KEY)

USDC_ABI = [
    {"name": "balanceOf", "type": "function", "inputs": [{"name": "a", "type": "address"}],
     "outputs": [{"type": "uint256"}], "stateMutability": "view"},
    {"name": "transfer", "type": "function",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"},
]
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=USDC_ABI)


def get_balance():
    raw = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    return raw / 1_000_000


async def main():
    url = f"{BLOG_URL}/api/articles/bitcoin-etf-analysis"
    print("[agent] mode: PROTECTED by doorno402")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {url}")
    print()

    async with httpx.AsyncClient() as client:
        # ─── THIS IS THE ONLY LINE YOU ADD ───
        client = protect(client, daily_budget=5.00)

        resp = await client.get(url)

        # If we get here, the SDK approved the payment as legitimate (or converted a block to 403)
        if resp.status_code == 402:
            data = resp.json()
            req = data["accepts"][0]
            pay_to = req["payTo"]
            raw_amount = int(req["maxAmountRequired"])

            print(f"[agent] ✓ doorno402 approved -- payment is legitimate")
            print(f"[agent] paying ${raw_amount / 1_000_000:.2f} to {pay_to[:10]}...")

            tx = usdc.functions.transfer(
                Web3.to_checksum_address(pay_to), raw_amount
            ).build_transaction({
                "from": Web3.to_checksum_address(AGENT_ADDRESS),
                "nonce": w3.eth.get_transaction_count(Web3.to_checksum_address(AGENT_ADDRESS)),
                "gas": 100000,
                "gasPrice": w3.eth.gas_price,
            })
            signed = account.sign_transaction(tx)
            tx_hash = w3.eth.send_raw_transaction(signed.raw_transaction)
            w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)
            print(f"[agent] paid: https://sepolia.basescan.org/tx/{tx_hash.hex()}")

        elif resp.status_code == 200:
            article = resp.json()
            print(f"[agent] article: {article.get('title')}")
            print(f"[agent] content: {article.get('content', '')[:120]}...")

        print()
        print(f"[agent] balance after: {get_balance():.2f} USDC")


if __name__ == "__main__":
    asyncio.run(main())
