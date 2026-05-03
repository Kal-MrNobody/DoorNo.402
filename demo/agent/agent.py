"""
DoorNo.402 Research Agent

Usage:
    python demo/agent/agent.py <topic> <url1> [url2] [url3] ...

Example:
    python demo/agent/agent.py "bitcoin ETF flows" https://cryptoinsider-nine.vercel.app https://chainpulse-chi.vercel.app

The agent will:
  - Visit each site, discover paywalled articles
  - Pay for access autonomously via KeeperHub
  - Summarize what it found about your research topic
"""

import os
import sys
import asyncio
import httpx
from dotenv import load_dotenv

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

KEEPERHUB_API_KEY = os.environ.get("KEEPERHUB_API_KEY", "")
DEFAULT_TOKEN = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"

DIVIDER = "-" * 58


async def execute_keeperhub_payment(recipient: str, amount_usd: float, token_address: str):
    """Executes a transaction via KeeperHub Direct Execution API."""
    if not KEEPERHUB_API_KEY:
        return {"success": False, "error": "KEEPERHUB_API_KEY not set in .env"}

    headers = {"Authorization": f"Bearer {KEEPERHUB_API_KEY}"}

    async with httpx.AsyncClient(timeout=30) as kh:
        resp = await kh.post(
            "https://app.keeperhub.com/api/execute/transfer",
            headers=headers,
            json={
                "network": "base-sepolia",
                "recipientAddress": recipient,
                "amount": f"{amount_usd:.6f}",
                "tokenAddress": token_address.lower(),
            }
        )
        data = resp.json()
        execution_id = data.get("executionId")
        if not execution_id:
            return {"success": False, "error": data.get("error", "Failed to start execution")}

        for _ in range(30):
            await asyncio.sleep(3)
            status_resp = await kh.get(
                f"https://app.keeperhub.com/api/execute/{execution_id}/status",
                headers=headers
            )
            status_data = status_resp.json()
            status = status_data.get("status")
            if status in ("completed", "failed"):
                return {
                    "success": status == "completed",
                    "tx_hash": status_data.get("transactionHash"),
                    "tx_link": status_data.get("transactionLink"),
                    "error": status_data.get("error"),
                    "balance_after": status_data.get("balanceAfter"),
                }

        return {"success": False, "error": "Timed out waiting for KeeperHub"}


async def fetch_site(client: httpx.AsyncClient, base_url: str, topic: str) -> dict:
    """Visit a site, find articles, pay if needed, return findings."""
    result = {
        "site": base_url,
        "articles_found": [],
        "article_title": None,
        "paid": False,
        "amount_usd": 0.0,
        "tx_link": None,
        "blocked": False,
        "content": None,
        "server_claim": None,
        "error": None,
    }

    try:
        # Discover articles
        api_resp = await client.get(f"{base_url}/api/articles")
        if api_resp.status_code != 200:
            result["error"] = f"No content API found (HTTP {api_resp.status_code})"
            return result

        articles = api_resp.json()
        result["articles_found"] = [a.get("title", "?") for a in articles]

        # Pick the most relevant article to the topic
        topic_lower = topic.lower()
        chosen = articles[0]
        for a in articles:
            if any(word in a.get("title", "").lower() for word in topic_lower.split()):
                chosen = a
                break

        result["article_title"] = chosen.get("title", "Unknown")
        slug = chosen.get("slug", "")
        article_resp = await client.get(f"{base_url}/api/articles/{slug}")

        if article_resp.status_code == 200:
            # Free article — no payment needed
            data = article_resp.json()
            result["content"] = data.get("content", data.get("body", "Content available"))
            result["paid"] = False
            return result

        if article_resp.status_code == 402:
            payload = article_resp.json()
            accepts = payload.get("accepts", [{}])
            req = accepts[0] if accepts else {}

            raw = int(req.get("maxAmountRequired", 0))
            amount_usd = raw / 1_000_000 if raw else 5.0
            recipient = req.get("payTo", "")
            description = req.get("description", "")
            token_address = req.get("asset", "") or req.get("token", "") or DEFAULT_TOKEN

            result["amount_usd"] = amount_usd
            result["server_claim"] = description
            result["recipient"] = recipient

            # Pay via KeeperHub
            payment = await execute_keeperhub_payment(recipient, amount_usd, token_address)

            if payment["success"]:
                result["paid"] = True
                result["tx_link"] = payment["tx_link"]
                result["content"] = f"[Article unlocked: '{result['article_title']}']"
            else:
                result["error"] = payment.get("error")
            return result

        if article_resp.status_code == 403:
            result["blocked"] = True
            return result

        result["error"] = f"Unexpected HTTP {article_resp.status_code}"

    except Exception as e:
        result["error"] = str(e)

    return result


async def research(topic: str, urls: list[str]):
    print(f"\n  RESEARCH AGENT  |  Topic: \"{topic}\"")
    print(f"  Sites to scan: {len(urls)}")
    print(DIVIDER)

    client = httpx.AsyncClient(timeout=10, follow_redirects=True)

    # =====================================================================
    # DOORNO.402 PROTECTION LAYER
    # Uncomment to enable security (blocks malicious paywalls):
    # =====================================================================
    # from doorno402 import protect
    # client = protect(client, daily_budget=5.00)

    total_spent = 0.0
    findings = []

    for url in urls:
        base_url = url.rstrip("/")
        domain = base_url.split("//")[-1].split(".")[0]
        print(f"\n  {domain.upper()}")

        r = await fetch_site(client, base_url, topic)

        if r["error"]:
            print(f"  ERROR: {r['error']}")
            continue

        if r["blocked"]:
            print(f"  BLOCKED by DoorNo.402 — payment rejected")
            continue

        if not r["paid"]:
            print(f"  Access: FREE (no payment required)")
            if r["content"]:
                preview = str(r["content"])[:120].replace("\n", " ")
                print(f"  Content: {preview}...")
            findings.append(r)
            continue

        # Paid article
        total_spent += r["amount_usd"]
        claim = r.get("server_claim", "")
        actual = r["amount_usd"]
        recipient = r.get("recipient", "")[:10] + "..." + r.get("recipient", "")[-6:]

        print(f"  Article  : {r['article_title']}")
        print(f"  Paywall  : \"{claim}\"")
        print(f"  Paid     : ${actual:.2f} USDC  ->  {recipient}")
        print(f"  Tx       : {r['tx_link']}")
        findings.append(r)

    await client.aclose()

    print(f"\n{DIVIDER}")
    print(f"  RESEARCH SUMMARY")
    print(DIVIDER)
    print(f"  Topic     : {topic}")
    print(f"  Sites     : {len(urls)}")
    print(f"  Articles  : {len(findings)}")
    print(f"  Total paid: ${total_spent:.2f} USDC")
    print(DIVIDER)
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args:
        # Default demo
        topic = "bitcoin ETF institutional flows"
        urls = [
            "https://cryptoinsider-nine.vercel.app",
            "https://blockbrief-rho.vercel.app",
        ]
    elif len(args) == 1:
        print("Usage: python agent.py <topic> <url1> [url2] ...")
        print("Example: python agent.py 'bitcoin ETF' https://cryptoinsider-nine.vercel.app")
        sys.exit(1)
    else:
        topic = args[0]
        urls = args[1:]

    asyncio.run(research(topic, urls))
