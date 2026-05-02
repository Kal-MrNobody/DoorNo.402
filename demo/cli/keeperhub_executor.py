"""KeeperHub Direct Execution API client for DoorNo.402 CLI."""

import os
import asyncio
import httpx
from dataclasses import dataclass

KEEPERHUB_BASE = "https://app.keeperhub.com"


@dataclass
class ExecutionResult:
    success: bool
    execution_id: str
    status: str
    tx_hash: str | None
    tx_link: str | None
    error: str | None


async def execute_payment(
    recipient: str,
    amount_usd: float,
    token_address: str,
) -> ExecutionResult:
    """Execute a USDC transfer via KeeperHub Direct Execution API."""
    api_key = os.environ.get("KEEPERHUB_API_KEY", "")
    if not api_key:
        return ExecutionResult(
            success=False,
            execution_id="",
            status="error",
            tx_hash=None,
            tx_link=None,
            error="KEEPERHUB_API_KEY not set in .env",
        )

    payload = {
        "network": "base-sepolia",
        "recipientAddress": recipient,
        "amount": f"{amount_usd:.6f}",
        "tokenAddress": token_address,
        "tokenConfig": '{"decimals":6,"symbol":"USDC"}',
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.post(
                f"{KEEPERHUB_BASE}/api/execute/transfer",
                json=payload,
                headers=headers,
            )
            if not resp.is_success:
                return ExecutionResult(
                    success=False,
                    execution_id="",
                    status=f"http_{resp.status_code}",
                    tx_hash=None,
                    tx_link=None,
                    error=resp.text[:200],
                )

            data = resp.json()
            execution_id = data.get("executionId", "")
            status = data.get("status", "unknown")

            # Poll for completion
            status_data = await get_execution_status(execution_id, api_key)
            final_status = status_data.get("status", status)
            return ExecutionResult(
                success=(final_status == "completed"),
                execution_id=execution_id,
                status=final_status,
                tx_hash=status_data.get("transactionHash"),
                tx_link=status_data.get("transactionLink"),
                error=status_data.get("error"),
            )
    except Exception as e:
        return ExecutionResult(
            success=False,
            execution_id="",
            status="error",
            tx_hash=None,
            tx_link=None,
            error=str(e)[:200],
        )


async def get_execution_status(
    execution_id: str,
    api_key: str,
) -> dict:
    """Poll KeeperHub for execution status until completed or failed."""
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            for _ in range(30): # Poll up to 90 seconds (testnets can be slow)
                resp = await client.get(
                    f"{KEEPERHUB_BASE}/api/execute/{execution_id}/status",
                    headers=headers,
                )
                data = resp.json()
                if data.get("status") in ("completed", "failed"):
                    return data
                await asyncio.sleep(3)
    except Exception:
        pass
    return {"status": "timeout"}


def extract_payment_details(payload: dict) -> dict:
    """Extract payment details from a 402 response payload."""
    accepts = payload.get("accepts", [{}])
    req = accepts[0] if accepts else {}
    raw = int(req.get("maxAmountRequired", 0))
    # Default to Base Sepolia USDC if asset is missing
    token = req.get("asset", "")
    if not token:
        token = "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
        
    return {
        "recipient": req.get("payTo", ""),
        "amount_usd": raw / 1_000_000,
        "token_address": token,
        "description": req.get("description", ""),
        "network": req.get("network", ""),
    }
