FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies including Node.js for Context7
RUN apt-get update && apt-get install -y \
    curl \
    ca-certificates \
    gnupg \
    && mkdir -p /etc/apt/keyrings \
    && curl -fsSL https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key | gpg --dearmor -o /etc/apt/keyrings/nodesource.gpg \
    && echo "deb [signed-by=/etc/apt/keyrings/nodesource.gpg] https://deb.nodesource.com/node_20.x nodistro main" | tee /etc/apt/sources.list.d/nodesource.list \
    && apt-get update \
    && apt-get install -y nodejs \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies (includes AI logging dependencies: networkx for correlation graphs)
RUN pip install --no-cache-dir -r requirements.txt

# Copy alembic configuration
COPY alembic.ini .
COPY alembic/ ./alembic/

# Copy the entire source code
COPY src/ ./src/

# Copy workspace initialization script
COPY init-weaviate-workspace.py .

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && chown -R app:app /app

# Expose port
EXPOSE 4000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Default command (can be overridden in docker-compose)
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "4000"]