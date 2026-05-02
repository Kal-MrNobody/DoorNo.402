import httpx
import os
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("KEEPERHUB_API_KEY")
resp = httpx.get(
    "https://app.keeperhub.com/api/execute/uct79jy6hrpd9osy1om6y/status",
    headers={"Authorization": f"Bearer {api_key}"}
)
print(resp.json())
