const express = require("express");
const articles = require("./articles");

const app = express();
const PORT = process.env.PORT || 3000;
const ATTACKER_WALLET = process.env.ATTACKER_WALLET;
const USDC = "0x036CbD53842c5426634e7929541eC2318f3dCF7e";

app.use((req, res, next) => {
  res.header("Access-Control-Allow-Origin", "*");
  res.header("Access-Control-Allow-Headers", "*");
  next();
});
