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
        "baseSelector": ".news-row.news-row-link",
        "fields": [
            {"name": "title", "selector": ".news-cell.nc-title .title-text span", "type": "text"},
            # Extraction du lien interne (conservé pour référence)
            {"name": "internal_url", "selector": "a.click-area", "type": "attribute", "attribute": "href"},
            # Extraction du lien externe
            {"name": "url", "selector": ".si-source-name", "type": "attribute", "attribute": "data-href"},
            # Si le sélecteur ci-dessus ne fonctionne pas, essayez celui-ci à la place :
            # {"name": "url", "selector": ".si-source-name a", "type": "attribute", "attribute": "href"},
            {"name": "source", "selector": ".si-source-domain", "type": "text"}
        ]
    }   
    
    # Configurer le crawler avec la stratégie d'extraction
    config = CrawlerRunConfig(
        target_elements=[".app-main-pane .news-container.ps .news > .news-row.news-row-link"],  # Focus sur ces éléments
        wait_for=".app-main-pane .news-container.ps .news > .news-row.news-row-link",  # Attendre que ces éléments apparaissent
        extraction_strategy=JsonCssExtractionStrategy(schema),  # Stratégie d'extraction
        js_code="""
        // Fonction pour charger progressivement plus d'articles puis extraire les liens externes
        async function processPage(minCount = 20) {
            // 1. Charger plus d'articles par défilement
            const getCount = () => document.querySelectorAll('.app-main-pane .news-container.ps .news > .news-row.news-row-link').length;
            let initialCount = getCount();
            let currentCount = initialCount;
            
            console.log(`Début: ${initialCount} articles déjà chargés`);
            
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
            
            // 2. Extraire les liens externes en simulant des clics
            const articles = [];
            const rows = document.querySelectorAll('.app-main-pane .news-container.ps .news > .news-row.news-row-link');
            
            console.log(`Extraction des liens externes pour ${rows.length} articles...`);
            
            // Pour chaque article...
            for (let i = 0; i < rows.length; i++) {
                const row = rows[i];
                
                // Extraire le titre
                const titleElement = row.querySelector('.news-cell.nc-title .title-text span');
                const title = titleElement ? titleElement.textContent.trim() : '';
                
                // Extraire la source
                const sourceElement = row.querySelector('.si-source-domain');
                const source = sourceElement ? sourceElement.textContent.trim() : '';
                
                // Extraire le lien cryptopanic (fallback)
                const internalLink = row.querySelector('a.click-area');
                const internalUrl = internalLink ? internalLink.getAttribute('href') : '';
                
                // Trouver l'icône de lien externe
                const linkIcon = row.querySelector('.open-link-icon.icon.icon-link');
                let externalUrl = '';
                
                // Si on trouve l'icône de lien externe, simuler un clic dessus et capturer la redirection
                if (linkIcon) {
                    try {
                        // Créer un capteur pour window.open
                        const oldOpenMethod = window.open;
                        let capturedUrl = null;
                        
                        // Remplacer temporairement window.open pour capturer l'URL
                        window.open = function(url) {
                            capturedUrl = url;
                            return { focus: () => {} }; // Stub pour éviter les erreurs
                        };
                        
                        // Simuler le clic sur l'icône
                        linkIcon.click();
                        
                        // Attendre un peu que le clic soit traité
                        await new Promise(r => setTimeout(r, 100));
                        
                        // Récupérer l'URL capturée
                        if (capturedUrl) {
                            externalUrl = capturedUrl;
                        }
                        
                        // Restaurer la méthode originale
                        window.open = oldOpenMethod;
                    } catch (e) {
                        console.error("Erreur lors du clic sur le lien externe:", e);
                    }
                }
                
                // Ajouter l'article si on a un titre
                if (title) {
                    articles.push({
                        title: title,
                        url: externalUrl || ("https://cryptopanic.com" + internalUrl), // URL externe ou interne complète
                        internal_url: internalUrl,
                        source: source
                    });
                }
            }
            
            console.log(`Extraction terminée: ${articles.length} articles avec leurs liens.`);
            return articles;
        }
        
        // Exécuter notre fonction et renvoyer les résultats
        return processPage(30);
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
    for i, article in enumerate(articles):
        print(f"{i+1}. {article.get('title')}")
        print(f"   URL: {article.get('url')}")
        print(f"   Source: {article.get('source') or 'N/A'}")
        print("---")
    print(f"Total: {len(articles)} articles trouvés")

if __name__ == "__main__":
    asyncio.run(main())

