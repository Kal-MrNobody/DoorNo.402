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
    <html>
    <head>
      <title>Web3Daily | Terminal</title>
      <style>
        body { background: #000000; color: #00ff00; font-family: monospace; margin: 0; padding: 2rem; }
        header { border-bottom: 1px solid #00ff00; padding-bottom: 1rem; margin-bottom: 2rem; }
        h1 { margin: 0; }
        .article { border: 1px dashed #00ff00; padding: 1.5rem; margin-bottom: 1rem; }
        .paywall { margin-top: 1rem; }
      </style>
    </head>
    <body>
      <header>
        <h1>root@web3daily:~# ./start</h1>
        <p>Connecting to decentralized net...</p>
      </header>
      <main>
        ${articles.map(a => `
          <div class="article">
            <h2>> ${a.title}</h2>
            <p>${a.preview}</p>
            <div class="paywall">[LOCKED] Execute payment of 0.01 USD to decrypt</div>
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
