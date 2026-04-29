# Cryptology Blog — Backend Deploy (Render)

## Steps

1. Go to [render.com](https://render.com) and sign in
2. Click **New** → **Web Service**
3. Connect your GitHub repo: `Kal-MrNobody/DoorNo.402`
4. Set **Root Directory** to `demo/blog/backend`
5. **Build Command**: `npm install`
6. **Start Command**: `node server.js`
7. **Environment Variables**:
   - `ATTACKER_WALLET` — your wallet address
   - `PORT` — leave blank (Render sets this automatically)
8. Click **Deploy**
9. Copy the deployed URL (e.g. `https://doorno402-blog.onrender.com`)
10. Update `BLOG_API_URL` in `demo/blog/frontend/main.js` to this URL before deploying frontend
