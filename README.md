# AI Documentation Cache System

## Project Overview

The AI Documentation Cache System is a production-ready, microservices-based platform that delivers instant, context-aware documentation search and enrichment for developers. It leverages AI-powered search, semantic vector databases, automated content ingestion, and continuous knowledge enrichment to provide authoritative, up-to-date answers with minimal cognitive load.

**Key Capabilities:**
- AI-powered semantic search with LLM evaluation and enrichment
- Automated ingestion from GitHub, web, and APIs
- Advanced content processing, chunking, and quality assessment
- Feedback-driven continuous improvement
- Ultra-simple deployment via Portainer or Docker Compose

---

## Quick Start (Portainer One-Click Deployment)

**Deploy the full system in minutes:**

1. **Open Portainer** and select "Add Stack".
2. **Paste the GitHub repo URL** or point to your fork.
3. **Portainer auto-detects `docker-compose.yml`** and prompts for environment variables.
4. **Configure variables** (or use defaults) in the UI.
5. **Click "Deploy the stack"** — all services launch and are managed from Portainer.

**No CLI required.** All configuration and management is handled via the Portainer web UI.

---

## Features

- **Core API Foundation**: FastAPI with secure, versioned REST endpoints, CORS, and health checks
- **Database & Caching**: Persistent SQLite for metadata, Redis for high-speed caching
- **Configuration Management**: Hierarchical config (env, YAML, DB) with runtime validation and hot-reload
- **AnythingLLM Integration**: Vector database for semantic search and document storage
- **LLM Providers**: Ollama and OpenAI integration with automatic failover and prompt templating
- **GitHub Client**: Authenticated, rate-limited repo ingestion and file discovery
- **Web Scraping**: Intelligent, robots.txt-compliant content extraction from documentation sites
- **Content Processing**: Markdown normalization, chunking, metadata extraction, quality scoring
- **Search Orchestration**: Multi-workspace, AI-evaluated search with enrichment triggers and caching
- **Knowledge Enrichment**: Automated background enrichment, tagging, and deduplication
- **Response Generation**: Template-based, context-aware answer synthesis
- **Web UI Service**: FastAPI-based admin/configuration interface with dashboard and content management
- **Operations & Deployment**: Docker Compose and Portainer-ready, with backup/restore and health checks

---

## Architecture

**Microservices Overview:**
- **API Service**: FastAPI, exposes all REST endpoints
- **Web UI**: FastAPI + Jinja2, admin/configuration dashboard
- **AnythingLLM**: Vector DB for semantic search
- **Ollama**: Local LLM provider (optional, can use OpenAI)
- **Redis**: High-speed cache for queries, sessions, and rate limiting
- **SQLite**: Persistent metadata and content storage

**Component Diagram:**
```
[User/Web UI] <--REST--> [API Service] <--gRPC/HTTP--> [AnythingLLM] [Ollama/OpenAI]
         |                        |                        |
         |                        |                        |
         |                        |                        |
         +----> [Redis] <---------+----> [SQLite] <--------+
```

**All services are containerized and orchestrated via Docker Compose or Portainer.**

---

## Deployment Options

### 1. Portainer (Recommended)

- **Open Portainer**, add a new stack, and provide the GitHub repo URL.
- Configure environment variables in the Portainer UI.
- Click "Deploy the stack" — all services are built, started, and managed from Portainer.

### 2. Docker Compose

```bash
git clone https://github.com/your-org/ai-docs-cache.git
cd ai-docs-cache
cp .env.example .env   # Edit as needed
docker-compose up --build -d
```
- All services (API, Web UI, AnythingLLM, Ollama, Redis, SQLite) are started and networked automatically.

### 3. Local Development

```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn src.main:app --reload --host 0.0.0.0 --port 8080
```
- For advanced development, debugging, and testing.

---

## Configuration

All configuration is managed via environment variables, `.env`, and `config.yaml`. See `.env.example` for all options.

**Core Environment Variables:**

