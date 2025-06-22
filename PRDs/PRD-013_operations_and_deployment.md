# PRD-013: Operations & Deployment

## Overview
Specifies the operational aspects of the application, including packaging, deployment, and maintenance. Provides the definitive Dockerfile and docker-compose.yml for the system stack.

## Technical Boundaries
- Describes the final deployable artifact and environment.
- Covers Docker, Docker Compose, and environment configuration.
- Includes backup and restore procedures.

## Success Criteria
- Developer can build and launch the stack with a single command.
- Deployed application is stable and observable.
- Backup and restore procedures are tested and reliable.

## Dependencies
| Component/PRD | Purpose |
|---------------|---------|
| PRD-003: Configuration Management | Loads config for deployment |
| PRD-002: Database & Caching Layer | Database and cache volumes |
| PRD-004: AnythingLLM Integration | Vector database container |
| PRD-005: LLM Provider Integration | LLM provider container |

## Cross-References
- Uses config.yaml and .env files from PRD-003.
- Deploys containers for AnythingLLM (PRD-004) and Ollama (PRD-005).
- Backs up SQLite and Redis data from PRD-002.

## Containerization

```dockerfile
# Stage 1: Build stage
FROM python:3.12-slim as builder
WORKDIR /app
RUN pip install poetry
COPY poetry.lock pyproject.toml ./
RUN poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction --no-ansi

# Stage 2: Final stage
FROM python:3.12-slim
WORKDIR /app
COPY --from=builder /app /app
COPY . /app
EXPOSE 8080
EXPOSE 8081
CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "main:app", "-b", "0.0.0.0:8080"]
```

## Docker Compose

```yaml
version: '3.8'
volumes:
  anythingllm_storage:
  ollama_storage:
  redis_data:
  app_data:

services:
  docs-cache:
    build: .
    container_name: docs-cache-app
    ports:
      - "8080:8080"
      - "8081:8081"
    volumes:
      - app_data:/app/data
    env_file: .env
    depends_on:
      - anythingllm
      - ollama
      - redis
    restart: unless-stopped

  anythingllm:
    image: mintplexlabs/anythingllm:latest
    container_name: anythingllm-db
    ports:
      - "3001:3001"
    volumes:
      - anythingllm_storage:/app/server/storage
      - ./anythingllm_hotdir:/app/server/hotdir
    environment:
      - STORAGE_DIR=/app/server/storage
    restart: unless-stopped

  ollama:
    image: ollama/ollama:latest
    container_name: ollama-llm
    ports:
      - "11434:11434"
    volumes:
      - ollama_storage:/root/.ollama
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    container_name: redis-cache
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    command: redis-server --appendonly yes --maxmemory 512mb --maxmemory-policy allkeys-lru
    restart: unless-stopped
```

## Backup and Restore Procedures

### Comprehensive Backup Strategy

```bash
#!/bin/bash
# backup.sh - Complete system backup including SQLite and Redis

set -e

BACKUP_DIR="${BACKUP_DIR:-/app/backups/$(date +%Y%m%d_%H%M%S)}"
mkdir -p "$BACKUP_DIR"

echo "Starting backup to $BACKUP_DIR..."

# 1. Backup SQLite database
echo "Backing up SQLite database..."
sqlite3 /app/data/docaiche.db ".backup $BACKUP_DIR/docaiche_backup.db"

# 2. Backup Redis data using BGSAVE
echo "Backing up Redis data..."
redis-cli -h redis BGSAVE
sleep 5  # Wait for background save to complete
docker cp redis:/data/dump.rdb "$BACKUP_DIR/redis_dump.rdb"

# 3. Backup AnythingLLM vectors and metadata
echo "Backing up AnythingLLM data..."
docker cp anythingllm-db:/app/server/storage "$BACKUP_DIR/anythingllm_storage"

# 4. Backup configuration files
echo "Backing up configuration..."
cp /app/config.yaml "$BACKUP_DIR/" 2>/dev/null || true
cp /app/.env "$BACKUP_DIR/env_backup" 2>/dev/null || true

# 5. Create backup manifest
echo "Creating backup manifest..."
cat > "$BACKUP_DIR/backup_manifest.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "version": "1.0.0",
  "components": {
    "sqlite": "docaiche_backup.db",
    "redis": "redis_dump.rdb",
    "anythingllm": "anythingllm_storage/",
    "config": "config.yaml"
  },
  "size_mb": $(du -sm "$BACKUP_DIR" | cut -f1)
}
EOF

echo "Backup completed successfully: $BACKUP_DIR"
```

### Restore Procedures

```bash
#!/bin/bash
# restore.sh - Complete system restore

BACKUP_DIR="$1"
if [[ -z "$BACKUP_DIR" ]]; then
    echo "Usage: $0 <backup_directory>"
    exit 1
fi

echo "Restoring from $BACKUP_DIR..."

# 1. Stop services
docker-compose down

# 2. Restore SQLite
echo "Restoring SQLite database..."
cp "$BACKUP_DIR/docaiche_backup.db" /app/data/docaiche.db

# 3. Restore Redis
echo "Restoring Redis data..."
docker-compose up -d redis
sleep 5
docker cp "$BACKUP_DIR/redis_dump.rdb" redis:/data/dump.rdb
docker-compose restart redis

# 4. Restore AnythingLLM
echo "Restoring AnythingLLM storage..."
docker cp "$BACKUP_DIR/anythingllm_storage" anythingllm-db:/app/server/

# 5. Restore configuration
cp "$BACKUP_DIR/config.yaml" /app/ 2>/dev/null || true

# 6. Start all services
docker-compose up -d

echo "Restore completed successfully"
```

## Implementation Tasks

| Task ID | Description |
|---------|-------------|
| OP-001  | Create multi-stage Dockerfile |
| OP-002  | Create docker-compose.yml for full stack with Redis service |
| OP-003  | Create .env.example file |
| OP-004  | Write and test comprehensive backup.sh script including Redis |
| OP-005  | Write and test restore.sh script for all components |
| OP-006  | Create Makefile for operational commands |
| OP-007  | Document Ollama model setup process |
| OP-008  | Write comprehensive README.md |
| OP-009  | Implement automated backup scheduling via cron |
| OP-010  | Create backup retention policy and cleanup scripts |

## Integration Contracts
- Uses standard Docker and Compose features.
- Volumes for persistent data.
- Environment variables for configuration.

## Summary Tables

### Services Table

| Service Name   | Purpose                         | Depends On           |
|----------------|---------------------------------|----------------------|
| docs-cache     | Main Python application         | anythingllm, ollama, redis |
| anythingllm    | Vector database                 | -                    |
| ollama         | LLM provider                    | -                    |
| redis          | Cache and session storage       | -                    |

### Implementation Tasks Table
(see Implementation Tasks above)

---