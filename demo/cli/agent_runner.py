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


def score_articles(articles: list, topic: str) -> dict:
    """Pick the most relevant article for a research topic."""
    words = topic.lower().split()
    best, best_score = articles[0], 0
    for a in articles:
        text = (a.get("title", "") + " " + a.get("preview", "")).lower()
        s = sum(1 for w in words if w in text)
        if s > best_score:
            best, best_score = a, s
    return best


def extract_402(payload: dict) -> dict:
    """Parse x402 payment details from a 402 response body."""
    req = (payload.get("accepts") or [{}])[0]
    raw = int(req.get("maxAmountRequired", 0))
    return {
        "recipient": req.get("payTo", ""),
        "amount": raw / 1_000_000 if raw else 5.0,
        "description": req.get("description", ""),
        "token": req.get("asset", "") or TOKEN,
    }


async def keeperhub_pay(recipient: str, amount: float, token: str) -> dict:
    """Execute payment via KeeperHub. Returns {success, tx_hash, tx_link, error}."""
    if not KH_KEY:
        return {"success": False, "error": "KEEPERHUB_API_KEY not set"}
    headers = {"Authorization": f"Bearer {KH_KEY}"}
    async with httpx.AsyncClient(timeout=30) as kh:
        r = await kh.post(f"{KH_BASE}/execute/transfer", headers=headers, json={
            "network": "base-sepolia",
            "recipientAddress": recipient,
            "amount": f"{amount:.6f}",
            "tokenAddress": token.lower(),
        })
        eid = r.json().get("executionId")
        if not eid:
            return {"success": False, "error": r.json().get("error", "no id")}
        for _ in range(30):
            await asyncio.sleep(3)
            s = (await kh.get(
                f"{KH_BASE}/execute/{eid}/status", headers=headers
            )).json()
            if s.get("status") in ("completed", "failed"):
                return {
                    "success": s["status"] == "completed",
                    "tx_hash": s.get("transactionHash", ""),
                    "tx_link": s.get("transactionLink", ""),
                    "error": s.get("error"),
                }
    return {"success": False, "error": "timeout"}
