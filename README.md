# Observer Project

Un système modulaire basé sur des microservices pour l'extraction, le filtrage, l'évaluation, la génération et la publication de contenus d'actualité.

## Architecture

Le projet utilise une architecture hiérarchique avec un orchestrateur central (`core/observer`) et des services spécialisés (`services/`), appliquant les principes de Feature-Sliced Design (FSD) pour une meilleure organisation du code.

### Structure du projet

```
observer/
├── core/                     # Services d'orchestration centraux
│   └── observer/             # Orchestrateur principal
│       ├── src/
│       │   ├── features/     # Fonctionnalités découpées (FSD)
│       │   │   ├── crawling/ # Extraction et mise en cache des contenus
│       │   │   ├── scoring/  # Évaluation et notation des articles
│       │   │   └── publishing/ # Publication des contenus
│       │   └── shared/       # Code partagé au sein du core
│       └── Dockerfile        # Configuration Docker pour observer-core
├── services/                 # Services spécialisés
│   ├── writer-agent/         # Service de génération de contenu (CrewAI)
│   └── telegram-bot/         # Interface utilisateur Telegram
├── shared/                   # Code partagé entre tous les services
│   └── models/               # Modèles Pydantic partagés
└── docker-compose.yml        # Orchestration des conteneurs
```

## Composants

- **Observer-Core**: Service central d'orchestration, notation et stockage
- **Crawl4AI**: Service externe pour l'extraction des contenus web
- **Writer-Agent**: Service de génération de contenus via CrewAI
- **Telegram-Bot**: Interface utilisateur pour la gestion et publication
- **Redis**: Cache pour les résultats d'extraction et de notation
- **PostgreSQL**: Base de données principale
- **pgAdmin**: Interface web de gestion de PostgreSQL

## Prérequis

- Docker et Docker Compose
- Python 3.9+ (pour le développement local)
- Clé API OpenAI (pour Writer-Agent)
- Token Bot Telegram (pour Telegram-Bot)

## Configuration

1. Copiez le fichier d'exemple d'environnement:
   ```
   cp .env.example .env
   ```

2. Éditez `.env` avec vos informations:
   - `OPENAI_API_KEY`: Votre clé API OpenAI
   - `TELEGRAM_BOT_TOKEN`: Token de votre bot Telegram

## Démarrage

```bash
# Construire et démarrer tous les services
docker-compose up -d

# Vérifier l'état des services
docker-compose ps
```

### Points d'accès

- Observer-Core API: http://localhost:8000
- Crawl4AI API: http://localhost:8001
- Writer-Agent API: http://localhost:8002
- pgAdmin: http://localhost:5050 (credentials: admin@observer.com / admin)
- PostgreSQL: localhost:5432 (credentials: observer / observer_password)
- Redis: localhost:6379

## Développement

Le projet suit une architecture modulaire avec séparation des responsabilités:

1. **Core**: Orchestration et logique métier centrale
2. **Services**: Composants spécialisés avec API indépendantes
3. **Shared**: Code et modèles partagés entre services

Chaque fonctionnalité dans le core suit les principes de Feature-Sliced Design pour une meilleure isolation et maintenabilité.
