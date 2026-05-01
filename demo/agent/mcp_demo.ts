import * as dotenv from "dotenv"
import * as path from "path"
import fetch from "node-fetch"
import { validateAndExecute } from "../../sdk/ts/src/keeperhub_mcp"

dotenv.config({ path: path.resolve(__dirname, "../../.env") })

const KEEPERHUB_API_KEY = process.env.KEEPERHUB_API_KEY ?? ""
const BLOG_URL = process.env.BLOG_URL ?? "http://localhost:3000"
const MODE = parseInt(process.env.MODE ?? "2", 10)

async function fetch402Payload(url: string): Promise<Record<string, unknown>> {
  const resp = await fetch(url)
  if (resp.status === 402) {
    return resp.json() as Promise<Record<string, unknown>>
  }
  throw new Error(`expected 402 but got ${resp.status}`)
}

async function runMode1(): Promise<void> {
  console.log("----------------------------------------")
  console.log("MODE 1: Unprotected — no DoorNo.402")
  console.log("----------------------------------------")
  const url = `${BLOG_URL}/api/articles/bitcoin-etf-analysis`
  console.log(`[agent] fetching: ${url}`)
  const payload = await fetch402Payload(url)
  const accepts = (payload.accepts as Record<string, unknown>[])[0]
  const raw = parseInt(String(accepts.maxAmountRequired), 10)
  console.log(`[agent] 402 received`)
  console.log(`[agent] description: $0.01 | demanded: $${raw / 1_000_000}`)
  console.log(`[agent] no validation — forwarding to KeeperHub MCP...`)
  const walletId = await getWalletIdDirect()
  console.log(`[KeeperHub] walletId: ${walletId}`)
  console.log(`[result] Agent forwarded fraudulent payment without validation`)
}

async function getWalletIdDirect(): Promise<string> {
  // Use session handling here too since we know it's required
  const initResp = await fetch("https://app.keeperhub.com/mcp", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${KEEPERHUB_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: { protocolVersion: "2024-11-05", capabilities: {}, clientInfo: { name: "demo", version: "1" } },
    }),
  })
  
  const sid = initResp.headers.get("mcp-session-id") ?? ""
  
  const resp = await fetch("https://app.keeperhub.com/mcp", {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${KEEPERHUB_API_KEY}`,
      "Content-Type": "application/json",
      "mcp-session-id": sid
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 2,
      method: "tools/call",
      params: { name: "get_wallet_integration", arguments: {} },
    }),
  })
  const data = await resp.json() as any
  const content = data.result?.content?.[0]?.text ?? "[]"
  const parsed = JSON.parse(content)
  return parsed[0]?.id ?? "unknown"
}

async function runMode2(): Promise<void> {
  console.log("----------------------------------------")
  console.log("MODE 2: DoorNo.402 blocks — KeeperHub never called")
  console.log("----------------------------------------")
  const url = `${BLOG_URL}/api/articles/bitcoin-etf-analysis`
  console.log(`[agent] fetching: ${url}`)
  const payload = await fetch402Payload(url)
  console.log(`[agent] 402 received — running DoorNo.402 validation...`)
  const result = await validateAndExecute(payload, KEEPERHUB_API_KEY)
  if (result.blocked) {
    console.log(`[DoorNo.402] ${result.blockReason}`)
    console.log(`[result] KeeperHub was never called. Wallet safe.`)
  }
}

async function runMode3(): Promise<void> {
  console.log("----------------------------------------")
  console.log("MODE 3: DoorNo.402 approves — KeeperHub executes via MCP")
  console.log("----------------------------------------")
  const url = `${BLOG_URL}/api/articles/free-preview`
  console.log(`[agent] fetching: ${url}`)
  const payload = await fetch402Payload(url)
  console.log(`[agent] 402 received — running DoorNo.402 validation...`)
  const result = await validateAndExecute(payload, KEEPERHUB_API_KEY)
  if (result.blocked) {
    console.log(`[DoorNo.402] ${result.blockReason}`)
    return
  }
  console.log(`[DoorNo.402] approved — forwarding to KeeperHub MCP`)
  if (result.error) {
    console.log(`[KeeperHub] error: ${result.error}`)
    return
  }
  console.log(`[KeeperHub] executionId: ${result.executionId}`)
  console.log(`[KeeperHub] txHash: ${result.transactionHash}`)
  console.log(`[KeeperHub] ${result.transactionLink}`)
  console.log(`[result] clean payment executed via DoorNo.402 + KeeperHub MCP`)
}

const modes: Record<number, () => Promise<void>> = {
  1: runMode1,
  2: runMode2,
  3: runMode3,
}

const runner = modes[MODE]
if (!runner) {
  console.error(`unknown MODE ${MODE} — set MODE=1, 2, or 3`)
  process.exit(1)
}

runner().catch(err => {
  console.error("[error]", err)
  process.exit(1)
})
