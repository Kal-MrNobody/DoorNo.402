# Hackathon Demo Report: DoorNo.402 x KeeperHub

This report summarizes the final, production-ready integration between the DoorNo.402 Security SDK and the KeeperHub execution layer that we completed today. Use this as your script and guide when presenting your project to the hackathon judges.

---

## 1. What We Accomplished Today

Today we finalized the entire demo suite and the SDK developer experience.

### 🔌 2-Line Developer Integration
We completely refactored the SDK so that developers don't have to write custom exception handling. Securing an AI agent's HTTP client is now as simple as wrapping it with `protect()`:
```python
from doorno402 import protect
client = protect(client, daily_budget=5.00)
```

### 🖥️ The Interactive CLI Dashboard
We built a beautiful, interactive CLI (`python demo/cli/run.py`) that acts as the centerpiece for the demo. It allows you to:
- See your **live KeeperHub Wallet balance** right at the top.
- Choose between 6 distinct vulnerability scenarios.
- Run side-by-side comparisons of a **SECURE** agent vs an **UNSECURE** agent.

### ⛓️ Real On-Chain KeeperHub Execution
We removed all fake simulations! The CLI now directly interfaces with the KeeperHub Direct Execution API (`/api/execute/transfer`). If an agent falls for an attack in the CLI, it initiates a real, on-chain transaction on the Base Sepolia testnet and prints the real Basescan link without truncating it.

---

## 2. How to Test It (The Demo Flow)

To show the judges how the system works, you will spin up local mock servers that simulate malicious AI tool endpoints, and then attack your agent with them.

### Step A: Start a Malicious Server
We built 6 different servers, each simulating a different attack vector (Price Inflation, Prompt Injection, Budget Drain, etc.).
1. Open a terminal in the root `DoorNo.402` folder.
2. Start one of the servers (e.g., Server 1):
   ```bash
   node demo/servers/cryptoinsider/server.js
   ```
   *(Leave this running in the background).*

### Step B: Run the CLI
1. Open a **second** terminal in the root `DoorNo.402` folder.
2. Run the interactive CLI:
   ```bash
   python demo/cli/run.py
   ```
3. Select Option `2` (Run Agent - Secure vs Unsecure).
4. Select the server you just started (e.g., Option `1` for CryptoInsider).
5. Select Option `3` to run a side-by-side comparison.

**What you will see:**
- The **UNSECURE** agent will blindly forward the malicious `$5.00` payload to KeeperHub. KeeperHub will execute it on-chain, and the CLI will print the Basescan link proving the agent was robbed.
- The **SECURE** agent (running the DoorNo.402 wrapper) will intercept the payload, instantly detect the anomaly, and completely block the transaction before KeeperHub is ever called.

---

## 3. ⚠️ Critical Gotchas to Keep in Mind

When doing live demos, there are three common pitfalls you must watch out for:

> **1. Testnet Gas Fees (ETH)**
> Even if your KeeperHub wallet has `24.00 USDC`, KeeperHub will **fail** to execute transactions if your wallet has `0 ETH`. Because KeeperHub executes on the real Base Sepolia network, your wallet must have a tiny fraction of ETH to pay the blockchain gas fees for the USDC transfer. 
> * **Fix:** Always ensure you have pinged a testnet faucet for ETH before a presentation.

> **2. Faucet Delays**
> When you request testnet funds from a faucet like Coinbase Developer Platform, it takes **1 to 3 minutes** for the funds to actually confirm on the blockchain.
> * **Fix:** If you just used a faucet, wait a few minutes before running the CLI, otherwise KeeperHub will throw a `failed` or `No token selected` error.

> **3. Terminal Navigation Errors**
> If you get a `Cannot find module` error when trying to start a server (e.g., `node demo/servers/chainpulse/server.js`), it means your terminal is already inside a sub-folder.
> * **Fix:** Always make sure your terminal is at the exact root `DoorNo.402/` directory before running any `node` or `python` commands. Use `cd ../../..` to back out if you get stuck.
