# scripts/cryptopanic_article_description.py
import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# CONFIGURATION
BASE_URL = "https://cryptopanic.com"
SLEEP_BETWEEN_REQUESTS = 1  # seconds between each request

# BROWSER CONFIG (JS enabled)
browser_cfg = BrowserConfig(
    browser_type="chromium",
    headless=True,
    verbose=False,
    ignore_https_errors=True,
)

# ARTICLE LIST SCHEMA (similar to the existing collector)
LIST_SCHEMA = {
    "name": "Articles",
    "baseSelector": ".app-main-pane .news-container.ps .news > .news-row.news-row-link",
    "fields": [
        {"name": "title",        "selector": ".title-text span",          "type": "text"},
        {"name": "internal_url", "selector": "a.click-area",             "type": "attribute", "attribute": "href"},
        {"name": "source",       "selector": ".si-source-domain",        "type": "text"},
        {"name": "time_ago",     "selector": ".news-cell.nc-date time",  "type": "text"},
    ]
}

# ARTICLE DETAIL SCHEMA (for the description)
DETAIL_SCHEMA = {
    "name": "ArticleDetail",
    "baseSelector": "html",
    "fields": [
        {"name": "description", "selector": ".description-body", "type": "text"},
        {"name": "title",       "selector": ".post-title .text",  "type": "text"},
    ]
}

# CONFIGURATIONS
LIST_CONF = CrawlerRunConfig(
    wait_for="css:.app-main-pane .news-container.ps .news > .news-row.news-row-link",
    target_elements=[".app-main-pane .news-container.ps .news > .news-row.news-row-link"],
    extraction_strategy=JsonCssExtractionStrategy(LIST_SCHEMA)
)

DETAIL_CONF = CrawlerRunConfig(
    wait_for="css:.description-body",  # Wait for description to be loaded
    extraction_strategy=JsonCssExtractionStrategy(DETAIL_SCHEMA)
)

ID_RE = re.compile(r"/news/(\d+)/")

async def fetch_article_descriptions(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch article descriptions from CryptoPanic
    
    Args:
        limit: Maximum number of articles to process
        
    Returns:
        List of article data with descriptions
    """
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        # First, fetch the article list
        print("Fetching article list...")
        lst_res = await crawler.arun(f"{BASE_URL}/news/", LIST_CONF)
        raw_items = json.loads(lst_res.extracted_content)
        
        # Limit the number of articles to process
        articles_to_process = raw_items[:limit]
        total = len(articles_to_process)
        
        # Process each article
        articles_with_descriptions = []
        for idx, item in enumerate(articles_to_process, start=1):
            title = item["title"]
            time_ago = item.get("time_ago", "")
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")
            
            # Extract article ID and create full URL
            href = item.get("internal_url", "")
            m = ID_RE.search(href)
            
            if not m:
                print(f"  ⚠️ Could not extract ID from URL: {href}")
                continue
                
            article_id = m.group(1)
            article_url = urljoin(BASE_URL, href)
            
            # Fetch article detail page
            print(f"  📄 Fetching article: {article_url}")
            detail_res = await crawler.arun(article_url, DETAIL_CONF)
            
            if not detail_res.extracted_content:
                print(f"  ⚠️ No content extracted for article {article_id}")
                continue
                
            try:
                detail_data = json.loads(detail_res.extracted_content)
                if not detail_data:
                    print(f"  ⚠️ Empty detail data for article {article_id}")
                    continue
                    
                article_detail = detail_data[0]  # First item in the array
                description = article_detail.get("description", "")
                
                # Create enriched article data
                enriched_article = {
                    **item,  # Include all original article data
                    "article_id": article_id,
                    "full_url": article_url,
                    "description": description
                }
                
                articles_with_descriptions.append(enriched_article)
                print(f"  ✅ Description extracted: {description[:50]}...")
                
            except json.JSONDecodeError:
                print(f"  ⚠️ Failed to parse JSON for article {article_id}")
                continue
                
            # Sleep between requests to avoid rate limiting
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)
            
    return articles_with_descriptions

async def main():
    articles = await fetch_article_descriptions(limit=5)
    
    # Print the results
    print("\n=== RESULTS ===")
    for article in articles:
        print(f"Title: {article['title']}")
        print(f"URL: {article['full_url']}")
        print(f"Description: {article['description']}")
        print("-" * 50)
    
    # Save to a JSON file for inspection
    with open("cryptopanic_articles_with_descriptions.json", "w", encoding="utf-8") as f:
        json.dump(articles, f, indent=2, ensure_ascii=False)
    
    print(f"\nSaved {len(articles)} articles with descriptions to 'cryptopanic_articles_with_descriptions.json'")

if __name__ == "__main__":
    asyncio.run(main())
