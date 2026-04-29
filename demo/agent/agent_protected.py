import os
import asyncio
import httpx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# ---- the only difference: import the SDK ----
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


def validate_402(data):
    """Run doorno402 validation on the 402 response."""
    from doorno402.validators.price import validate_price
    return validate_price(data)


async def main():
    print("[agent] mode: PROTECTED by doorno402")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {BLOG_URL}/api/articles/bitcoin-etf-analysis")
    print()

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BLOG_URL}/api/articles/bitcoin-etf-analysis")

        if resp.status_code != 402:
            print(f"[agent] got {resp.status_code}, expected 402")
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

        # ---- the SDK does its job here ----
        result = validate_402(data)

        if not result["valid"]:
            print(f"[agent] doorno402 says: {result['reason']}")
            print()
            print(f"[agent] BLOCKED. payment was NOT sent.")
            print(f"[agent] balance: {get_balance():.2f} USDC -- unchanged")
            return

        # if validation passed, pay normally
        print("[agent] doorno402 approved the payment, proceeding...")
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

        print(f"[agent] payment sent: {tx_hash.hex()}")
        print(f"[agent] balance after: {get_balance():.2f} USDC")


if __name__ == "__main__":
    asyncio.run(main())
