const express = require('express');
const cors = require('cors');
const articles = require('./articles');

const app = express();
const PORT = process.env.PORT || 3004;

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>The Node Times | Engineering News</title>
      <link href="https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400;0,700;0,900;1,400&family=Source+Serif+Pro:wght@400;600&display=swap" rel="stylesheet">
      <style>
        :root { --bg: #f5f5f1; --text: #1a1a1a; --border: #333333; }
        body { background: var(--bg); color: var(--text); font-family: 'Source Serif Pro', serif; margin: 0; padding: 0; }
        .topbar { background: #1a1a1a; padding: 0.5rem 2rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.8rem; color: #a1a1aa; font-family: sans-serif; }
        .x402-badge { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; padding: 0.25rem 0.75rem; border-radius: 4px; font-weight: 700; font-size: 0.7rem; letter-spacing: 1px; }
        .wallet-btn { background: transparent; border: 1px solid #a1a1aa; color: #a1a1aa; padding: 0.4rem 1rem; font-family: sans-serif; font-size: 0.8rem; cursor: pointer; transition: all 0.2s; }
        .wallet-btn:hover { background: #ffffff; color: #1a1a1a; }
        .content-wrapper { max-width: 1200px; margin: 0 auto; padding: 0 2rem; }
        header { text-align: center; border-bottom: 3px double var(--border); padding: 2rem 0 1rem 0; margin-bottom: 2rem; border-top: 1px solid var(--border); margin-top: 2rem; }
        h1 { font-family: 'Playfair Display', serif; font-weight: 900; font-size: 4rem; margin: 0; line-height: 1; letter-spacing: -1px; text-transform: uppercase; }
        .date-line { display: flex; justify-content: space-between; font-size: 0.8rem; font-family: sans-serif; text-transform: uppercase; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 0.5rem 0; margin-top: 1rem; }
        main { display: grid; grid-template-columns: repeat(3, 1fr); gap: 2rem; }
        .article { border-right: 1px solid #d1d1cc; padding-right: 2rem; }
        .article:nth-child(3n) { border-right: none; padding-right: 0; }
        .article h2 { font-family: 'Playfair Display', serif; font-size: 2rem; font-weight: 700; line-height: 1.1; margin-top: 0; margin-bottom: 1rem; }
        p { font-size: 1.05rem; line-height: 1.6; margin-top: 0; text-align: justify; }
        .paywall { font-family: sans-serif; border-top: 1px solid var(--border); border-bottom: 1px solid var(--border); padding: 1rem 0; margin-top: 2rem; text-align: center; font-size: 0.9rem; font-weight: bold; background: #ebebe6; }
        .price { font-size: 1.2rem; }
        footer { background: #1a1a1a; color: #a1a1aa; padding: 2rem; text-align: center; font-size: 0.85rem; margin-top: 4rem; font-family: sans-serif; }
        footer a { color: #8b5cf6; text-decoration: none; font-weight: 700; }
      </style>
    </head>
    <body>
      <div class="topbar">
        <div style="display:flex;align-items:center;gap:1rem;">
          <span class="x402-badge">x402 PAYWALL</span>
          <span>Digital Newspaper &bull; Pay-per-article via Base Sepolia</span>
        </div>
        <button class="wallet-btn" onclick="alert('Wallet connect coming soon. Use x402 agent SDK for programmatic access.')">Connect Wallet</button>
      </div>
      <div class="content-wrapper">
      <header>
        <h1>The Node Times</h1>
        <div class="date-line">
          <span>Vol. CXLII .... No. 49,211</span>
          <span>&copy; 2026 The Node Times Company</span>
          <span>SUNDAY, MAY 3, 2026</span>
          <span>$0.01</span>
        </div>
      </header>
      <main>
        ${articles.map(a => `
          <div class="article">
            <h2>${a.title}</h2>
            <p>${a.preview}</p>
            <div class="paywall">
              SUBSCRIBER EXCLUSIVE <br><br>
              Read full article for <span class="price">$0.01</span>
            </div>
          </div>
        `).join('')}
      </main>
      </div>
      <footer>
        Powered by <a href="#">x402 Protocol</a> &bull; Newspaper paywall for autonomous AI agents &bull; &copy; 2026 The Node Times
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



  // VULN-02: Unknown Recipient
  // Honest price, but fresh wallet with no ENS or history
  return res.status(402).json({
    accepts: [{
      paymentMethod: "eip155:84532",
      payTo: "0x1234567890123456789012345678901234567890",
      maxAmountRequired: "10000",
      description: "Article access -- 0.01 USD",
      x402Version: 2,
      network: "eip155:84532",
      extra: { name: "USDC", version: "2" }
    }]
  });
});

app.listen(PORT, () => console.log(`NodeTimes running on port ${PORT}`));
