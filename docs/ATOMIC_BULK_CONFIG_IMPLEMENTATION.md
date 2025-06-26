# Persistent Task Queue Options for Config Change Operations

## Background

Current config updates are synchronous or use FastAPI background tasks, which are not persistent. To ensure config changes are not lost on process restarts, a persistent task queue is required.

---

## Option 1: Celery

**Overview:**  
Celery is a widely used distributed task queue for Python. It supports multiple brokers (Redis, RabbitMQ) and provides robust persistence and retry mechanisms.

**Pros:**
- Mature, well-documented, and widely adopted.
- Supports persistent brokers (Redis, RabbitMQ).
- Automatic retry and result backend support.
- Good Docker compatibility (official images, easy orchestration).
- Flexible for future scaling and complex workflows.

**Cons:**
- More setup overhead (requires broker and optional result backend).
- More concepts to learn (tasks, workers, brokers).
- Overkill for very simple use cases.

---

## Option 2: RQ (Redis Queue)

**Overview:**  
RQ is a simple Python library for queueing jobs and processing them in the background with workers. It uses Redis as its only broker.

**Pros:**
- Very simple and easy to understand for juniors.
- Minimal setup (just Redis, no extra services).
- Good Docker compatibility.
- Sufficient for basic persistent background tasks.

**Cons:**
- Fewer features than Celery (no built-in periodic tasks, less flexible retries).
- Only supports Redis as a broker.
- Less suitable for complex workflows or scaling needs.

---

## Recommendation

**Use RQ (Redis Queue) for persistent config change tasks.**

- RQ is easier for junior developers to set up and maintain.
- It provides persistence via Redis and is simple to integrate.
- Docker support is straightforward.

---

## Config Input Validation & Sanitization Requirements

**All config input (keys and values) must be strictly validated and sanitized before being accepted.**

### Key Validation Rules
- Keys must use dot notation (e.g., `app.debug`).
- Allowed characters: letters, numbers, underscores, dots (no spaces or special chars).
- Length: 3–64 characters.
- Must match regex: `^[a-zA-Z0-9_.]{3,64}$`.

### Value Validation Rules
- Type must match expected config (string, int, bool, etc.).
- For strings: max 256 chars, no control chars, no script tags or dangerous content.
- For numbers: must be within safe range for the config (e.g., port 1024–65535).
- For booleans: only `true` or `false` (case-insensitive).
- For URLs: must start with `http://` or `https://` and be a valid URL.
- All values must be sanitized to remove leading/trailing whitespace.

### General Security
- Reject any input containing `<script>`, SQL keywords (`DROP`, `DELETE`, etc.), or suspicious patterns.
- Log all validation failures for audit.

---

## Test Cases for Invalid/Malicious Input

| Case | Input | Expected Result |
|------|-------|----------------|
| Invalid key chars | `app$debug` | Rejected, 400 error |
| Key too short | `a.b` | Rejected, 400 error |
| Key too long | `[65+ chars]` | Rejected, 400 error |
| Value too long | `[257+ chars string]` | Rejected, 400 error |
| Value with `<script>` | `"<script>alert(1)</script>"` | Rejected, 400 error |
| Invalid int | `"app.api_port": "notanumber"` | Rejected, 400 error |
| Out-of-range int | `"app.api_port": 999999` | Rejected, 400 error |
| Invalid bool | `"app.debug": "maybe"` | Rejected, 400 error |
| Invalid URL | `"anythingllm.endpoint": "ftp://bad"` | Rejected, 400 error |
| SQL injection | `"DROP TABLE users;"` | Rejected, 400 error |

---

## Instructions for Junior Developers

- Add/extend validation logic in [`src/core/config/validation.py`](src/core/config/validation.py:1) and config models.
- Ensure endpoints in [`src/api/v1/config_endpoints.py`](src/api/v1/config_endpoints.py:1) call validation utilities for all input.
- Write unit tests for all above cases in `tests/validation/` or `tests/test_bulk_config_atomic.py`.
- Document any new validation logic and test cases here.
---

## Minimal Setup & Integration Plan

### 1. Identify FastAPI Background Tasks for Config Changes

- Locate all uses of `BackgroundTasks` for config changes in [`src/api/v1/config_endpoints.py`](src/api/v1/config_endpoints.py:1).
- Example: The `update_configuration` endpoint uses `background_tasks.add_task(update_config)` for config updates.

### 2. Add Dependencies

Add to `requirements.txt`:
```
rq
redis
```

Install with:
```bash
pip install rq redis
```

### 3. Docker Compose

Add a Redis service to your `docker-compose.yml`:
```yaml
redis:
  image: redis:7
  ports:
    - "6379:6379"
  restart: always
```

### 4. Refactor Background Task Calls

- Replace `background_tasks.add_task(...)` with RQ job enqueue:
  ```python
  from rq import Queue
  from redis import Redis

  redis_conn = Redis(host="redis", port=6379)
  q = Queue("default", connection=redis_conn)
  q.enqueue(config_update_function, key, value, user)
  ```
- Move config update logic into standalone functions if not already.

### 5. Run RQ Worker

- Start an RQ worker process:
  ```bash
  rq worker default --url redis://redis:6379/0
  ```
- Add an RQ worker service to `docker-compose.yml` if desired.

### 6. Test Task Persistence

- Submit a config change and restart the API or worker.
- Confirm the job is not lost and is processed after restart.

### 7. Operational Notes

- Monitor the Redis container for health.
- Ensure the RQ worker is running as a separate process/container.
- Document the queue usage and worker management for the team.

---

---

## DevOps Review: `system_config` Table Schema & Migrations

- All required fields for `system_config` are present in [`src/database/schema.py`](src/database/schema.py:99):
  - `config_key` (TEXT, PRIMARY KEY, NOT NULL)
  - `config_value` (TEXT, NOT NULL)
  - `is_active` (BOOLEAN, DEFAULT TRUE)
  - `created_at` (INTEGER, DEFAULT current timestamp)
  - `updated_at` (INTEGER, DEFAULT current timestamp)
- All constraints (PK, NOT NULL, defaults) are correctly applied.

**Action Required:**  
No Alembic migration scripts exist for `system_config` or other tables.  
- Junior developers must add Alembic migration scripts to track and manage schema changes.
- This ensures database changes are reproducible and production-safe.

**Next Steps for Juniors:**
1. Initialize Alembic versioning if not already done.
2. Create a migration script reflecting the current `system_config` schema.
3. Use `alembic revision --autogenerate -m "Add system_config table"` and review the generated script.
4. Apply the migration with `alembic upgrade head`.
5. Commit migration scripts to version control.
**Next Steps:**
- Replace all FastAPI background tasks for config changes with RQ jobs as described.
- Update this documentation with code examples after migration.