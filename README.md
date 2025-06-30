# 🚀 **Syntinel Project**

**Un système modulaire de microservices pour scruter l’actualité crypto, filtrer, scorer, générer et publier du contenu différencié automatiquement, tout en gardant un contrôle humain final.**

---

## 🗂️ **Architecture**

Ce projet repose sur une **architecture orientée microservices**, orchestrée par un cœur central (`core/syntinel`) et enrichie de services spécialisés (`services/`).
Chaque brique est isolée selon le principe **Feature-Sliced Design (FSD)** pour une organisation claire et évolutive.

---

### 📌 **Structure du projet**

```
syntinel/
├── core/                     # Orchestrateur central
│   └── syntinel/
│       ├── modules/          # Modules métiers (FSD)
│       │   ├── crawling/     # Extraction et mise en cache des titres crypto
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
| **Crawl4AI**      | (Optionnel) Service dédié d’extraction rapide multi-sources             |
| **Writer-Agent**  | Générateur de contenus stylisés via **CrewAI** (ex. ton sarcastique)    |
| **Telegram-Bot**  | Interface conviviale pour valider, éditer et publier                    |
| **PostgreSQL**    | Base de données centrale pour titres, scores, logs                      |
| **Redis**         | Cache et queue pour accélérer le crawl et la notation                   |
| **pgAdmin**       | Interface web pour administrer PostgreSQL                               |

---

## 📌 **Flux Fonctionnel**

1️⃣ **Crawler** : Explore plusieurs sites crypto, extrait uniquement les titres.
2️⃣ **Scoring** : Évalue chaque titre selon pertinence et popularité pour prioriser les news chaudes.
3️⃣ **Bot Telegram** : Propose à l’utilisateur une sélection triée (ex. Top 3).
4️⃣ **Writer-Agent (CrewAI)** : Génère une version du titre au ton sarcastique/mème-friendly.
5️⃣ **Validation utilisateur** : Via Telegram, le créateur peut modifier ou demander une autre version.
6️⃣ **Publication** : Après validation, le tweet est publié automatiquement via l’API X.

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

* `OPENAI_API_KEY` — Votre clé API OpenAI
* `TELEGRAM_BOT_TOKEN` — Token de votre Bot Telegram
* `POSTGRES_USER`, `POSTGRES_PASSWORD` — Credentials DB si custom
* `X_API_KEY` (optionnel) — Pour l’intégration Twitter

---

## 🚀 **Démarrage**

```bash
# Construire et lancer tous les conteneurs en arrière-plan
docker-compose up -d

# Vérifier l’état des services
docker-compose ps
```

---

### 🔗 **Points d’accès**

| Service               | URL                                                                                    |
| --------------------- | -------------------------------------------------------------------------------------- |
| **Syntinel-Core API** | [http://localhost:8000](http://localhost:8000)                                         |
| **Writer-Agent API**  | [http://localhost:8002](http://localhost:8002)                                         |
| **Telegram-Bot**      | Via votre App Telegram                                                                 |
| **pgAdmin**           | [http://localhost:5050](http://localhost:5050) (login: `admin@syntinel.com` / `admin`) |
| **PostgreSQL**        | `localhost:5432` (par défaut : `admin / pswd`)                         |
| **Redis**             | `localhost:6379`                                                                       |

---

## **Développement**

* **Syntinel-Core** : Gère la logique métier et l'orchestration globale.
* **Services** : Gèrent des tâches spécialisées via APIs isolées.
* **Shared** : Fournit des modèles et outils communs pour assurer la cohérence entre modules.

Le design **FSD** garantit une isolation forte par fonctionnalité, facilitant le test unitaire, l’évolution incrémentale et le déploiement CI/CD.

---

## ✅ **Bonnes pratiques**

✔️ **Feature Sliced Design** pour chaque `modules/` :

* `api.py` : Routes API (ex. FastAPI)
* `service.py` : Logique pure Python, testable sans serveur

✔️ **Queue ou cache Redis** pour fiabiliser crawl et scoring.

✔️ **CrewAI paramétrable** pour personnaliser le ton du contenu (sérieux, sarcastique, troll).

✔️ **Logs Telegram** pour tracer les interactions et valider l’engagement.

---

## ✨ **Roadmap**

✅ MVP avec crawl + scoring + rewriting + validation
🚀 Ajout d’autres sources (Reddit, CoinGecko)
🚀 Mode « planification » pour poster à heure fixe
🚀 Dashboard web pour historique et métriques

---

## 🏷️ **Licence**

MIT — open source, fork et améliore à ta guise 🤝
