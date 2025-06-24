# Portainer One-Click Deployment Guide

This project supports ultra-simple deployment via Portainer using a single `docker-compose.yml` in the repository root.

## Steps

1. **Open Portainer** and go to **Stacks**.
2. Click **Add Stack**.
3. Enter a name (e.g., `docaiche`).
4. In the **Git repository** section, enter:

   ```
   https://github.com/user/docaiche
   ```

5. Portainer will auto-detect `docker-compose.yml` in the root.
6. In the **Environment variables** section, review and set values as needed. All required variables are in `.env.example`.
7. Click **Deploy the stack**.

## Notes

- **No external files or secrets required**. All configuration is via environment variables.
- **Volumes**: Data is persisted using named volumes managed by Portainer.
- **Health checks**: All services include health checks for Portainer monitoring.
- **Custom Dockerfiles**: You must provide minimal `Dockerfile.api`, `Dockerfile.webui`, `Dockerfile.anythingllm`, and `Dockerfile.ollama` in the project root for builds to succeed.
- **Public images**: Redis and SQLite use official public images.
- **Single network**: All services communicate on the `docaiche` network.

## Troubleshooting

- If a service fails to start, check the Portainer logs for build errors or missing Dockerfiles.
- Ensure all environment variables are set in Portainer before deploying.
- For persistent data, Portainer manages named volumes automatically.