# 🚀 **Syntinel Project**

**Un système modulaire de microservices pour scruter l’actualité, filtrer, scorer, générer et publier du contenu différencié automatiquement, tout en gardant un contrôle humain final.**

---

## 📂️ **Architecture**

Ce projet repose sur une **architecture orientée microservices**, orchestrée par un cœur central (`core/syntinel`) et enrichie de services spécialisés (`services/`).
Chaque brique est isolée selon le principe **Feature-Sliced Design (FSD)** pour une organisation claire et évolutive.

---

### 📌 **Structure du projet**

```
syntinel/
├── core/                     # Orchestrateur central
│   └── syntinel/
│       ├── orchestrator.py   # Point d'entrée pour exécuter les pipelines métiers
│       ├── modules/          # Modules métiers (FSD)
│       │   ├── ingestion/    # Extraction, dédoublonnage, normalisation, Redis
│       │   │   ├── ingestion_pipeline.py
│       │   │   └── collector/
│       │   │       ├── base.py
│       │   │       └── CryptoPanicCollector.py
│       │   ├── scoring/      # Attribution de scores de pertinence
│       │   └── publishing/   # Orchestration de la publication
│       └── Dockerfile        # Build du service syntinel-core
├── services/                 # Microservices spécialisés
│   ├── writer-agent/         # Génération de posts via CrewAI
│   └── telegram-bot/         # Interface Telegram pour interaction utilisateur
├── shared/                   # Modèles et utilitaires partagés
│   └── models/               # Modèles Pydantic communs
├── docker-compose.yml        # Orchestration de tous les conteneurs
└── .env.example              # Variables d'environnement d'exemple
```

---

## ⚙️ **Composants**

| Composant         | Rôle                                                                    |
| ----------------- | ----------------------------------------------------------------------- |
| **Syntinel-Core** | Orchestrateur principal : collecte, scoring, coordination des workflows |
| **Crawl4AI**      | (Optionnel) Service d'extraction multi-sources en HTTP                  |
| **Writer-Agent**  | Générateur de contenus stylisés via **CrewAI** (ex. ton sarcastique)    |
| **Telegram-Bot**  | Interface conviviale pour valider, éditer et publier                    |
| **PostgreSQL**    | Base de données centrale pour titres, scores, logs                      |
| **Redis**         | Cache + queue (via Redis Streams) pour ingestion et scoring             |
| **pgAdmin**       | Interface web pour administrer PostgreSQL                               |

---

## 📌 **Flux Fonctionnel**

1. **Scheduler/Orchestrator** : déclenche périodiquement le pipeline d'ingestion
2. **Collectors** : récupèrent les titres d'actu via API tierces (Cryptopanic, etc.)
3. **Pipeline ingestion** :

   * Dédoublonne via DB
   * Normalise les articles (nettoyage, format)
   * Insère en base si nouveauté
   * Pousse un événement dans un stream Redis
4. **Scoring Worker** : consomme le stream Redis pour scorer les nouveaux articles
5. **Bot Telegram** : affiche les meilleurs titres à l'utilisateur
6. **Writer-Agent** : génère un contenu original
7. **Validation utilisateur** : choix du ton, édition ou validation finale
8. **Publication automatique** : vers l'API X (Twitter)

---

## ✅ **Prérequis**

* **Docker & Docker Compose**
* **Python 3.9+** (pour dev local)
* **Clé API OpenAI** (pour Writer-Agent)
* **Token Bot Telegram** (pour l’interface utilisateur)
* **Compte X (Twitter)** + API Key pour la publication automatisée.

---

## ⚙️ **Configuration**

```bash
# Copier le fichier d’exemple d’environnement
cp .env.example .env
```

**Dans `.env`, renseigner :**

* `OPENAI_API_KEY`
* `TELEGRAM_BOT_TOKEN`
* `POSTGRES_USER`, `POSTGRES_PASSWORD`
* `X_API_KEY` (optionnel)

---

## 🚀 **Démarrage**

```bash
# Construire et lancer tous les conteneurs
docker-compose up -d
```

---

### 🔗 **Points d’accès**

| Service               | URL                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------- |
| **Syntinel-Core API** | [http://localhost:8000](http://localhost:8000)                                         |
| **Writer-Agent API**  | [http://localhost:8002](http://localhost:8002)                                         |
| **Telegram-Bot**      | Via votre App Telegram                                                                 |
| **pgAdmin**           | [http://localhost:5050](http://localhost:5050) (login: `admin@syntinel.com` / `admin`) |
| **PostgreSQL**        | `localhost:5432` (par défaut : `admin / pswd`)                                         |
| **Redis**             | `localhost:6379`                                                                       |

---

## **Développement**

* **Syntinel-Core** : orchestrateur + pipelines + ingestion workers
* **Services** : APIs spécialisées, isolables
* **Shared** : Modèles Pydantic / outils communs

---

## ✅ **Bonnes pratiques**

* ✅ Feature Sliced Design : `api.py`, `service.py`, `pipeline.py`, `collector/`
* ✅ Interface commune `BaseCollector` pour déclencher `fetch()` sur tous les modules
* ✅ Déduplication en amont + `ON CONFLICT DO UPDATE` en fallback
* ✅ Streams Redis pour ingestion asynchrone
* ✅ Wrapper `run_collector_safely()` avec logs + retry automatique
* ✅ Validation des entrées via `pydantic`
* ✅ Tests automatisés via `docker-compose.tests.yml`
* ✅ Orchestration unique via `orchestrator.py`

---

## ✨ **Roadmap**

✅ MVP ingestion → scoring → rewriting → publication
✅ Support Redis Streams
✅ Orchestrateur unique : `orchestrator.py`
🚀 Ajout de `metrics Prometheus`
🚀 Extension multi-sources : Reddit, CoinGecko
🚀 CI automatisée avec tests intégrés

---

## 🏷️ **Licence**

MIT — open source, fork et améliore à ta guise 🤝
