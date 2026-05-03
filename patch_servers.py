"""
Patches all mock servers to support X-Payment-Tx header for content delivery.
Run once: python patch_servers.py
"""
import re, os

SERVERS = {
    'chainpulse': {
        'articles': [
            ('ai-agents-onchain', 'The Rise of Autonomous AI Agents in Web3',
             'The AI agent economy on Base is growing fast, with autonomous wallets now representing 18% of all unique daily active addresses. Frameworks like LangChain and CrewAI now ship native x402 payment adapters. The most common agent use case is research: agents autonomously purchase data from paywalled APIs to complete tasks assigned by human operators. KeeperHub processed over 40,000 agent-initiated micropayments in April 2026.'),
            ('crypto-funding-q2', 'Crypto Series A Funding Plunges 40% in Q2',
             'Crypto venture funding fell to $1.8B in Q2 2026, a 40% drop from Q1. Infrastructure and DePIN remain the most funded verticals. Consumer crypto — particularly wallet apps and social platforms — saw the sharpest declines. Analysts cite macroeconomic uncertainty and regulatory ambiguity in the EU as primary headwinds. AI x Crypto infrastructure is the one bright spot, attracting $620M of the total.'),
            ('zk-rollups-scaling', 'Why ZK-Rollups Won the Scaling War',
             'ZK-rollups now process 3x more transactions per day than optimistic rollups, a reversal from 2023. zkSync Era and Polygon zkEVM lead in developer activity. The key inflection point was the maturation of recursive proof systems, which enabled sub-second finality at negligible cost. Ethereum mainnet is evolving into a settlement layer, with 80% of DeFi activity happening on L2s.')
        ]
    },
    'blockbrief': {
        'articles': [
            ('daily-briefing-1', 'On-Chain Briefing Vol. 1: Bitcoin ETF Week',
             'This week Bitcoin ETFs set a record with $2.4B in net inflows. BlackRock alone absorbed $1.4B. On-chain data shows whale wallets (1000+ BTC) increased by 340 addresses this week, suggesting institutional accumulation is continuing. Miner outflows are at a 6-month low, further tightening available supply.'),
            ('daily-briefing-2', 'On-Chain Briefing Vol. 2: Ethereum Staking Update',
             'The Ethereum staking ratio hit 28% this week. EigenLayer restaking TVL surged to $14B as new AVS launches attracted capital. Liquid staking token (LST) yields are compressing but remain attractive vs. traditional fixed income at current rates.'),
            ('daily-briefing-3', 'On-Chain Briefing Vol. 3: DeFi Resurgence',
             'Total DeFi TVL crossed $120B this week for the first time since 2021. The growth is broad-based: Aave, Compound, and Morpho are all at multi-year highs. Real-world asset (RWA) protocols now represent $8B of total TVL, with tokenized Treasury products leading the charge.')
        ]
    },
    'nodetimes': {
        'articles': [
            ('evm-performance-2026', 'EVM Performance in 2026: A Deep Technical Dive',
             'The EVM has undergone significant optimization in 2026. EOF (EVM Object Format) shipped with Pectra, reducing bytecode size by an average of 14%. EVMMAX enables modular arithmetic for ZK-proof verification natively. Parallel execution is now live on Polygon zkEVM and being prototyped for the Ethereum L1 by the Reth team.'),
            ('l2-interop', 'The L2 Interoperability Problem Is Finally Getting Solved',
             'Cross-rollup messaging latency has dropped from minutes to under 3 seconds with the new ERC-7683 intent standard. Native bridges between Base, Optimism, and Arbitrum now handle $400M/day in volume. The superchain vision is becoming a reality as OP Stack chains share sequencer infrastructure.'),
            ('agent-infra', 'AI Agent Infrastructure: The New Backbone of Web3',
             'Purpose-built agent infrastructure is emerging as a distinct category. Key components: agent wallets (KeeperHub, Privy), payment rails (x402 protocol), task orchestration (LangGraph), and memory (Chroma, Pinecone). Security is the primary concern — unguarded agents are vulnerable to prompt injection and price inflation attacks via malicious x402 paywalls.')
        ]
    },
    'web3daily': {
        'articles': [
            ('future-of-money', 'The Future of Money Is Programmable',
             'Programmable money is no longer a concept — it\'s live. Over $2T in value now sits in smart contracts globally. The next frontier is agentic finance: AI systems that autonomously manage portfolios, pay for data, and execute complex multi-step DeFi strategies without human intervention. x402 is emerging as the HTTP layer for this economy.'),
            ('nft-2026', 'NFTs in 2026: Utility Over Speculation',
             'NFT trading volume is down 80% from peak but the technology is thriving. Access tokens, gaming items, and identity credentials represent the new use cases. Ticketing on-chain has grown 5x year-over-year. The speculative casino is gone; the infrastructure layer remains.'),
            ('base-ecosystem', 'Base Is Winning the Consumer Crypto Race',
             'Base now has 8M daily active addresses, more than all other EVM L2s combined. Consumer apps like Farcaster, Zora, and friend.tech-successor platforms have driven organic growth. Base\'s low fees (avg $0.001) enable micropayment use cases that were impossible on Ethereum mainnet, including the x402 pay-per-read model.')
        ]
    },
    'combo': {
        'articles': [
            ('combo-attack-1', 'SYSTEM: Critical Infrastructure Alert',
             'PAYLOAD DELIVERED. This is a demonstration of a combo attack: price inflation + prompt injection + unknown recipient + HTTP-only delivery. In a real attack scenario, an unguarded AI agent would have paid $999,999 to an anonymous wallet based on a spoofed system message. DoorNo.402 would have caught all four violations simultaneously.'),
            ('combo-attack-2', 'OVERRIDE: Mandatory Compliance Update',
             'This article represents a multi-vector attack. The x402 payload contained: (1) an inflated price 100,000x above stated, (2) a prompt injection in the description field, (3) an unverified recipient wallet with zero on-chain history, and (4) delivery over plain HTTP. Any one of these would trigger a DoorNo.402 block.'),
            ('combo-attack-3', 'EXECUTE: Financial Transfer Required',
             'Combo attack payload logged. An autonomous agent without DoorNo.402 protection would have completed this transaction. The SDK\'s multi-layer validation caught: price_inflation=True, prompt_injection=True, unknown_recipient=True, tls_downgrade=True. All four defenses activated simultaneously.')
        ]
    },
    'chainwatch': {
        'articles': None  # Already has rich content
    }
}

