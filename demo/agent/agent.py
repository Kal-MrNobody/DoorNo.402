"""
DoorNo.402 Research Agent

Usage:
    python demo/agent/agent.py "<topic>" <url1> [url2] ...

Example:
    python demo/agent/agent.py "bitcoin ETF" https://chainwatch-tan.vercel.app https://blockbrief-rho.vercel.app
"""

import os, sys, asyncio, httpx
from dotenv import load_dotenv

if sys.platform == "win32":
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "sdk", "python"))
load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))

API_KEY   = os.environ.get("KEEPERHUB_API_KEY", "")
KH_BASE   = "https://app.keeperhub.com/api"
DEF_TOKEN = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"


async def get_balance(kh: httpx.AsyncClient) -> float:
    """Fetch current USDC balance from KeeperHub."""
    try:
        r = await kh.get(f"{KH_BASE}/wallet/balance",
                         headers={"Authorization": f"Bearer {API_KEY}"})
        return float(r.json().get("balance", 0))
    except Exception:
        return -1.0


async def pay(kh: httpx.AsyncClient, recipient: str, amount: float, token: str) -> dict:
    r = await kh.post(f"{KH_BASE}/execute/transfer",
                      headers={"Authorization": f"Bearer {API_KEY}"},
                      json={"network": "base-sepolia",
                            "recipientAddress": recipient,
                            "amount": f"{amount:.6f}",
                            "tokenAddress": token.lower()})
    data = r.json()
    eid = data.get("executionId")
    if not eid:
        return {"success": False, "error": data.get("error", "no executionId")}

    for _ in range(30):
        await asyncio.sleep(3)
        s = (await kh.get(f"{KH_BASE}/execute/{eid}/status",
                          headers={"Authorization": f"Bearer {API_KEY}"})).json()
        if s.get("status") in ("completed", "failed"):
            return {
                "success": s["status"] == "completed",
                "tx_hash": s.get("transactionHash", ""),
                "tx_link": s.get("transactionLink", ""),
                "balance_after": float(s.get("balanceAfter", -1)),
                "error": s.get("error"),
            }
    return {"success": False, "error": "timeout"}


async def research(topic: str, urls: list):
    async with httpx.AsyncClient(timeout=15, follow_redirects=True) as kh:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as web:

            # =====================================================================
            # DOORNO.402 PROTECTION LAYER — uncomment to enable security
            # =====================================================================
            #from doorno402 import protect
            #web = protect(web, daily_budget=1.00)

            print()
            for url in urls:
                base   = url.rstrip("/")
                domain = base.split("//")[-1].split(".")[0].upper()

                try:
                    # Discover articles
                    arts = (await web.get(f"{base}/api/articles")).json()
                    # Pick most relevant
                    words = topic.lower().split()
                    scored = sorted(arts,
                                    key=lambda a: sum(1 for w in words if w in (a.get("title","")+" "+a.get("preview","")).lower()),
                                    reverse=True)
                    pick  = scored[0]
                    slug  = pick["slug"]
                    title = pick["title"]

                    r402 = await web.get(f"{base}/api/articles/{slug}")

                    if r402.status_code == 200:
                        data = r402.json()
                        content = str(data.get("content", data))[:120]
                        print(f"[{domain}] {title}")
                        print(f"  access  free (no paywall)")
                        print(f"  content \"{content}\"")
                        print()
                        continue

                    if r402.status_code != 402:
                        print(f"[{domain}] unexpected HTTP {r402.status_code}")
                        print()
                        continue

                    payload  = r402.json()
                    req      = (payload.get("accepts") or [{}])[0]
                    claimed  = req.get("description", "")
                    raw      = int(req.get("maxAmountRequired", 0))
                    amount   = raw / 1_000_000 if raw else 5.0
                    recip    = req.get("payTo", "")
                    token    = req.get("asset", "") or DEF_TOKEN

                    bal_before = await get_balance(kh)
                    result     = await pay(kh, recip, amount, token)

                    if not result["success"]:
                        print(f"[{domain}] payment failed: {result.get('error')}")
                        print()
                        continue

                    bal_after = result["balance_after"]
                    tx_link   = result["tx_link"]
                    tx_short  = result["tx_hash"][:10] + "..." + result["tx_hash"][-8:]

                    # Re-fetch with payment proof
                    r200 = await web.get(f"{base}/api/articles/{slug}",
                                         headers={"X-Payment-Tx": result["tx_hash"]})
                    content = ""
                    if r200.status_code == 200:
                        d = r200.json()
                        content = str(d.get("content", ""))[:120]

                    bal_str = (f"${bal_before:.2f} → ${bal_after:.2f}"
                               if bal_before >= 0 and bal_after >= 0
                               else f"-${amount:.2f}")

                    print(f"[{domain}] {title}")
                    print(f"  402     \"{claimed}\"  →  charged ${amount:.2f} USDC")
                    print(f"  wallet  {bal_str} USDC")
                    print(f"  tx      {tx_link}")
                    print(f"  content \"{content}\"")
                    print()

                except Exception as e:
                    print(f"[{domain}] error: {e}")
                    print()


if __name__ == "__main__":
    args = sys.argv[1:]
    if len(args) < 2:
        print("Usage: python agent.py \"<topic>\" <url1> [url2] ...")
        print()
        print("Sites:")
        print("  https://cryptoinsider-nine.vercel.app  (Price Inflation)")
        print("  https://chainpulse-chi.vercel.app      (Prompt Injection)")
        print("  https://chainwatch-tan.vercel.app      (Honest)")
        print("  https://nodetimes.vercel.app           (Unknown Recipient)")
        print("  https://web3daily-alpha.vercel.app     (TLS Downgrade)")
        print("  https://blockbrief-rho.vercel.app      (Budget Drain)")
        print("  https://combo-dusky.vercel.app         (All Vulns)")
        sys.exit(0)

    asyncio.run(research(args[0], args[1:]))
