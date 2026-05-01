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

async function createTransferWorkflow(
  apiKey: string,
  walletId: string,
  recipient: string,
  amount: string,
  tokenAddress: string
): Promise<string> {
  const prompt = (
    `Transfer ${amount} USDC token at ${tokenAddress} ` +
    `to ${recipient} on base-sepolia ` +
    `using wallet ${walletId}`
  )
  const result = await callMcpTool(
    apiKey,
    "ai_generate_workflow",
    { prompt, walletId }
  )
  const parsed = JSON.parse(result)
  return parsed.id ?? parsed.workflowId ?? ""
}

async function executeWorkflow(
  apiKey: string,
  workflowId: string
): Promise<string> {
  const result = await callMcpTool(
    apiKey,
    "execute_workflow",
    { workflowId }
  )
  const parsed = JSON.parse(result)
  return parsed.executionId ?? parsed.id ?? ""
}

interface ExecutionResult {
  status: string
  transactionHash?: string
  transactionLink?: string
  error?: string
}

async function pollExecutionStatus(
  apiKey: string,
  executionId: string,
  maxAttempts = 12,
  intervalMs = 5000
): Promise<ExecutionResult> {
  for (let i = 0; i < maxAttempts; i++) {
    const result = await callMcpTool(
      apiKey,
      "get_execution_status",
      { executionId }
    )
    const parsed = JSON.parse(result) as ExecutionResult
    if (parsed.status === "completed" || parsed.status === "failed") {
      return parsed
    }
    await new Promise(r => setTimeout(r, intervalMs))
  }
  return { status: "timeout", error: "execution did not complete in time" }
}

export interface McpExecutionResult {
  approved: boolean
  blocked: boolean
  blockReason?: string
  executionId?: string
  transactionHash?: string
  transactionLink?: string
  error?: string
}

export async function validateAndExecute(
  paymentDetails: Record<string, unknown>,
  apiKey: string,
  options?: {
    dailyBudget?: number
    mainnetRpcUrl?: string
  }
): Promise<McpExecutionResult> {
  // Import DoorNo.402 validators inline
  const { validatePrice } = await import("./validators/price")
  const { validateInjection } = await import("./validators/injection")
  const { validateTls } = await import("./validators/tls")

  const accepts = (
    paymentDetails.accepts as Record<string, unknown>[]
  ) ?? []
  const req = accepts[0] ?? {}
  const url = String(req.resource ?? "")

  // TLS check
  const tlsResult = validateTls(url)
  if (!tlsResult.valid) {
    return { approved: false, blocked: true, blockReason: tlsResult.reason }
  }

  // Injection check
  const injectionResult = validateInjection(paymentDetails)
  if (injectionResult.injectionDetected) {
    return {
      approved: false,
      blocked: true,
      blockReason: injectionResult.reason,
    }
  }

  // Price check
  const priceResult = validatePrice(paymentDetails)
  if (!priceResult.valid) {
    return { approved: false, blocked: true, blockReason: priceResult.reason }
  }

  // All checks passed — execute via KeeperHub MCP
  try {
    const walletId = await getWalletId(apiKey)
    const raw = parseInt(String(req.maxAmountRequired ?? "0"), 10)
    const amount = (raw / 1_000_000).toFixed(6)
    const workflowId = await createTransferWorkflow(
      apiKey,
      walletId,
      String(req.payTo ?? ""),
      amount,
      String(req.asset ?? "")
    )
    const executionId = await executeWorkflow(apiKey, workflowId)
    const status = await pollExecutionStatus(apiKey, executionId)
    return {
      approved: true,
      blocked: false,
      executionId,
      transactionHash: status.transactionHash,
      transactionLink: status.transactionLink,
      error: status.error,
    }
  } catch (err) {
    return {
      approved: true,
      blocked: false,
      error: String(err),
    }
  }
}
