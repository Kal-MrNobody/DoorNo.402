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
    {"name": "transfer", "type": "function",
     "inputs": [{"name": "to", "type": "address"}, {"name": "amount", "type": "uint256"}],
     "outputs": [{"type": "bool"}], "stateMutability": "nonpayable"},
]
usdc = w3.eth.contract(address=Web3.to_checksum_address(USDC_CONTRACT), abi=USDC_ABI)


def get_balance():
    raw = usdc.functions.balanceOf(Web3.to_checksum_address(AGENT_ADDRESS)).call()
    return raw / 1_000_000


async def run_unprotected():
    import httpx

    print(f"[agent] mode: UNPROTECTED")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {BLOG_URL}/api/articles/bitcoin-etf-analysis")
    print()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BLOG_URL}/api/articles/bitcoin-etf-analysis")

        if resp.status_code != 402:
            print(f"[agent] got {resp.status_code}, no paywall hit")
            return

        data = resp.json()
        req = data["accepts"][0]
        pay_to = req["payTo"]
        raw_amount = int(req["maxAmountRequired"])
        description = req["description"]

        print(f"[agent] 402 received:")
        print(f"[agent]   description: {description}")
        print(f"[agent]   payTo: {pay_to}")
        print(f"[agent]   maxAmountRequired: {raw_amount} ({raw_amount / 1_000_000:.2f} USDC)")
        print()
        print(f"[agent] agent sees '0.01 USD' in description -- looks cheap")
        print(f"[agent] agent pays the demanded amount blindly...")
        print()

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
        receipt = w3.eth.wait_for_transaction_receipt(tx_hash, timeout=60)

        print(f"[agent] PAYMENT SENT:")
        print(f"[agent]   tx hash: {tx_hash.hex()}")
        print(f"[agent]   status: {'success' if receipt.status == 1 else 'failed'}")
        print(f"[agent]   basescan: https://sepolia.basescan.org/tx/{tx_hash.hex()}")
        print()

        # now fetch content with payment header
        resp2 = await client.get(
            f"{BLOG_URL}/api/articles/bitcoin-etf-analysis",
            headers={"x-payment": tx_hash.hex()}
        )
        if resp2.status_code == 200:
            article = resp2.json()
            print(f"[agent] article received: {article.get('title', 'unknown')}")
            print(f"[agent] content: {article.get('content', '')[:120]}...")

        print()
        print(f"[agent] balance after: {get_balance():.2f} USDC")
        print(f"[agent] EXPLOITED: paid ${raw_amount / 1_000_000:.2f}, description said $0.01")




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
            print(f"[agent] balance: {get_balance():.2f} USDC -- unchanged")


if __name__ == "__main__":
    if PROTECTED:
        asyncio.run(run_protected())
    else:
        asyncio.run(run_unprotected())
