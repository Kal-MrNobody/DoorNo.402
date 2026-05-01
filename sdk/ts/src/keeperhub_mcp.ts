import fetch from "node-fetch"

const KEEPERHUB_MCP_URL = "https://app.keeperhub.com/mcp"

async function callMcpTool(
  apiKey: string,
  toolName: string,
  args: Record<string, unknown>
): Promise<string> {
  const resp = await fetch(KEEPERHUB_MCP_URL, {
    method: "POST",
    headers: {
      "Authorization": `Bearer ${apiKey}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      method: "tools/call",
      params: { name: toolName, arguments: args },
    }),
  })
  if (!resp.ok) {
    throw new Error(`KeeperHub MCP error: ${resp.status} ${resp.statusText}`)
  }
  const data = await resp.json() as {
    content: Array<{ type: string; text: string }>
    isError: boolean
  }
  if (data.isError) {
    throw new Error(`KeeperHub tool error: ${data.content[0]?.text}`)
  }
  return data.content[0]?.text ?? ""
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

export { getWalletId }
