import asyncio
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import sys

from crawl4ai import AsyncWebCrawler, CrawlerRunConfig

# Ajouter le répertoire parent au chemin pour pouvoir importer les modules du projet
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import des modules du projet existant - à adapter si nécessaire
try:
    from shared.db import Article
except ImportError:
    print("AVERTISSEMENT: Module shared.db non trouvé. Exécution en mode test uniquement.")
    Article = None

# Configuration
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/observer")
NEWS_URL = "https://cryptopanic.com/news"
SOURCE_NAME = "cryptopanic"

# Configuration de la base de données si le module Article est disponible
engine = None
SessionLocal = None
if Article:
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

async def extract_and_save_articles():
    """Extrait les titres et liens des articles de cryptopanic et les sauvegarde en base de données"""
    
    # Configurer le crawler pour cibler spécifiquement les éléments d'articles
    config = CrawlerRunConfig(
        # Cibler les éléments d'articles selon la structure HTML de cryptopanic
        target_elements=[".news-row"],  # Récupère tous les types de news-row (link, media, etc.)
        js_code="""
            // Attendre que tous les articles soient chargés
            await new Promise(r => setTimeout(r, 20000));
        """,  # Attendre le chargement complet du contenu dynamique
        # Pas besoin de capturer les images, PDF, etc.
        screenshot=False,
        pdf=False,
        capture_mhtml=False,
        verbose=True  # Afficher plus d'informations de débogage
    )
    
    print(f"Extraction des articles depuis {NEWS_URL}")
    
    # Initialiser le crawler
    async with AsyncWebCrawler() as crawler:
        # Exécuter la requête de crawling
        result = await crawler.arun(
            url=NEWS_URL,
            config=config
        )
        
        # Utiliser BeautifulSoup pour extraire les données précisément
        from bs4 import BeautifulSoup
        
        # Analyser le HTML récupéré
        soup = BeautifulSoup(result.html, 'html.parser')
        
        # Trouver tous les éléments d'articles
        article_rows = soup.select('.news-row.news-row-link')
        
        articles = []
        for article in article_rows:
            try:
                # Extraire le titre de l'article
                title_elem = article.select_one('.news-cell.nc-title .title-text span')
                title = title_elem.text.strip() if title_elem else ''
                
                # Extraire l'URL de l'article
                click_area = article.select_one('a.click-area')
                url = click_area['href'] if click_area and 'href' in click_area.attrs else ''
                
                # Si l'URL est relative, la convertir en URL absolue
                if url and url.startswith('/'):
                    url = f"https://cryptopanic.com{url}"
                
                # Extraire la source (domaine)
                source_elem = article.select_one('.si-source-domain')
                source = source_elem.text.strip() if source_elem else SOURCE_NAME
                
                # Extraire la monnaie (si disponible)
                currency_elem = article.select_one('.news-cell.nc-currency a.colored-link')
                currency = currency_elem.text.strip() if currency_elem else None
                
                # Vérifier si c'est un lien d'article valide
                if title and url and 'cryptopanic.com/news/' in url:
                    articles.append({
                        "title": title,
                        "url": url,
                        "source": source,
                        "currency": currency
                    })
            except Exception as e:
                print(f"Erreur lors de l'extraction d'un article: {e}")
        
        print(f"Extraction terminée: {len(articles)} articles trouvés")
        
        # Stocker les articles si la base de données est configurée
        if Article and SessionLocal:
            db = SessionLocal()
            try:
                count_new = 0
                for article in articles:
                    # Vérifier si l'article existe déjà
                    existing = db.query(Article).filter(Article.url == article["url"]).first()
                    if existing:
                        print(f"Article déjà existant: {article['title']}")
                        continue
                    
                    # Créer un nouvel article
                    new_article = Article(
                        url=article["url"],
                        title=article["title"],
                        content="",  # Contenu vide car nous ne récupérons que les titres et liens
                        markdown_content="",
                        source=SOURCE_NAME
                    )
                    
                    # Ajouter à la base de données
                    db.add(new_article)
                    count_new += 1
                
                # Valider les changements
                if count_new > 0:
                    db.commit()
                    print(f"{count_new} nouveaux articles ajoutés à la base de données")
                else:
                    print("Aucun nouvel article à ajouter")
            
            except Exception as e:
                db.rollback()
                print(f"Erreur lors de l'enregistrement en base de données: {e}")
            
            finally:
                db.close()
        else:
            # Afficher les résultats si pas de base de données
            print("Mode test - Affichage des articles trouvés:")
            for idx, article in enumerate(articles, 1):
                print(f"{idx}. {article['title']} - {article['url']}")
        
        return articles

async def main():
    await extract_and_save_articles()

if __name__ == "__main__":
    asyncio.run(main())