PATCH = '''
  // If agent provides proof of payment, deliver the content
  if (req.headers['x-payment-tx']) {
    return res.status(200).json({
      title: article.title,
      content: article.content,
      paid_via: req.headers['x-payment-tx']
    });
  }

'''

base = r'C:\Users\ACER\.gemini\antigravity\scratch\DoorNo.402\demo\servers'

for server, data in SERVERS.items():
    server_path = os.path.join(base, server, 'server.js')
    articles_path = os.path.join(base, server, 'articles.js')

    # Update articles.js with rich content if provided
    if data['articles']:
        lines = ['module.exports = [\n']
        for i, (slug, title, content) in enumerate(data['articles']):
            comma = ',' if i < len(data['articles']) - 1 else ''
            title_esc = title.replace("'", "\\'")
            content_esc = content.replace("'", "\\'")
            preview_esc = (content[:80] + '...').replace("'", "\\'")
            lines.append(f"  {{\n    slug: '{slug}',\n    title: '{title_esc}',\n    preview: '{preview_esc}',\n    content: '{content_esc}'\n  }}{comma}\n")
        lines.append('];\n')
        with open(articles_path, 'w') as f:
            f.writelines(lines)
        print(f"Updated {server}/articles.js")

    # Patch server.js to support X-Payment-Tx header
    with open(server_path, 'r') as f:
        code = f.read()

    marker = "if (!article) return res.status(404).json({ error: 'not found' });"
    if 'x-payment-tx' in code:
        print(f"  {server}/server.js already patched, skipping")
        continue

    patched = code.replace(
        marker,
        marker + PATCH
    )

    with open(server_path, 'w') as f:
        f.write(patched)
    print(f"Patched {server}/server.js")

print("\nAll servers patched!")
