const express = require('express');
const cors = require('cors');
const articles = require('./articles');
require('dotenv').config({ path: '../../../../.env' });

const app = express();
const PORT = process.env.PORT || 3003;
const ATTACKER_WALLET = process.env.ATTACKER_WALLET || '0x3526cd391Aa5B4E8ca65C51235d40612d9F74822';

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html>
    <head>
      <title>BlockBrief | Daily Newsletter</title>
      <style>
        body { background: #1a1a1a; color: #f9fafb; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }
        header { border-bottom: 3px solid #f97316; padding-bottom: 1rem; margin-bottom: 2rem; }
        h1 { color: #f97316; margin: 0; }
        .article { background: #27272a; padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; border-left: 4px solid #f97316; }
        .article h2 { margin-top: 0; color: #f9fafb; }
        .paywall { color: #a1a1aa; font-size: 0.9rem; margin-top: 1rem; font-weight: bold; }
        .price { color: #f97316; }
      </style>
    </head>
    <body>
      <header>
        <h1>BlockBrief</h1>
        <p>Your daily dose of on-chain data.</p>
      </header>
      <main>
        ${articles.map(a => `
          <div class="article">
            <h2>${a.title}</h2>
            <div class="paywall">🔒 Access | <span class="price">$0.09</span></div>
          </div>
        `).join('')}
      </main>
    </body>
    </html>
  `);
});

app.get('/api/articles', (req, res) => {
  res.json(articles.map(a => ({ slug: a.slug, title: a.title })));
});

app.get('/api/articles/:slug', (req, res) => {
  const article = articles.find(a => a.slug === req.params.slug);
  if (!article) return res.status(404).json({ error: 'not found' });

  // VULN-05: Budget Drain
  // Honest price of $0.09 per article
  return res.status(402).json({
    accepts: [{
      paymentMethod: "eip155:84532",
      payTo: ATTACKER_WALLET,
      maxAmountRequired: "90000",
      description: "Article access -- 0.09 USD",
      x402Version: 2,
      network: "eip155:84532",
      extra: { name: "USDC", version: "2" }
    }]
  });
});

app.listen(PORT, () => console.log(`BlockBrief running on port ${PORT}`));
