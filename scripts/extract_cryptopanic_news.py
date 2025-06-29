# scripts/extract_cryptopanic_news.py
import asyncio
import json
import re
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

# ──────────────── SCHEMA DE LA LISTE ─────────────
LIST_SCHEMA = {
    "name": "Articles",
    "baseSelector": ".app-main-pane .news-container.ps .news > .news-row.news-row-link",
    "fields": [
        {"name": "title",        "selector": ".title-text span",           "type": "text"},
        {"name": "internal_url", "selector": "a.click-area",             "type": "attribute", "attribute": "href"},
        {"name": "source",       "selector": ".si-source-domain",        "type": "text"},
        {"name": "time_ago",     "selector": ".news-cell.nc-date time",  "type": "text"},
    ]
}

LIST_CONF = CrawlerRunConfig(
    wait_for="css:.app-main-pane .news-container.ps .news > .news-row.news-row-link",
    target_elements=[".app-main-pane .news-container.ps .news > .news-row.news-row-link"],
    extraction_strategy=JsonCssExtractionStrategy(LIST_SCHEMA)
)

ID_RE = re.compile(r"/news/(\d+)/")

# ─────────────── FONCTION CANONICAL (avec JsonCssExtractionStrategy) ─────────────
async def canonical(crawler: AsyncWebCrawler, art_id: str) -> Optional[str]:
    # Schéma pour extraire la balise canonical ou og:url
    canonical_schema = {
        "name": "CanonicalUrl",
        "baseSelector": "html",
        "fields": [
            {"name": "canonical", "selector": "link[rel=canonical]",   "type": "attribute", "attribute": "href"},
            {"name": "og_url",     "selector": "meta[property='og:url']", "type": "attribute", "attribute": "content"}
        ]
    }
    click_conf = CrawlerRunConfig(
        delay_before_return_html=1,
        extraction_strategy=JsonCssExtractionStrategy(canonical_schema)
    )
    res = await crawler.arun(
        url=f"https://cryptopanic.com/news/click/{art_id}/",
        config=click_conf
    )
    if res.extracted_content:
        # JsonCssExtractionStrategy renvoie une liste de dicts
        data_list = json.loads(res.extracted_content)
        if data_list:
            first = data_list[0]
            return first.get("canonical") or first.get("og_url")
    return None

# ─────────────────────── PIPELINE PRINCIPAL ───────────────────────
async def fetch_cryptopanic() -> List[Dict]:
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        lst_res = await crawler.arun("https://cryptopanic.com/news/", LIST_CONF)
        raw_items = json.loads(lst_res.extracted_content)
        total = len(raw_items)

        articles: List[Dict] = []
        for idx, item in enumerate(raw_items, start=1):
            title    = item["title"]
            time_ago = item.get("time_ago", "")
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")

            href = item.get("internal_url", "")
            m = ID_RE.search(href)
            if not m:
                print("    ⚠️ pas d’ID trouvé, on skip")
                continue
            art_id = m.group(1)

            canon = await canonical(crawler, art_id)
            print(f"    ↪ Canonical URL: {canon or 'pas trouvé'}")

            articles.append({
                "article_id": art_id,
                "title":      title,
                "source":     item.get("source", ""),
                "time_ago":   time_ago,
                "internal":   f"https://cryptopanic.com{href}",
                "canonical":  canon or f"https://cryptopanic.com{href}",
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
