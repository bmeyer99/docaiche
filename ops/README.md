# Operations & Deployment Scaffolding (PRD-013)

This directory contains the foundational scaffolding for production deployment, operations, and maintenance of the AI Documentation Cache System.

> **Note:** Portainer is the recommended deployment method. Environment variables for containerized deployments are managed directly in the Portainer UI or via shell variables for Docker Compose. The `env/` directory and `.env` files are only used for local development and testing.

## Structure

- [`docker/`](./docker): Dockerfiles, Compose, and service configs
- [`ci/`](./ci): CI/CD pipeline templates and scripts
- [`monitoring/`](./monitoring): Monitoring, logging, and alerting configs
- [`secrets/`](./secrets): Secrets management templates (never commit real secrets)
- [`scripts/`](./scripts): Operational scripts (backup, restore, health checks, etc.)
- [`docs/`](./docs): Operational procedures and runbooks

## Deployment Strategy

- **Portainer (Recommended):** Deploy and manage stacks via the Portainer UI. Set all environment variables in the Portainer web interface. No `.env` or `env/` files are used for containerized deployment.
- **Docker Compose:** For CLI-based deployments, set environment variables in your shell or use a `docker-compose.override.yml` file. Do not use `.env` or `env/` files for containerized services.
- **Local Development:** Use `.env` files (from `env/` or `.env.example`) for local runs outside containers.

## Implementation TODOs

- Complete all TODOs in config and script files
- Integrate with all PRD-001 to PRD-012 components
- Validate all configs in staging before production