| Variable                       | Description                                 | Default                |
|---------------------------------|---------------------------------------------|------------------------|
| APP_ENV                        | Application environment                     | production             |
| APP_PORT                       | API service port                            | 8000                   |
| LOG_LEVEL                      | Logging level                               | info                   |
| DATABASE_URL                   | SQLite DB URL                               | sqlite:////data/app.db |
| REDIS_URL                      | Redis connection URL                        | redis://redis:6379/0   |
| ANYTHINGLLM_URL                | AnythingLLM API endpoint                    | http://anythingllm:3001|
| OLLAMA_URL                     | Ollama API endpoint                         | http://ollama:11434    |
| API_AUTH_SECRET                | API authentication secret                   | changeme               |
| API_JWT_SECRET                 | JWT signing secret                          | changeme               |
| WEBUI_SESSION_SECRET           | Web UI session secret                       | changeme               |
| ANYTHINGLLM_API_KEY            | AnythingLLM API key                         | changeme               |
| OLLAMA_MODEL                   | Ollama model name                           | llama3                 |
| OLLAMA_API_KEY                 | Ollama API key                              | changeme               |
| OPENAI_ENABLED                 | Enable OpenAI provider                      | false                  |
| OPENAI_API_KEY                 | OpenAI API key                              |                        |
| OPENAI_MODEL                   | OpenAI model name                           |                        |
| ENVIRONMENT                    | System environment                          | production             |
| DEBUG                          | Enable debug mode                           | false                  |

**See `.env.example` and [PRD-003_Config_Mgmt_System.md](PRDs/PRD-003_Config_Mgmt_System.md) for full details and advanced options.**

---

## API Documentation

- **Swagger UI**: `/docs`
- **ReDoc**: `/redoc`
- **OpenAPI JSON**: `/openapi.json`

**Key Endpoints:**
- `/api/v1/search` — AI-powered documentation search
- `/api/v1/feedback` — Submit explicit feedback
- `/api/v1/signals` — Submit implicit usage signals
- `/api/v1/config` — Get/set system configuration
- `/api/v1/health` — System health check
- `/api/v1/stats` — Usage and performance metrics
- `/api/v1/collections` — List documentation collections
- `/api/v1/admin/search-content` — Admin content search
- `/api/v1/content/{content_id}` — Flag content for removal

**See OpenAPI docs for all endpoints, schemas, and error formats.**

---

## Monitoring & Operations

- **Health Checks**: `/health` endpoint for all services (API, Web UI, AnythingLLM, Ollama, Redis)
- **Structured Logging**: JSON logs with correlation IDs for all requests
- **Metrics**: Usage, performance, and error metrics exposed via `/stats`
- **Backup/Restore**: Use `backup.sh` and `restore.sh` scripts for full system backup and recovery (see [PRD-013](PRDs/PRD-013_operations_and_deployment.md))
- **Troubleshooting**: All errors are logged with trace IDs; see logs via Portainer or `docker-compose logs`

---

## Development

- **Testing**:  
  ```bash
  pytest tests/ -v
  ```
- **Linting/Formatting**:  
  ```bash
  black src/
  isort src/
  flake8 src/
  mypy src/
  ```
- **Type Checking**:  
  ```bash
  mypy src/
  ```
- **Security Scanning**:  
  ```bash
  bandit -r src/
  ```
- **Contributing**:  
  - Fork the repo, create a feature branch, submit PRs with clear descriptions.
  - All code must include type hints, docstrings, and tests.

---

## System Requirements

- **CPU**: 4+ cores recommended
- **RAM**: 8GB+ (16GB+ for large LLMs)
- **Disk**: 10GB+ free (persistent volumes for DB, Redis, AnythingLLM, Ollama)
- **OS**: Linux (x86_64), Docker Engine 20.10+, Portainer (optional)
- **Network**: Outbound HTTPS for GitHub, OpenAI (if enabled)

---

## Support & Documentation

- **Full PRD Suite**: See `PRDs/` for all product requirements and architecture docs
- **Deployment Guide**: See `DEPLOYMENT_GUIDE.md`
- **Backup/Restore**: See `scripts/backup.sh` and `scripts/restore.sh`
- **Configuration Reference**: See `.env.example` and `config.yaml`
- **API Reference**: Auto-generated OpenAPI docs at `/docs`
- **Issue Tracker**: Use GitHub Issues for bug reports and feature requests

---

**This README reflects the complete, production-ready state of the AI Documentation Cache System. All features are implemented and ready for deployment.**