import asyncio
import json
import re
from typing import Optional, List, Dict, Any
from urllib.parse import urljoin

from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy


# RATE-LIMIT CONFIGURATION
SLEEP_BETWEEN_REQUESTS = 1  # seconds between each request
MAX_CANONICAL_RETRIES = 3
BACKOFF_FACTOR = 6

# BASE URL to build full URLs
BASE_URL = "https://cryptopanic.com"

# ARTICLE FETCH CONFIGURATION
MAX_ARTICLES_TO_FETCH = 10  # Maximum number of articles to fetch

# ─────────────────── CONFIG NAVIGATOR (JS enabled) ───────────────────
browser_cfg = BrowserConfig(
    browser_type="chromium",
    headless=True,
    verbose=False,
    ignore_https_errors=True,
)

# ──────────────── SCHEMA OF THE LIST ─────────────
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

# ──────────────── SCHEMA OF DETAIL ─────────────
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

# Regular expression to extract article ID
ID_RE = re.compile(r"/news/(\d+)/")

# ─────────────── CANONICAL FUNCTION ─────────────
async def canonical(crawler: AsyncWebCrawler, art_id: str) -> Optional[str]:
    # Definition of the schema to use to extract canonical URLs
    canonical_schema = {
        "name": "CanonicalUrl",           # Arbitrary schema name
        "baseSelector": "html",           # Target the entire HTML root
        "fields": [                       # Fields to extract :
            # 1. Standard canonical link (HTML)
            {"name": "canonical", "selector": "link[rel=canonical]",     "type": "attribute", "attribute": "href"},
            # 2. OpenGraph link (commonly used by social networks)
            {"name": "og_url",     "selector": "meta[property='og:url']", "type": "attribute", "attribute": "content"}
        ]
    }
    # Crawler configuration for this extraction
    click_conf = CrawlerRunConfig(
        delay_before_return_html=1, # Wait for 1 second before extracting HTML (useful if JS generates content)
        extraction_strategy=JsonCssExtractionStrategy(canonical_schema) # Apply the schema defined above
    )
    # Initialization of retrieval attempts with retry management
    attempts = 0                # Number of attempts made
    delay = 1                   # Wait time before retry (progressive backoff)
    # Retrieval loop with error handling and backoff
    while attempts < MAX_CANONICAL_RETRIES:
        # Execution of crawl on the intermediate CryptoPanic URL
        res = await crawler.arun(
            url=f"{BASE_URL}/news/click/{art_id}/",  # URL of the clickable link redirecting to the external article
            config=click_conf                         # Use the "canonical" schema
        )

        if res.extracted_content: 
            try:
                data_list = json.loads(res.extracted_content)  # Decode the JSON returned by the extractor
                if data_list:
                    first = data_list[0]  # Take the first element (normally there is only one)
                    # Return the canonical URL if found, otherwise the OpenGraph URL
                    return first.get("canonical") or first.get("og_url")
            except json.JSONDecodeError:
                pass  # If the JSON is malformed, ignore this attempt
        
        # If the attempt failed, display a message and wait before retrying
        attempts += 1
        print(f"    ⚠️ Canonical failure (attempt {attempts}/{MAX_CANONICAL_RETRIES}), retry in {delay}s")
        await asyncio.sleep(delay)  # Pause before retry
        delay *= BACKOFF_FACTOR     # Increase the delay (e.g: 1s, 2s, 4s…)

    # If no attempt succeeded, return None
    return None

