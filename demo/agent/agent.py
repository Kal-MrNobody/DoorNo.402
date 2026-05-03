"""
DoorNo.402 Research Agent

Give it a research topic and a list of website URLs.
The agent discovers content, pays for paywalled articles, reads them,
and delivers a research report.

Usage:
    python demo/agent/agent.py "<topic>" <url1> [url2] ...

Examples:
    python demo/agent/agent.py "bitcoin ETF flows" https://chainwatch-tan.vercel.app
    python demo/agent/agent.py "AI agents web3" https://chainpulse-chi.vercel.app https://nodetimes.vercel.app
    python demo/agent/agent.py "ethereum staking" https://cryptoinsider-nine.vercel.app https://blockbrief-rho.vercel.app
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
LINE = "-" * 60


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
            s = status_resp.json()
            if s.get("status") in ("completed", "failed"):
                return {
                    "success": s["status"] == "completed",
                    "tx_hash": s.get("transactionHash"),
                    "tx_link": s.get("transactionLink"),
                    "error": s.get("error"),
                }

        return {"success": False, "error": "Timed out waiting for KeeperHub"}


def pick_article(articles: list, topic: str) -> dict:
    """Pick the most relevant article for the given research topic."""
    words = topic.lower().split()
    scored = []
    for a in articles:
        text = (a.get("title", "") + " " + a.get("preview", "")).lower()
        score = sum(1 for w in words if w in text)
        scored.append((score, a))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


async def research_site(client: httpx.AsyncClient, base_url: str, topic: str) -> dict:
    """Visit a site, find the best article, pay if needed, return findings."""
    domain = base_url.split("//")[-1].split(".")[0].upper()
    result = {
        "domain": domain,
        "url": base_url,
        "article": None,
        "content": None,
        "paid": False,
        "amount": 0.0,
        "tx": None,
        "server_claim": None,
        "blocked": False,
        "error": None,
    }

    try:
        # Step 1: Discover articles
        r = await client.get(f"{base_url}/api/articles")
        if r.status_code != 200:
            result["error"] = f"No content API (HTTP {r.status_code})"
            return result

        articles = r.json()
        chosen = pick_article(articles, topic)
        result["article"] = chosen.get("title", "Unknown")
        slug = chosen.get("slug", "")

        # Step 2: Request the article
        article_url = f"{base_url}/api/articles/{slug}"
        r2 = await client.get(article_url)

        if r2.status_code == 200:
            # Free content
            data = r2.json()
            result["content"] = data.get("content") or data.get("body") or str(data)[:300]
            return result

        if r2.status_code == 402:
            payload = r2.json()
            req = (payload.get("accepts") or [{}])[0]
            raw = int(req.get("maxAmountRequired", 0))
            amount = raw / 1_000_000 if raw else 5.0
            recipient = req.get("payTo", "")
            token = req.get("asset", "") or DEFAULT_TOKEN
            result["server_claim"] = req.get("description", "")
            result["amount"] = amount

            # Step 3: Pay via KeeperHub
            payment = await execute_keeperhub_payment(recipient, amount, token)

            if not payment["success"]:
                result["error"] = payment.get("error", "Payment failed")
                return result

            result["paid"] = True
            result["tx"] = payment["tx_link"]

            # Step 4: Re-request with payment proof to get content
            r3 = await client.get(
                article_url,
                headers={"X-Payment-Tx": payment["tx_hash"] or "paid"}
            )
            if r3.status_code == 200:
                data = r3.json()
                result["content"] = data.get("content") or str(data)[:300]
            else:
                result["content"] = f"[Payment confirmed but server returned HTTP {r3.status_code}]"

            return result

        if r2.status_code == 403:
            result["blocked"] = True
            return result

        result["error"] = f"HTTP {r2.status_code}"

    except Exception as e:
        result["error"] = str(e)

    return result


def synthesize(topic: str, findings: list[dict]) -> str:
    """Build a research summary from all collected articles."""
    usable = [f for f in findings if f.get("content")]
    if not usable:
        return "No content could be retrieved for this topic."

    lines = []
    for f in usable:
        content = f["content"]
        # Extract sentences most relevant to the topic
        sentences = [s.strip() for s in content.replace("\n", " ").split(".") if s.strip()]
        topic_words = topic.lower().split()
        relevant = [s for s in sentences if any(w in s.lower() for w in topic_words)]
        best = relevant[:2] if relevant else sentences[:2]
        if best:
            lines.append(f"  [{f['domain']}] " + ". ".join(best) + ".")

    if not lines:
        return "Articles were retrieved but contained no sentences directly matching your topic."

    return "\n".join(lines)


async def research(topic: str, urls: list):
    print(f"\n  RESEARCH AGENT")
    print(f"  Topic : \"{topic}\"")
    print(f"  Sites : {len(urls)}")
    print(LINE)

    client = httpx.AsyncClient(timeout=15, follow_redirects=True)

    # =====================================================================
    # DOORNO.402 PROTECTION LAYER
    # Uncomment to protect against malicious paywalls:
    # =====================================================================
    # from doorno402 import protect
    # client = protect(client, daily_budget=1.00)

    findings = []
    total_paid = 0.0

    for url in urls:
        base = url.rstrip("/")
        r = await research_site(client, base, topic)
        findings.append(r)
        domain = r["domain"]

        if r["error"]:
            print(f"\n  {domain}")
            print(f"  ERROR : {r['error']}")
            continue

        if r["blocked"]:
            print(f"\n  {domain}")
            print(f"  BLOCKED : DoorNo.402 rejected this payment")
            continue

        if not r["paid"]:
            print(f"\n  {domain}")
            print(f"  Article : {r['article']}")
            print(f"  Access  : Free (no payment required)")
        else:
            total_paid += r["amount"]
            print(f"\n  {domain}")
            print(f"  Article : {r['article']}")
            print(f"  Claimed : \"{r['server_claim']}\"")
            print(f"  Paid    : ${r['amount']:.2f} USDC")
            print(f"  Tx      : {r['tx']}")

    await client.aclose()

    # Research summary
    print(f"\n{LINE}")
    print(f"  RESEARCH FINDINGS  |  Topic: \"{topic}\"")
    print(LINE)
    summary = synthesize(topic, findings)
    print(summary)
    print(LINE)
    print(f"  Articles retrieved : {len([f for f in findings if f.get('content')])}/{len(findings)}")
    print(f"  Total paid         : ${total_paid:.2f} USDC")
    print(LINE + "\n")


if __name__ == "__main__":
    args = sys.argv[1:]

    if len(args) < 2:
        print("\nUsage:")
        print('  python demo/agent/agent.py "<topic>" <url1> [url2] ...')
        print()
        print("Examples:")
        print('  python demo/agent/agent.py "bitcoin ETF" https://chainwatch-tan.vercel.app')
        print('  python demo/agent/agent.py "AI agents" https://chainpulse-chi.vercel.app https://nodetimes.vercel.app')
        print()
        print("Live sites:")
        print("  https://cryptoinsider-nine.vercel.app  (VULN-01: Price Inflation)")
        print("  https://chainpulse-chi.vercel.app      (VULN-04: Prompt Injection)")
        print("  https://blockbrief-rho.vercel.app      (VULN-05: Budget Drain)")
        print("  https://nodetimes.vercel.app           (VULN-02: Unknown Recipient)")
        print("  https://web3daily-alpha.vercel.app     (VULN-06: TLS Downgrade)")
        print("  https://combo-dusky.vercel.app         (All Vulns Combined)")
        print("  https://chainwatch-tan.vercel.app      (HONEST server)")
        sys.exit(0)

    topic = args[0]
    urls = args[1:]
    asyncio.run(research(topic, urls))
