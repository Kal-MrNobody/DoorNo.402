import httpx
import os
import time
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KEEPERHUB_API_KEY")
resp = httpx.post(
    "https://app.keeperhub.com/api/execute/transfer",
    headers={"Authorization": f"Bearer {api_key}"},
    timeout=30,
    json={
        "network": "base-sepolia",
        "recipientAddress": "0x3526cd391Aa5B4E8ca65C51235d40612d9F74822",
        "amount": "5.000000",
        "tokenAddress": "0x036cbd53842c5426634e7929541ec2318f3dcf7e",
    }
)
print("POST Status:", resp.status_code)
data = resp.json()
print("POST Response:", data)

if "executionId" in data:
    time.sleep(2)
    poll_resp = httpx.get(
        f"https://app.keeperhub.com/api/execute/{data['executionId']}/status",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    print("POLL Response:", poll_resp.json())
