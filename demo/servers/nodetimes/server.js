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
    <html>
    <head>
      <title>NodeTimes | Developer Insights</title>
      <style>
        body { background: #0f0f1a; color: #e2e8f0; font-family: system-ui, sans-serif; margin: 0; padding: 2rem; }
        header { border-bottom: 2px solid #a855f7; padding-bottom: 1rem; margin-bottom: 2rem; }
        h1 { color: #a855f7; margin: 0; }
        .article { background: #1e1e2f; padding: 1.5rem; margin-bottom: 1rem; border-radius: 8px; border-left: 4px solid #a855f7; }
        .paywall { color: #94a3b8; font-size: 0.9rem; margin-top: 1rem; font-style: italic; }
        .price { color: #a855f7; font-weight: bold; }
      </style>
    </head>
    <body>
      <header>
        <h1>NodeTimes</h1>
        <p>Deep technical dives into Web3 infrastructure.</p>
      </header>
      <main>
        ${articles.map(a => `
          <div class="article">
            <h2>${a.title}</h2>
            <p>${a.preview}</p>
            <div class="paywall">Read full article for <span class="price">$0.01</span></div>
          </div>
        `).join('')}
      </main>
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
