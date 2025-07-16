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

# ARTICLE FETCH CONFIGURATION
MAX_ARTICLES_TO_FETCH = 10  # Nombre maximum d'articles à récupérer

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
    # Définition du schéma à utiliser pour extraire les URLs canoniques
    canonical_schema = {
        "name": "CanonicalUrl",           # Nom arbitraire du schéma
        "baseSelector": "html",           # On cible la racine HTML entière
        "fields": [                       # Champs à extraire :
            # 1. Lien canonique standard (HTML)
            {"name": "canonical", "selector": "link[rel=canonical]",     "type": "attribute", "attribute": "href"},
            # 2. Lien OpenGraph (souvent utilisé par les réseaux sociaux)
            {"name": "og_url",     "selector": "meta[property='og:url']", "type": "attribute", "attribute": "content"}
        ]
    }
    # Configuration du crawler pour cette extraction
    click_conf = CrawlerRunConfig(
        delay_before_return_html=1, # Attente de 1 seconde avant d'extraire le HTML (utile si JS génère le contenu)
        extraction_strategy=JsonCssExtractionStrategy(canonical_schema) # On applique le schéma défini ci-dessus
    )
    # Initialisation des tentatives de récupération avec gestion du retry
    attempts = 0                # Nombre de tentatives effectuées
    delay = 1                   # Temps d'attente avant retry (backoff progressif)
    # Boucle de récupération avec gestion des erreurs et backoff
    while attempts < MAX_CANONICAL_RETRIES:
        # Exécution du crawl sur l’URL intermédiaire de CryptoPanic
        res = await crawler.arun(
            url=f"{BASE_URL}/news/click/{art_id}/",  # URL du lien cliquable redirigeant vers l’article externe
            config=click_conf                         # Utilisation de la config dédiée au schéma "canonical"
        )

        if res.extracted_content: 
            try:
                data_list = json.loads(res.extracted_content)  # Décodage du JSON retourné par l'extracteur
                if data_list:
                    first = data_list[0]  # On prend le premier élément (normalement il n’y en a qu’un)
                    # On retourne l'URL canonique si trouvée, sinon l’URL OpenGraph
                    return first.get("canonical") or first.get("og_url")
            except json.JSONDecodeError:
                pass  # Si le JSON est mal formé, on ignore cette tentative
        
        # Si la tentative a échoué, on affiche un message et on attend avant de réessayer
        attempts += 1
        print(f"    ⚠️ Échec canonical (tentative {attempts}/{MAX_CANONICAL_RETRIES}), retry dans {delay}s")
        await asyncio.sleep(delay)  # Pause avant retry
        delay *= BACKOFF_FACTOR     # Augmente le délai (ex: 1s, 2s, 4s…)

    # Si aucune tentative n’a abouti, on retourne None
    return None

# ─────────────────────── PIPELINE PRINCIPAL ───────────────────────
async def fetch_cryptopanic(limit: int = MAX_ARTICLES_TO_FETCH) -> List[Dict[str, Any]]:
    """Récupère la liste des articles et leurs descriptions"""
    async with AsyncWebCrawler(config=browser_cfg) as crawler:

        # ───────────── ÉTAPE 1 : Récupération et parsing de la liste d'articles ─────────────
        lst_res = await crawler.arun(f"{BASE_URL}/news/", LIST_CONF)
        raw_items = json.loads(lst_res.extracted_content)
        if limit:
            raw_items = raw_items[:limit]
        total = len(raw_items)

        # ───────────── ÉTAPE 2 : Préparation et itération sur chaque article ─────────────
        # Préparation d'une liste vide qui contiendra les articles enrichis
        articles: List[Dict[str, Any]] = []
        # Boucle sur chaque article brut extrait (raw_items), en numérotant à partir de 1 pour l'affichage
        for idx, item in enumerate(raw_items, start=1):
            title    = item.get("title", "")
            time_ago = item.get("time_ago", "")
            # Affiche dans la console l’état d’avancement du traitement avec le titre et l’âge de l’article
            print(f"[{idx}/{total}] → {title} (il y a {time_ago})")

            # ───────────── ÉTAPE 3 : Extraction de l'ID unique de l'article ─────────────
            # Récupère l'URL interne de l'article, ex: "/news/123456/"
            href = item.get("internal_url", "")

            # Applique l'expression régulière pour extraire l'ID numérique (ex: 123456)
            m = ID_RE.search(href)

            # Si aucun match (ID) n'est trouvé, on affiche un avertissement et on passe à l'article suivant
            if not m:
                print(f"    ⚠️ pas d’ID trouvé, on skip")
                continue

            # Si un match (ID) est trouvé, on l'extrait depuis le groupe capturé par la regex
            art_id = m.group(1)     # Le groupe 1 correspond à la première sous-partie capturée entre parenthèses dans la regex (ici : l’ID numérique après /news/)

            # ───────────── ÉTAPE 4 : Extraction des URLs (internes et canoniques) ─────────────
            # Construction de l'URL complète vers la page interne de l'article sur CryptoPanic
            internal_url = urljoin(BASE_URL, href)
            # Tentative de récupération de l’URL canonique (= lien source original de l’article externe)
            canon = await canonical(crawler, art_id)
            print(f"    ↪ Canonical URL: {canon or 'pas trouvé'}")

            # ───────────── ÉTAPE 5 : Récupération du contenu détaillé de l’article ─────────────
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
    arts = await fetch_cryptopanic()
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