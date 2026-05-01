import asyncio
import httpx

async def hook(resp):
    print("Hook running...")
    resp.status_code = 403

async def main():
    async with httpx.AsyncClient() as client:
        client.event_hooks["response"].append(hook)
        resp = await client.get("http://localhost:3000/api/articles/bitcoin-etf-analysis")
        print("Status:", resp.status_code)

asyncio.run(main())
