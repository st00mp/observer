# 🛰️ Syntinel Project

**A modular microservices system for monitoring news, filtering, scoring, generating and publishing differentiated content — while keeping a final human-in-the-loop.**

> Note: This project is currently in progress. Only the ingestion pipeline is functional at this stage. See the Project Status section for details.

---

## 📂️ Architecture

This project is built on a **microservices architecture**, orchestrated by a central core (`core/syntinel`) and extended with specialized services (`services/`).

Each component follows the **Feature-Sliced Design (FSD)** principle for clarity and scalability.

---

## 📌 Project Structure

```
syntinel/
├── core/                     # Central orchestrator
│   └── syntinel/
│       ├── orchestrator.py   # Entry point for executing business pipelines
│       ├── db/              # Database module
│       │   ├── session.py    # DB connection, engine and session configuration
│       │   ├── models/       # Database models
│       │   │   ├── article.py
│       │   │   └── draft.py
│       │   └── __init__.py   # Re-exports for easy imports
│       ├── modules/          # Business modules (FSD)
│       │   ├── ingestion/    # Extraction, deduplication, normalization, Redis
│       │   │   ├── pipeline.py
│       │   │   └── collector/
│       │   │       ├── base.py
│       │   │       └── cryptopanic_collector.py
│       │   ├── scoring/      # Relevance scoring logic
│       │   └── publishing/   # Publishing orchestration
│       └── Dockerfile        # Build for syntinel-core service
├── services/                 # Specialized microservices
│   ├── writer-agent/         # Content generation via CrewAI
│   └── telegram-bot/         # Telegram interface for user interaction
├── docker-compose.yml        # Container orchestration
└── .env.example              # Example environment variables
```

---

## ⚙️ Components

| Component       | Role                                                                 |
|----------------|----------------------------------------------------------------------|
| Syntinel-Core   | Main orchestrator: ingestion, scoring, workflow coordination         |
| Crawl4AI        | (Optional) Multi-source HTTP extraction service                      |
| Writer-Agent    | Stylized content generator using CrewAI (e.g. sarcastic tone)        |
| Telegram-Bot    | User-friendly interface to validate, edit and publish content        |
| PostgreSQL      | Central database for headlines, scores, and logs                     |
| Redis           | Cache + queue system (Redis Streams) for ingestion and scoring       |
| pgAdmin         | Web interface for PostgreSQL administration                          |

---

## 📌 Functional Flow

1. Scheduler / Orchestrator triggers the ingestion pipeline periodically  
2. Collectors fetch headlines from third-party APIs (e.g. Cryptopanic)  
3. Ingestion Pipeline:
   - Deduplicates using the DB  
   - Normalizes articles (cleaning, formatting)  
   - Inserts into DB if new  
   - Pushes event to Redis stream  
4. Scoring Worker consumes Redis stream and applies relevance scoring  
5. Telegram Bot displays top headlines to the user  
6. Writer-Agent generates original content  
7. User Validation: tone selection, editing, final approval  
8. Automatic Publishing: pushes to X (Twitter) API  

---

## ✅ Requirements

- Docker & Docker Compose  
- Python 3.9+ (for local development)  
- OpenAI API Key (for Writer-Agent)  
- Telegram Bot Token (for user interaction)  
- X (Twitter) account + API Key (for automated publishing)  

---

## ⚙️ Configuration

```bash
# Copy the environment file
cp .env.example .env
```

Fill in the .env file with:
	•	OPENAI_API_KEY
	•	TELEGRAM_BOT_TOKEN
	•	POSTGRES_USER, POSTGRES_PASSWORD
	•	X_API_KEY (optional)

---

## 🚀 Startup

```bash
# Build and launch all containers
docker-compose up -d
```


---

## 🔗 Service Access

| Service           | URL / Access Info                                         |
|-------------------|-----------------------------------------------------------|
| Syntinel-Core API | http://localhost:8000                                     |
| Writer-Agent API  | http://localhost:8002                                     |
| Telegram-Bot      | Available via your Telegram app                           |
| pgAdmin           | http://localhost:5050 (login: admin@syntinel.com / admin) |
| PostgreSQL        | localhost:5432 (default: admin / pswd)                    |
| Redis             | localhost:6379                                            |


---

## 🛠 Development
	•	Syntinel-Core: orchestrator, pipelines, ingestion workers
	•	Services: isolated, pluggable APIs
	•	Shared: Pydantic models and common utilities

---

## ✅ Best Practices
	•	✅ Feature-Sliced Design: api.py, service.py, pipeline.py, collector/
	•	✅ Shared interface BaseCollector to trigger fetch() across modules
	•	✅ Pre-insert deduplication + ON CONFLICT DO UPDATE fallback
	•	✅ Redis Streams for async ingestion
	•	✅ run_collector_safely() wrapper with logs + automatic retry
	•	✅ Input validation via Pydantic
	•	✅ Automated tests with docker-compose.tests.yml
	•	✅ Centralized orchestration via orchestrator.py

---

## 📌 Project Status

This project is a work in progress. Current state:

```
•	✅ Ingestion pipeline: functional (collector, normalization, deduplication, storage)
•	🔄 Scoring module: in progress
•	🚧 Writer-Agent + Telegram interface: not yet implemented
•	🚧 Publishing module: not yet implemented
```

I welcome contributions and suggestions — feel free to fork, clone, or reach out.

## 🚀 Usage

### Running the Orchestrator

The orchestrator is the main entry point to run the ingestion pipeline. It provides several options for customization:

```bash
# Standard execution (ingestion only)
python -m core.orchestrator

# With JSON export (auto-generated filename)
python -m core.orchestrator --export-json

# With JSON export and custom filename
python -m core.orchestrator --export-json --export-path custom_export.json
```

#### CLI Options

| Option | Description |
|--------|-------------|
| `--export-json` | Enable JSON export of collected articles |
| `--export-path PATH` | Specify a custom path for the JSON export file |

The JSON export contains both raw article data from collectors and normalized data used for database storage.

---

## 🏷️ License

MIT — Open source, feel free to fork and improve 🤝
