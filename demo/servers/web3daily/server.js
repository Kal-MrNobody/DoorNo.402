const express = require('express');
const cors = require('cors');
const articles = require('./articles');
require('dotenv').config({ path: '../../../../.env' });

// This server demonstrates VULN-06 TLS downgrade
// Deploy without HTTPS or test on http://localhost
// DoorNo.402 blocks payments to non-TLS endpoints

const app = express();
const PORT = process.env.PORT || 3005;
const ATTACKER_WALLET = process.env.ATTACKER_WALLET || '0x3526cd391Aa5B4E8ca65C51235d40612d9F74822';

app.use(cors());
app.use(express.json());

app.get('/', (req, res) => {
  res.send(`
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>W3B DAILY | The Future of Culture</title>
      <link href="https://fonts.googleapis.com/css2?family=Oswald:wght@500;700&family=Roboto:wght@400;500&display=swap" rel="stylesheet">
      <style>
        :root { --bg: #f4f4f0; --text: #000000; --accent: #ff0055; --secondary: #00e5ff; }
        body { background: var(--bg); color: var(--text); font-family: 'Roboto', sans-serif; margin: 0; padding: 0; }
        header { background: #000; color: #fff; padding: 1.5rem 2rem; display: flex; align-items: center; justify-content: space-between; border-bottom: 8px solid var(--accent); }
        h1 { font-family: 'Oswald', sans-serif; font-size: 3rem; margin: 0; line-height: 1; letter-spacing: -1px; text-transform: uppercase; }
        h1 span { color: var(--secondary); }
        .tagline { font-weight: 500; font-size: 1rem; text-transform: uppercase; letter-spacing: 2px; }
        main { padding: 3rem 2rem; max-width: 1200px; margin: 0 auto; display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 3rem; }
        .article { background: #fff; border: 4px solid #000; box-shadow: 8px 8px 0px var(--accent); padding: 2rem; display: flex; flex-direction: column; transition: transform 0.1s, box-shadow 0.1s; }
        .article:hover { transform: translate(4px, 4px); box-shadow: 4px 4px 0px var(--accent); }
        h2 { font-family: 'Oswald', sans-serif; font-size: 2.2rem; line-height: 1.1; margin-top: 0; margin-bottom: 1rem; text-transform: uppercase; }
        p { font-size: 1.1rem; line-height: 1.5; font-weight: 500; margin-bottom: 2rem; flex-grow: 1; }
        .paywall { background: #000; color: #fff; padding: 1rem; text-align: center; text-transform: uppercase; font-family: 'Oswald', sans-serif; font-size: 1.2rem; letter-spacing: 1px; margin-top: auto; border: 2px solid #000; }
        .price { color: var(--secondary); font-weight: 700; }
      </style>
    </head>
    <body>
      <header>
        <h1>W3B<span>DAILY</span></h1>
        <div class="tagline">Tech. Culture. Future.</div>
      </header>
      <main>
        ${articles.map(a => `
          <div class="article">
            <h2>${a.title}</h2>
            <p>${a.preview}</p>
            <div class="paywall">
              Read Story | <span class="price">$0.01</span>
            </div>
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

  // VULN-06: TLS Downgrade
  // Honest price, honest recipient, but running on plain HTTP
  return res.status(402).json({
    accepts: [{
      paymentMethod: "eip155:84532",
      payTo: ATTACKER_WALLET,
      maxAmountRequired: "10000",
      description: "Article access -- 0.01 USD",
      x402Version: 2,
      network: "eip155:84532",
      extra: { name: "USDC", version: "2" }
    }]
  });
});

app.listen(PORT, () => console.log(`Web3Daily running on port ${PORT}`));
