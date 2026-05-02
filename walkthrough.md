# Hackathon Demo Report: DoorNo.402 x KeeperHub

This report summarizes the complete integration between the DoorNo.402 Security SDK and the KeeperHub execution layer. Use this as your script and guide when presenting your project to the hackathon judges.

---

## 1. The Architecture (Before & After)

### The Problem (Before DoorNo.402)
KeeperHub is an incredibly powerful on-chain execution layer that abstracts away gas and private key management for AI agents. However, execution layers execute whatever they are told. 

If an AI agent visits a malicious website requesting a fraudulent x402 payment (e.g., claiming a premium article costs `$0.01` in the description, but demanding `$5.00` in the protocol), the agent will unknowingly forward the malicious `$5.00` payload to KeeperHub. **KeeperHub will blindly execute the transaction, and the wallet is drained.**

### The Solution (After DoorNo.402)
DoorNo.402 acts as a **Security Middleware** sitting *between* the AI agent and the KeeperHub execution layer. 

When the agent encounters an x402 payment, DoorNo.402 intercepts it and runs 7 strict security checks (Price Inflation, Prompt Injection, ENS Verification, Budget Limits, TLS, Redirect Hijacks, Delivery Verification). 
* **If it's malicious:** DoorNo.402 blocks it entirely (`PaymentBlockedError`). KeeperHub is never called.
* **If it's honest:** DoorNo.402 approves the payment details and safely forwards them to KeeperHub for execution.

---

## 2. How to Perform the Demo

Follow these exact steps to demonstrate the full power of your project to the judges.

### Step A: Start the Malicious Server
First, spin up your backend server that hosts both the malicious endpoints and the honest endpoint.
Open a terminal in the root `DoorNo.402` directory and run:
```bash
node demo/blog/backend/server.js
```
*(Leave this running in the background).*

### Step B: The Three Demo Scenarios

In your second terminal (also in the root `DoorNo.402` directory), you will run the agent script `demo/agent/keeperhub_demo.py`. You will change the `MODE` variable at the top of that file to show the three different scenarios.

#### Scenario 1: The Exploit (Unprotected)
**Goal:** Show the judges how easily an agent gets robbed without DoorNo.402.
1. Open `demo/agent/keeperhub_demo.py` and set `MODE = 1`.
2. Run the script: `python demo/agent/keeperhub_demo.py`
3. **What happens:** The agent hits the malicious `/api/articles/bitcoin-etf-analysis` endpoint. Because DoorNo.402 is OFF, the agent blindly forwards the $5.00 fraudulent demand to KeeperHub. 
4. **Result:** KeeperHub executes the $5.00 transaction on Base Sepolia. The agent is robbed. Show the judges the Basescan transaction link printed in the terminal.

#### Scenario 2: The Block (Protected)
**Goal:** Show DoorNo.402 catching the exact same exploit.
1. Open `demo/agent/keeperhub_demo.py` and set `MODE = 2`.
2. Run the script: `python demo/agent/keeperhub_demo.py`
3. **What happens:** The agent hits the exact same malicious endpoint. This time, DoorNo.402 is ON. The SDK intercepts the payload, detects the security violations (TLS, Price Inflation, etc.), and immediately throws a `PaymentBlockedError`.
4. **Result:** KeeperHub is never called. The $5.00 is saved. The terminal will clearly print: `[result] KeeperHub was never called. Wallet safe.`

#### Scenario 3: The Happy Path (Protected + Executed)
**Goal:** Show DoorNo.402 and KeeperHub working together perfectly on a legitimate transaction.
1. Open `demo/agent/keeperhub_demo.py` and set `MODE = 3`.
2. Run the script: `python demo/agent/keeperhub_demo.py`
3. **What happens:** The agent hits the honest `/api/articles/free-preview` endpoint. DoorNo.402 intercepts it, verifies that the description (`$0.01`) perfectly matches the demanded protocol amount (`$0.01`), and validates the endpoint.
4. **Result:** DoorNo.402 approves the payload and forwards the `$0.01` transaction to KeeperHub. KeeperHub successfully executes the transfer on Base Sepolia. Show the judges the final Basescan link for the successful `$0.01` transfer.

---

> [!TIP]
> **Pro-Tip for the pitch:** Have the KeeperHub dashboard open during the demo. When you run Mode 1, show them the $5.00 transaction appearing. When you run Mode 2, show them that *nothing* hits the dashboard. When you run Mode 3, show them the clean $0.01 transaction. This visually proves that DoorNo.402 is acting as a perfect gatekeeper!
