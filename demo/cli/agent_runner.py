"""Research agent runner — discovers, scores, pays, collects."""

import os
import asyncio

import httpx
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

KH_BASE = "https://app.keeperhub.com/api"
KH_KEY = os.environ.get("KEEPERHUB_API_KEY", "")
TOKEN = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"


async def fetch_articles(client: httpx.AsyncClient, base_url: str) -> list:
    """GET /api/articles from a server."""
    r = await client.get(f"{base_url}/api/articles")
    if r.status_code != 200:
        return []
    return r.json()


async def fetch_402(client: httpx.AsyncClient, url: str) -> dict | None:
    """GET an article endpoint, return parsed 402 payload or None."""
    r = await client.get(url)
    if r.status_code == 402:
        return {"status": 402, "payload": r.json()}
    if r.status_code == 200:
        return {"status": 200, "payload": r.json()}
    if r.status_code == 403:
        return {"status": 403, "payload": {}}
    return None


async def fetch_content(
    client: httpx.AsyncClient, url: str, tx_hash: str
) -> str | None:
    """Re-fetch with payment proof header to get content."""
    r = await client.get(url, headers={"X-Payment-Tx": tx_hash})
    if r.status_code == 200:
        d = r.json()
        return d.get("content") or d.get("body") or str(d)[:300]
    return None
