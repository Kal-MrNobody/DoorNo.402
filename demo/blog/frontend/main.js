const BLOG_API_URL = "http://localhost:3000";

const articlesEl = document.getElementById("articles");
const articleContent = document.getElementById("article-content");
const paywall = document.getElementById("paywall");

function isArticlePage() {
  return !!articleContent;
}

function getSlugFromUrl() {
  const params = new URLSearchParams(window.location.search);
  return params.get("slug");
}

async function loadArticleList() {
  if (!articlesEl) return;
  try {
    const resp = await fetch(`${BLOG_API_URL}/api/articles`);
    const articles = await resp.json();
    articlesEl.innerHTML = articles.map((a) => `
      <div class="article-card" onclick="window.location='article.html?slug=${a.slug}'">
        ${a.premium ? '<span class="premium-badge">Premium</span>' : ""}
        <h2>${a.title}</h2>
        <p>${a.preview}</p>
      </div>
    `).join("");
  } catch (e) {
    articlesEl.innerHTML = '<p class="loading">Could not load articles. Is the backend running?</p>';
  }
}

async function loadArticle() {
  if (!articleContent) return;
  const slug = getSlugFromUrl();
  if (!slug) {
    articleContent.innerHTML = "<p>No article specified.</p>";
    return;
  }

  try {
    const resp = await fetch(`${BLOG_API_URL}/api/articles/${slug}`);

    if (resp.status === 402) {
      const data = await resp.json();
      const price = data.accepts?.[0]?.description || "payment required";
      articleContent.innerHTML = `
        <h1>Premium Article</h1>
        <div class="content">This content is behind the x402 paywall. The server claims "${price}" but the actual charge may differ. An autonomous agent would pay this automatically without validation.</div>
      `;
      articleContent.classList.add("blurred");
      if (paywall) paywall.classList.remove("hidden");
      return;
    }

    const article = await resp.json();
    articleContent.innerHTML = `
      <h1>${article.title}</h1>
      <div class="content">${article.content}</div>
    `;
  } catch (e) {
    articleContent.innerHTML = '<p class="loading">Could not load article.</p>';
  }
}

if (isArticlePage()) {
  loadArticle();
} else {
  loadArticleList();
}
