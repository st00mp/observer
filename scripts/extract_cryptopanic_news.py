# scripts/extract_cryptopanic_news.py
import asyncio, json, re
from typing import Optional, List, Dict

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# ─────────────────── CONFIG NAVIGATEUR (JS activé) ───────────────────
browser_cfg = BrowserConfig(
    browser_type="chromium",
    headless=True,
    verbose=False,
    ignore_https_errors=True,
)

# ──────────────── SCHEMA DE LA LISTE (ajout de "freshness") ─────────────
LIST_SCHEMA = {
    "name": "Articles",
    "baseSelector": ".app-main-pane .news-container.ps .news > .news-row.news-row-link",
    "fields": [
        {"name": "title",        "selector": ".title-text span",  "type": "text"},
        {"name": "internal_url", "selector": "a.click-area",      "type": "attribute", "attribute": "href"},
        {"name": "source",       "selector": ".si-source-domain", "type": "text"},
        {"name": "time_ago",     "selector": ".news-cell.nc-date time", "type": "text"},  # ← nouveau
    ]
}

LIST_CONF = CrawlerRunConfig(
    wait_for="css:.app-main-pane .news-container.ps .news > .news-row.news-row-link",
    target_elements=[".app-main-pane .news-container.ps .news > .news-row.news-row-link"],
    extraction_strategy=JsonCssExtractionStrategy(LIST_SCHEMA)
)

ID_RE = re.compile(r"/news/(\d+)/")

# ─────────────── FONCTION CANONICAL (sans wait_for) ────────────────
async def canonical(crawler: AsyncWebCrawler, art_id: str) -> Optional[str]:
    res = await crawler.arun(
        url=f"https://cryptopanic.com/news/click/{art_id}/",
        config=CrawlerRunConfig(
            delay_before_return_html=1  # juste 1s de pause, pas de timeout sur un élément caché
        )
    )
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(res.html, "html.parser")
    tag = (soup.select_one("link[rel=canonical]") or
           soup.select_one("meta[property='og:url']"))
    if tag:
        return tag.get("href") or tag.get("content")
    return None

# ─────────────────────── PIPELINE PRINCIPAL ────────────────────────
async def fetch_cryptopanic() -> List[Dict]:
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 1) on récupère la liste
        lst_res = await crawler.arun("https://cryptopanic.com/news/", LIST_CONF)
        raw_items = json.loads(lst_res.extracted_content)
        total = len(raw_items)

        articles: List[Dict] = []
        for idx, item in enumerate(raw_items, start=1):
            title     = item["title"]
            time_ago = item.get("time_ago", "")
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")

            href = item.get("internal_url", "")
            m = ID_RE.search(href)
            if not m:
                print("    ⚠️ pas d’ID trouvé, on skip")
                continue
            art_id = m.group(1)

            # 2) on va chercher l’URL canonique
            canon = await canonical(crawler, art_id)
            print(f"    ↪ Canonical URL: {canon or 'pas trouvé'}")

            articles.append({
                "article_id": art_id,
                "title":       title,
                "source":      item.get("source", ""),
                "time_ago":    time_ago,
                "internal":    f"https://cryptopanic.com{href}",
                "canonical":   canon or f"https://cryptopanic.com{href}",
            })

        return articles

# ────────────────────────────────────────────────────────────────────
async def main():
    arts = await fetch_cryptopanic()
    print("\n=== Résultat final ===\n")
    for idx, a in enumerate(arts, 1):
        print(f"{idx:02d}. {a['title']}")
        print(f"    Source    : {a['source']}")
        print(f"    Âge       : {a['time_ago']}")
        print(f"    URL       : {a['canonical']}\n")
    print(f"Total: {len(arts)} articles")

if __name__ == "__main__":
    asyncio.run(main())