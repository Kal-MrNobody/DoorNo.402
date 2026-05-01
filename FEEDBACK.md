# FEEDBACK.md

## What we built

DoorNo.402 is a security middleware SDK for autonomous AI agents that make x402 payments. It intercepts HTTP 402 responses before the agent processes them, running validation checks for price inflation, ENS trust scoring, prompt injection, budget limits, TLS enforcement, redirect hijacking, and delivery verification. It integrates with KeeperHub MCP via the interceptAndForward pattern -- DoorNo.402 validates, KeeperHub executes.

## What worked

- MCP server concept is clean and easy to reason about
- The execute() interface is simple to wrap
- Documentation was clear enough to understand the integration pattern
- SSE transport worked reliably once configured

## Pain points

- No official TypeScript types exported from KeeperHub MCP package which made building typed wrappers harder
- MCP endpoint URL was not immediately obvious from the dashboard, had to find it in docs
- Would benefit from a sandbox/test mode that does not execute real transactions so integration can be tested without funds

## Bugs

None confirmed. The SSE endpoint occasionally timed out during testing on localhost which made debugging harder. Could not determine if this was a network issue or server-side.

## Feature requests

- Dry run mode for testing integrations without executing payments
- Webhook support for payment confirmation events so SDK can implement delivery verification natively
- TypeScript SDK with exported types for the MCP request/response shapes
- A validation hook in the MCP pipeline so middleware like DoorNo.402 can register officially rather than wrapping the client externally

## Overall

KeeperHub solves a real problem. The execution reliability layer is exactly what autonomous agents need. The gap is that security validation happens outside KeeperHub -- DoorNo.402 fills that gap. A first-party validation hook in the MCP server would make this integration significantly tighter.
