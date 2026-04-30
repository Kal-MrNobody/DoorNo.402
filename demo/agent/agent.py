"""DoorNo.402 — Single Agent Demo

This script demonstrates how vulnerable a standard AI agent is, 
and how adding exactly TWO LINES of code completely secures it.

Instructions for Demo:
1. Run as-is to see the agent blindly pay a malicious invoice.
2. Uncomment the two lines labeled below.
3. Run again to see the SDK intercept and block the attack.
"""

import os
import asyncio
import httpx
from dotenv import load_dotenv
from eth_account import Account
from web3 import Web3

# ─── ADD LINE 1: Import the SDK ───
# from doorno402 import protect

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
    # Pointing to the attack server (VULN-01 Price Inflation)
    url = "http://localhost:4000/vuln01"
    
    print("[agent] mode: LIVE DEMO")
    print(f"[agent] wallet: {AGENT_ADDRESS}")
    print(f"[agent] balance: {get_balance():.2f} USDC")
    print(f"[agent] target: {url}")
    print()

    async with httpx.AsyncClient() as client:
        # ─── ADD LINE 2: Wrap the client ───
        # client = protect(client, daily_budget=5.00)

        # 1. Agent fetches the resource
        resp = await client.get(url)

        # 2. Server demands payment (402)
        if resp.status_code == 402:
            data = resp.json()
            req = data["accepts"][0]
            pay_to = req["payTo"]
            raw_amount = int(req["maxAmountRequired"])

            print(f"[agent] 402 Payment Required")
            print(f"[agent] description says: {req['description']}")
            print(f"[agent] agent blindly trusts description and attempts to pay {raw_amount / 1_000_000:.2f} USDC...")

            # 3. Build and send transaction
            try:
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
                
                print(f"[agent] PAYMENT SENT: https://sepolia.basescan.org/tx/{tx_hash.hex()}")
                
                # 4. Fetch the resource again with proof of payment
                print(f"[agent] Requesting resource again with proof of payment...")
                resp2 = await client.get(url, headers={"x-payment": tx_hash.hex()})
                if resp2.status_code == 200:
                    data2 = resp2.json()
                    print(f"[agent] DATA RECEIVED: {data2.get('message', data2)}")
                
            except Exception as e:
                print(f"[agent] Transaction failed: {e}")

        elif resp.status_code == 200:
            print("[agent] Successfully accessed the resource!")
            
        print()
        import time
        time.sleep(4)  # Wait for RPC node to sync the new block
        print(f"[agent] balance after: {get_balance():.2f} USDC")

if __name__ == "__main__":
    asyncio.run(main())
