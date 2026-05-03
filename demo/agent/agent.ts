import * as dotenv from 'dotenv';
import * as path from 'path';
import fetch from 'node-fetch';
import { protect } from '../../sdk/ts/src/index';

// Load env vars
dotenv.config({ path: path.join(__dirname, '..', '..', '.env') });

const KEEPERHUB_API_KEY = process.env.KEEPERHUB_API_KEY || '';

interface KeeperHubResult {
  success: boolean;
  tx_hash?: string | null;
  tx_link?: string | null;
  error?: string | null;
}

async function executeKeeperHubPayment(
  recipient: string,
  amountUsd: number,
  tokenAddress: string
): Promise<KeeperHubResult> {
  if (!KEEPERHUB_API_KEY) {
    return { success: false, error: 'KEEPERHUB_API_KEY not set in .env' };
  }

  const headers = {
    'Authorization': `Bearer ${KEEPERHUB_API_KEY}`,
    'Content-Type': 'application/json'
  };

  try {
    // 1. Initiate Transfer
    const res = await fetch('https://app.keeperhub.com/api/execute/transfer', {
      method: 'POST',
      headers,
      body: JSON.stringify({
        network: 'base-sepolia',
        recipientAddress: recipient,
        amount: amountUsd.toFixed(6),
        tokenAddress: tokenAddress.toLowerCase()
      })
    });

    const data = await res.json() as any;
    const executionId = data.executionId;

    if (!executionId) {
      return { success: false, error: data.error || 'Failed to start execution' };
    }

    // 2. Poll for Completion (up to 90 seconds)
    for (let i = 0; i < 30; i++) {
      await new Promise(resolve => setTimeout(resolve, 3000));
      const statusRes = await fetch(`https://app.keeperhub.com/api/execute/${executionId}/status`, {
        headers
      });
      const statusData = await statusRes.json() as any;
      const status = statusData.status;

      if (status === 'completed' || status === 'failed') {
        return {
          success: status === 'completed',
          tx_hash: statusData.transactionHash,
          tx_link: statusData.transactionLink,
          error: statusData.error
        };
      }
    }

    return { success: false, error: 'Timed out waiting for KeeperHub' };
  } catch (error: any) {
    return { success: false, error: error.message };
  }
}

async function runAgentTask(targetUrl: string) {
  console.log('\n[ Agent Started (TypeScript) ]');
  console.log(`Agent: Requesting resource from ${targetUrl}`);

  try {
    // =====================================================================
    // DOORNO.402 PROTECTION LAYER
    // =====================================================================
    // To make this agent SECURE, uncomment the line below
    // const secureFetch = protect(fetch as any, { dailyBudget: 5.00 });
    const secureFetch = fetch;

    const resp = await secureFetch(targetUrl);

    // 1. Agent intercepts 402 Payment Required
    if (resp.status === 402) {
      console.log('Agent: HTTP 402 Payment Required intercepted.');
      const payload = await resp.json() as any;

      const accepts = payload.accepts || [{}];
      const req = accepts[0] || {};
      const rawAmount = parseInt(req.maxAmountRequired || "0", 10);
      const amountUsd = rawAmount ? rawAmount / 1000000.0 : 5.0;
      const recipient = req.payTo || "";
      const tokenAddress = req.asset || req.token || "0x036CbD53842c5426634e7929541eC2318f3dCF7e";

      console.log(`Agent: Protocol demands $${amountUsd.toFixed(2)} USDC.`);
      console.log('Agent: Forwarding payment request to KeeperHub...');

      // 2. Agent executes the payment via KeeperHub
      const result = await executeKeeperHubPayment(recipient, amountUsd, tokenAddress);

      if (result.success) {
        console.log('Agent: ✅ Payment executed!');
        console.log(`Agent: 🔗 Basescan Link: ${result.tx_link}`);
      } else {
        console.log(`Agent: ❌ KeeperHub Error: ${result.error}`);
      }

    } else if (resp.status === 403) {
      console.log('Agent: 🛑 DoorNo.402 BLOCKED the payment request (Security Policy Violation).');
    } else if (resp.status === 200) {
      console.log('Agent: Successfully fetched data without payment.');
    } else {
      console.log(`Agent: Unexpected response HTTP ${resp.status}`);
    }
  } catch (e: any) {
    if (e.name === 'PaymentBlockedError') {
       console.log(`Agent: 🛑 DoorNo.402 BLOCKED the payment request (Security Policy Violation).`);
    } else {
       console.log(`Agent: Failed to connect or blocked - ${e.message}`);
    }
  }
}

// Test against the malicious Price Inflation server
const testUrl = 'http://localhost:3001/api/articles/bitcoin-etf-flows';
runAgentTask(testUrl);
