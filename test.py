import asyncio
import json
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

base_browser = BrowserConfig(
    browser_type="chromium",
    headless=True,
    viewport_width=1280,
    viewport_height=800,
    user_agent_mode="random",
    verbose=True,
    ignore_https_errors=True,
    use_persistent_context=False,
    text_mode=True,
    light_mode=True,
)

async def extract_cryptopanic_titles_links():
    # Définir le schéma d'extraction
    schema = {
        "name": "CryptopanicArticles",
        "baseSelector": ".news-container.ps .news > .news-row.news-row-link",  # Sélecteur plus spécifique
        "fields": [
            {
                "name": "title",
                "selector": ".news-cell.nc-title .title-text span",
                "type": "text"
            },
            {
                "name": "url",
                "selector": "a.click-area",
                "type": "attribute",
                "attribute": "href"
            },
            {
                "name": "source",
                "selector": ".si-source-domain",
                "type": "text"
            }
        ]
    }
    
    # Configurer le crawler avec la stratégie d'extraction
    config = CrawlerRunConfig(
        target_elements=[".app-main-pane .news-container.ps .news > .news-row.news-row-link"],  # Focus sur ces éléments
        wait_for=".app-main-pane .news-container.ps .news > .news-row.news-row-link",  # Attendre que ces éléments apparaissent
        extraction_strategy=JsonCssExtractionStrategy(schema),  # Stratégie d'extraction
        js_code="""
        // Fonction pour charger progressivement plus d'articles
        async function loadMoreArticles(minCount = 20) {
            const getCount = () => document.querySelectorAll('.app-main-pane .news-container.ps .news > .news-row.news-row-link').length;
            let initialCount = getCount();
            let currentCount = initialCount;
            
            // Essayer jusqu'à 3 fois de charger plus d'articles
            for (let i = 0; i < 3; i++) {
                // Défiler jusqu'en bas
                window.scrollTo(0, document.body.scrollHeight);
                
                // Attendre que de nouveaux éléments se chargent
                await new Promise(r => setTimeout(r, 2000));
                
                // Vérifier si de nouveaux articles ont été chargés
                let newCount = getCount();
                if (newCount > currentCount) {
                    currentCount = newCount;
                    console.log(`${currentCount} articles chargés`);
                } else {
                    // Aucun nouvel article chargé, on arrête
                    console.log("Pas de nouveaux articles chargés, fin du chargement");
                    break;
                }
                
                // Si on a assez d'articles, on arrête
                if (currentCount >= minCount) {
                    console.log(`Objectif atteint: ${currentCount} articles chargés`);
                    break;
                }
            }
            
            return currentCount;
        }
        
        return await loadMoreArticles(30);
        """
    )
    
    # Exécuter le crawler
    async with AsyncWebCrawler(config=base_browser) as crawler:
        result = await crawler.arun(
            url="https://cryptopanic.com/news",
            config=config
        )
        
        # Extraire les résultats au format JSON
        if result.extracted_content:
            articles = json.loads(result.extracted_content)
            
            # Traiter les URLs relatives
            for article in articles:
                if article.get('url') and article['url'].startswith('/'):
                    article['url'] = f"https://cryptopanic.com{article['url']}"
            
            return articles
        else:
            print("Aucun contenu extrait")
            return []

async def main():
    articles = await extract_cryptopanic_titles_links()
    
    # Afficher le résultat
    for i, article in enumerate(articles[:10]):
        print(f"{i+1}. {article.get('title')}")
        print(f"   URL: {article.get('url')}")
        print(f"   Source: {article.get('source') or 'N/A'}")
        print("---")
    print(f"Total: {len(articles)} articles trouvés")

if __name__ == "__main__":
    asyncio.run(main())

