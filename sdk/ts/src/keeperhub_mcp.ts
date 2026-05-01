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
