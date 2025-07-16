import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# @todo:
# - Créer logique métier pour ne pas récupérer les articles déjà en base.

# RATE-LIMIT CONFIGURATION
SLEEP_BETWEEN_REQUESTS = 1  # seconds between each request
MAX_CANONICAL_RETRIES = 3
BACKOFF_FACTOR = 2

# BASE URL pour construire les URLs complètes
BASE_URL = "https://cryptopanic.com"

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

# ──────────────── SCHEMA DE DÉTAIL ─────────────
DETAIL_SCHEMA = {
    "name": "ArticleDetail",
    "baseSelector": "#detail_pane",
    "fields": [
        {"name": "description", "selector": ".description-body", "type": "text"},
        {"name": "title",       "selector": ".post-title .text",  "type": "text"},
    ]
}

DETAIL_CONF = CrawlerRunConfig(
    wait_for="css:.description-body",
    extraction_strategy=JsonCssExtractionStrategy(DETAIL_SCHEMA)
)

# Expression régulière pour extraire l'ID de l'article
ID_RE = re.compile(r"/news/(\d+)/")

# ─────────────── FONCTION CANONICAL ─────────────
async def canonical(crawler: AsyncWebCrawler, art_id: str) -> Optional[str]:
    canonical_schema = {
        "name": "CanonicalUrl",
        "baseSelector": "html",
        "fields": [
            {"name": "canonical", "selector": "link[rel=canonical]",     "type": "attribute", "attribute": "href"},
            {"name": "og_url",     "selector": "meta[property='og:url']", "type": "attribute", "attribute": "content"}
        ]
    }
    click_conf = CrawlerRunConfig(
        delay_before_return_html=1,
        extraction_strategy=JsonCssExtractionStrategy(canonical_schema)
    )
    attempts = 0
    delay = 1
    while attempts < MAX_CANONICAL_RETRIES:
        res = await crawler.arun(
            url=f"{BASE_URL}/news/click/{art_id}/",
            config=click_conf
        )
        if res.extracted_content:
            try:
                data_list = json.loads(res.extracted_content)
                if data_list:
                    first = data_list[0]
                    return first.get("canonical") or first.get("og_url")
            except json.JSONDecodeError:
                pass
        attempts += 1
        print(f"    ⚠️ Échec canonical (tentative {attempts}/{MAX_CANONICAL_RETRIES}), retry dans {delay}s")
        await asyncio.sleep(delay)
        delay *= BACKOFF_FACTOR
    return None

# ─────────────────────── PIPELINE PRINCIPAL ───────────────────────
async def fetch_cryptopanic(limit: int = 10) -> List[Dict[str, Any]]:
    """Récupère la liste des articles et leurs descriptions"""
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # 1. Récupération de la liste
        lst_res = await crawler.arun(f"{BASE_URL}/news/", LIST_CONF)
        raw_items = json.loads(lst_res.extracted_content)
        if limit:
            raw_items = raw_items[:limit]
        total = len(raw_items)

        articles: List[Dict[str, Any]] = []
        for idx, item in enumerate(raw_items, start=1):
            title    = item.get("title", "")
            time_ago = item.get("time_ago", "")
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")

            href = item.get("internal_url", "")
            m = ID_RE.search(href)
            if not m:
                print(f"    ⚠️ pas d’ID trouvé, on skip")
                continue
            art_id = m.group(1)

            # Construction des URLs
            internal_url = urljoin(BASE_URL, href)
            canon = await canonical(crawler, art_id)
            print(f"    ↪ Canonical URL: {canon or 'pas trouvé'}")

            # 2. Récupération de la description
            print(f"    📄 Récupération description: {internal_url}")
            detail_res = await crawler.arun(internal_url, DETAIL_CONF)
            description = ""
            if detail_res.extracted_content:
                try:
                    detail_data = json.loads(detail_res.extracted_content)
                    if detail_data:
                        description = detail_data[0].get("description", "")
                except json.JSONDecodeError:
                    print(f"    ⚠️ JSON détail invalide pour {art_id}")
            print(f"    ↪ Description: {description or 'pas trouvée'}")

            # Pause pour le rate-limit
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

            articles.append({
                "article_id":  art_id,
                "title":       title,
                "source":      item.get("source", ""),
                "time_ago":    time_ago,
                "internal":    internal_url,
                "canonical":   canon or internal_url,
                "description": description,
            })

        return articles

# ────────────────────────────────────────────────────────────────────
async def main():
    arts = await fetch_cryptopanic(limit=5)
    print("\n=== Résultat final ===\n")
    for idx, a in enumerate(arts, 1):
        print(f"{idx:02d}. {a['title']}")
        print(f"    Source    : {a['source']}")
        print(f"    Âge       : {a['time_ago']}")
        print(f"    URL       : {a['canonical']}")
        print(f"    Description: {a['description']}\n")
    print(f"Total: {len(arts)} articles")

    # Sauvegarde dans un fichier JSON
    output_file = "cryptopanic_articles.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(arts, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Sauvegardé dans {output_file}")

if __name__ == "__main__":
    asyncio.run(main())