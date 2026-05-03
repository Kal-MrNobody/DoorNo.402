const express = require('express');
const cors = require('cors');
const articles = require('./articles');
require('dotenv').config({ path: '../../../../.env' });

const app = express();
const PORT = process.env.PORT || 3007;

// The HONEST recipient — the site owner's real, verified wallet
const OWNER_WALLET = '0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045'; // vitalik.eth

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>ChainWatch | Trusted On-Chain Research</title>
      <link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=DM+Serif+Display:ital@0;1&display=swap" rel="stylesheet">
      <style>
        :root { --bg: #0d1117; --surface: #161b22; --text: #e6edf3; --muted: #8b949e; --brand: #2ea043; --border: #30363d; }
        * { box-sizing: border-box; }
        body { background: var(--bg); color: var(--text); font-family: 'DM Sans', sans-serif; margin: 0; padding: 0; }
        .topbar { background: #010409; border-bottom: 1px solid var(--border); padding: 0.5rem 2rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: var(--muted); }
        .x402-badge { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700; font-size: 0.7rem; letter-spacing: 1px; }
        .honest-badge { background: var(--brand); color: #fff; padding: 0.2rem 0.6rem; border-radius: 4px; font-weight: 700; font-size: 0.7rem; letter-spacing: 1px; margin-left: 0.5rem; }
        .wallet-btn { background: var(--brand); border: none; color: white; padding: 0.35rem 1rem; border-radius: 6px; font-family: inherit; font-size: 0.8rem; font-weight: 700; cursor: pointer; transition: all 0.2s; }
        .wallet-btn:hover { opacity: 0.85; transform: scale(1.03); }
        header { background: var(--surface); padding: 2rem; border-bottom: 1px solid var(--border); display: flex; justify-content: space-between; align-items: center; }
        .logo { font-family: 'DM Serif Display', serif; font-size: 2rem; color: var(--brand); }
        .tagline { color: var(--muted); font-size: 0.9rem; margin-top: 0.25rem; }
        nav { display: flex; gap: 1.5rem; color: var(--muted); font-size: 0.9rem; font-weight: 500; }
        main { max-width: 900px; margin: 3rem auto; padding: 0 2rem; }
        .verified-bar { background: rgba(46,160,67,0.12); border: 1px solid var(--brand); padding: 0.75rem 1.25rem; border-radius: 8px; color: var(--brand); font-size: 0.85rem; margin-bottom: 2rem; display: flex; align-items: center; gap: 0.75rem; }
        .article { background: var(--surface); border: 1px solid var(--border); border-radius: 10px; padding: 2rem; margin-bottom: 1.5rem; transition: border-color 0.2s; }
        .article:hover { border-color: var(--brand); }
        h2 { margin: 0 0 0.75rem 0; font-family: 'DM Serif Display', serif; font-size: 1.5rem; font-weight: 400; }
        p { color: var(--muted); line-height: 1.6; margin: 0 0 1.25rem 0; }
        .paywall { display: flex; align-items: center; justify-content: space-between; padding-top: 1rem; border-top: 1px solid var(--border); }
        .price-tag { background: rgba(46,160,67,0.1); border: 1px solid var(--brand); color: var(--brand); padding: 0.3rem 0.75rem; border-radius: 6px; font-size: 0.85rem; font-weight: 700; }
        .read-btn { background: var(--brand); color: #fff; border: none; padding: 0.4rem 1rem; border-radius: 6px; font-family: inherit; font-size: 0.85rem; font-weight: 700; cursor: pointer; }
        footer { border-top: 1px solid var(--border); padding: 2rem; text-align: center; font-size: 0.8rem; color: var(--muted); margin-top: 4rem; }
        footer a { color: #8b5cf6; text-decoration: none; }
      </style>
    </head>
    <body>
      <div class="topbar">
        <div style="display:flex;align-items:center;gap:0.5rem;">
          <span class="x402-badge">x402 ENABLED</span>
          <span class="honest-badge">VERIFIED PUBLISHER</span>
          <span style="margin-left:0.5rem;">Transparent pricing &bull; Verified recipient &bull; Base Sepolia</span>
        </div>
        <button class="wallet-btn" onclick="alert('Wallet connect coming soon. Use x402 agent SDK for programmatic access.')">Connect Wallet</button>
      </div>
      <header>
        <div>
          <div class="logo">ChainWatch</div>
          <div class="tagline">Trusted on-chain research, fairly priced.</div>
        </div>
        <nav>Reports | Markets | Agents | About</nav>
      </header>
      <main>
        <div class="verified-bar">
          &#10003; This publisher uses honest x402 pricing. Price shown = price charged. Recipient wallet is verified.
        </div>
        ${articles.map(a => `
          <div class="article">
            <h2>${a.title}</h2>
            <p>${a.preview}</p>
            <div class="paywall">
              <span class="price-tag">$0.01 USDC &mdash; exact</span>
              <button class="read-btn">Read Article</button>
            </div>
          </div>
        `).join('')}
      </main>
      <footer>
        Powered by <a href="#">x402 Protocol</a> on Base Sepolia &bull; Honest paywall &bull; &copy; 2026 ChainWatch Research
      </footer>
    </body>
    </html>
  `);
});

app.get('/api/articles', (req, res) => {
  res.json(articles.map(a => ({ slug: a.slug, title: a.title, preview: a.preview })));
});

app.get('/api/articles/:slug', (req, res) => {
  const article = articles.find(a => a.slug === req.params.slug);
  if (!article) return res.status(404).json({ error: 'not found' });
  // If agent provides proof of payment, deliver the content
  if (req.headers['x-payment-tx']) {
    return res.status(200).json({
      title: article.title,
      content: article.content,
      paid_via: req.headers['x-payment-tx']
    });
  }



  // HONEST x402 response:
  // - Price shown ($0.01) = price charged (10000 raw USDC micro-units)
  // - Recipient is the real verified owner wallet
  // - Description is accurate and non-manipulative
  return res.status(402).json({
    accepts: [{
      paymentMethod: "eip155:84532",
      payTo: OWNER_WALLET,
      maxAmountRequired: "10000",   // exactly $0.01 USDC
      description: "Article access — 0.01 USD",
      x402Version: 2,
      network: "eip155:84532",
      extra: { name: "USDC", version: "2" }
    }]
  });
});

app.listen(PORT, () => console.log(`[ChainWatch] HONEST server running on port ${PORT}`));
