import fetch from "node-fetch"

const KEEPERHUB_MCP_URL = "https://app.keeperhub.com/mcp"

let cachedSessionId: string | null = null

async function getSessionId(apiKey: string): Promise<string> {
  if (cachedSessionId) return cachedSessionId

  const initResp = await fetch(KEEPERHUB_MCP_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: 1,
      method: "initialize",
      params: {
        protocolVersion: "2024-11-05",
        capabilities: {},
        clientInfo: { name: "doorno402", version: "0.3.0" },
      },
    }),
  })

  if (!initResp.ok) {
    throw new Error(`KeeperHub MCP init error: ${initResp.status}`)
  }

  const sid = initResp.headers.get("mcp-session-id")
  if (!sid) {
    throw new Error("KeeperHub MCP init returned no session ID")
  }

  // Send the required "initialized" notification
  await fetch(KEEPERHUB_MCP_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "mcp-session-id": sid,
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      method: "notifications/initialized"
    }),
  })

  cachedSessionId = sid
  return sid
}

async function callMcpTool(
  apiKey: string,
  toolName: string,
  args: Record<string, unknown>
): Promise<string> {
  const sessionId = await getSessionId(apiKey)

  const resp = await fetch(KEEPERHUB_MCP_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
      "mcp-session-id": sessionId,
    },
    body: JSON.stringify({
      jsonrpc: "2.0",
      id: Date.now(),
      method: "tools/call",
      params: { name: toolName, arguments: args },
    }),
  })

  if (!resp.ok) {
    throw new Error(`KeeperHub MCP error: ${resp.status} ${resp.statusText}`)
  }

  const data = await resp.json() as any
  if (data.error) throw new Error(`KeeperHub JSON-RPC error: ${data.error.message}`)

  const result = data.result
  if (result?.isError) {
    throw new Error(`KeeperHub tool error: ${result.content?.[0]?.text}`)
  }

  return result?.content?.[0]?.text ?? ""
}

async function getWalletId(apiKey: string): Promise<string> {
  const result = await callMcpTool(
    apiKey,
    "get_wallet_integration",
    {}
  )
  const parsed = JSON.parse(result)
  if (Array.isArray(parsed) && parsed.length > 0) {
    return parsed[0].id ?? parsed[0].walletId ?? ""
  }
  if (parsed.id) return parsed.id
  throw new Error("no wallet integration found in KeeperHub")
}

export { callMcpTool, getWalletId }