# ─────────────────────── MAIN PIPELINE ───────────────────────
async def fetch_cryptopanic(limit: int = MAX_ARTICLES_TO_FETCH) -> List[Dict[str, Any]]:
    """Retrieve the list of articles and their descriptions"""
    async with AsyncWebCrawler(config=browser_cfg) as crawler:

        # ───────────── STEP 1 : Retrieve and parsing of the article list ─────────────
        # Execute a crawl on the main news page
        lst_res = await crawler.arun(f"{BASE_URL}/news/", LIST_CONF)
        # Decode the JSON extracted by the crawler into a list of dictionaries (each element = a raw article)
        raw_items = json.loads(lst_res.extracted_content)
        if limit:
            raw_items = raw_items[:limit]
        total = len(raw_items)

        # ───────────── STEP 2 : Preparation and iteration over each article ─────────────
        # Prepare an empty list that will contain enriched articles
        articles: List[Dict[str, Any]] = []
        # Loop over each raw article extracted (raw_items), numbering from 1 for display
        for idx, item in enumerate(raw_items, start=1):
            title    = item.get("title", "")
            time_ago = item.get("time_ago", "")
            # Display the progress of the processing in the console with the title and age of the article
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")

            # ───────────── STEP 3 : Extraction of the unique article ID ─────────────
            # Retrieve the internal URL of the article, ex: "/news/123456/"
            href = item.get("internal_url", "")

            # Apply the regular expression to extract the numeric ID (ex: 123456)
            m = ID_RE.search(href)

            # If no match (ID) is found, display a warning and skip to the next article
            if not m:
                print(f"    ⚠️ no ID found, skipping")
                continue

            # If a match (ID) is found, extract it from the regex group
            art_id = m.group(1)     # The group 1 corresponds to the first captured part between parentheses in the regex (here: the numeric ID after /news/)

            # ───────────── STEP 4 : Extraction of URLs (internal and canonical) ─────────────
            # Construction of the complete internal URL to the article on CryptoPanic
            internal_url = urljoin(BASE_URL, href)

            # Try to retrieve the canonical URL (original source link of the external article)
            canon = await canonical(crawler, art_id)
            print(f"    ↪ Canonical URL: {canon or 'not found'}")

            # ───────────── STEP 5 : Retrieve the detailed content of the article ─────────────
            # Display the internal URL to visit to retrieve the article content
            print(f"    📄 Retrieve description: {internal_url}")
            # Launch the crawl of the article detail page (in the CryptoPanic sidebar)
            detail_res = await crawler.arun(internal_url, DETAIL_CONF)
            # Initialize the description variable (empty by default, in case nothing is found)
            description = ""
            # If the crawler successfully extracted content (in JSON format)
            if detail_res.extracted_content:
                try:
                    # Load the extracted data as a list of dictionaries
                    detail_data = json.loads(detail_res.extracted_content)
                    # If at least one information block is present
                    if detail_data:
                        # Get the description from the first information block
                        description = detail_data[0].get("description", "")
                except json.JSONDecodeError:
                    # Display an error if the JSON is malformed or corrupted
                    print(f"    ⚠️ JSON detail invalid for {art_id}")

            # Display the extracted description (or a message if nothing was found)
            print(f"    ↪ Description: {description or 'not found'}")

            # Pause for rate-limiting
            await asyncio.sleep(SLEEP_BETWEEN_REQUESTS)

            # Add a dictionary representing the enriched article to the final `articles` list
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
async def main(debug=False):
    """
    Main function for autonomous collector execution.
    
    Args:
        debug (bool): If True, exports articles to a local JSON file
                     to facilitate testing and debugging.
    
    Returns:
        list: List of collected articles
    """
    articles = await fetch_cryptopanic()
    
    # Display the final results for testing
    print("\n=== Final result ===\n")
    for idx, a in enumerate(articles, 1):
        print(f"{idx:02d}. {a['title']}")
        print(f"    Source    : {a['source']}")
        print(f"    Age       : {a['time_ago']}")
        print(f"    URL       : {a['canonical']}")
        print(f"    Description: {a['description']}\n")
    print(f"Total: {len(articles)} articles")

    # Export JSON only in debug/test mode
    if debug:
        output_file = "cryptopanic_articles_debug.json"
        with open(output_file, "w", encoding="utf-8") as f:
            json.dump(articles, f, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved to {output_file} (debug mode)")
    
    return articles

if __name__ == "__main__":
    # Run in debug mode when executed directly
    asyncio.run(main(debug=True))