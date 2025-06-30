# MCP Deployment Guide

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start](#quick-start)
3. [Configuration](#configuration)
4. [Deployment Options](#deployment-options)
5. [Security Hardening](#security-hardening)
6. [Monitoring Setup](#monitoring-setup)
7. [Troubleshooting](#troubleshooting)
8. [Production Checklist](#production-checklist)

## Prerequisites

### System Requirements

- **Python**: 3.8 or higher
- **Memory**: Minimum 2GB RAM (4GB recommended)
- **Storage**: 10GB for application and cache
- **OS**: Linux (Ubuntu 20.04+ recommended), macOS, or Windows with WSL2

### Dependencies

```bash
# Core dependencies
pip install fastapi uvicorn httpx
pip install prometheus-client structlog

# Optional dependencies (production)
pip install gunicorn redis psycopg2-binary
```

## Quick Start

### 1. Clone and Setup

```bash
# Clone repository
git clone https://github.com/your-org/docaiche.git
cd docaiche

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Basic Configuration

Create `.env` file:

```bash
# Server Configuration
MCP_HOST=0.0.0.0
MCP_PORT=8000
MCP_WORKERS=4

# Security
MCP_SECRET_KEY=your-secret-key-here
MCP_JWT_ALGORITHM=RS256
MCP_CORS_ORIGINS=["https://app.example.com"]

# Database (optional)
DATABASE_URL=postgresql://user:pass@localhost/docaiche

# Redis Cache (optional)
REDIS_URL=redis://localhost:6379/0
```

### 3. Run Development Server

```bash
# Run with uvicorn (development)
uvicorn src.mcp.main:app --reload --host 0.0.0.0 --port 8000

# Or use the provided script
python -m src.mcp.main
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|------------|---------|----------|
| `MCP_HOST` | Server bind address | `0.0.0.0` | No |
| `MCP_PORT` | Server port | `8000` | No |
| `MCP_WORKERS` | Number of worker processes | `4` | No |
| `MCP_SECRET_KEY` | Secret key for signing | - | Yes |
| `MCP_JWT_ALGORITHM` | JWT signing algorithm | `RS256` | No |
| `MCP_JWT_PUBLIC_KEY_PATH` | Path to RSA public key | `./keys/public.pem` | No |
| `MCP_JWT_PRIVATE_KEY_PATH` | Path to RSA private key | `./keys/private.pem` | No |
| `MCP_CORS_ORIGINS` | Allowed CORS origins | `[]` | No |
| `MCP_RATE_LIMIT_ENABLED` | Enable rate limiting | `true` | No |
| `MCP_RATE_LIMIT_REQUESTS` | Requests per minute | `100` | No |
| `DATABASE_URL` | PostgreSQL connection URL | - | No |
| `REDIS_URL` | Redis connection URL | - | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `LOG_FORMAT` | Log format (json/text) | `json` | No |

### Configuration File

Create `config/mcp.yaml`:

```yaml
server:
  host: 0.0.0.0
  port: 8000
  workers: 4
  keepalive: 75

security:
  authentication:
    required: true
    token_expiry: 3600
    refresh_enabled: true
  
  rate_limiting:
    enabled: true
    default_limit: 100
    burst_size: 20
    
  cors:
    origins:
      - https://app.example.com
    allow_credentials: true
    max_age: 86400

transport:
  http:
    compression: gzip
    timeout: 30
    max_connections: 100
  
  websocket:
    enabled: true
    heartbeat_interval: 30
    max_message_size: 1048576

cache:
  provider: redis
  ttl: 3600
  max_size: 1000
  eviction_policy: lru

monitoring:
  metrics:
    enabled: true
    endpoint: /metrics
  
  health:
    enabled: true
    endpoint: /health
    interval: 30
  
  tracing:
    enabled: false
    jaeger_endpoint: http://localhost:14268/api/traces
```

## Deployment Options

### Docker Deployment

#### 1. Build Image

```dockerfile
# Dockerfile is provided in the repository
docker build -t docaiche-mcp:latest .
```

#### 2. Run Container

```bash
# Run with environment file
docker run -d \
  --name docaiche-mcp \
  -p 8000:8000 \
  --env-file .env \
  -v $(pwd)/config:/app/config \
  -v $(pwd)/logs:/app/logs \
  docaiche-mcp:latest
```

#### 3. Docker Compose

```yaml
# docker-compose.yml
version: '3.8'

services:
  mcp:
    build: .
    ports:
      - "8000:8000"
    environment:
      - MCP_SECRET_KEY=${MCP_SECRET_KEY}
      - DATABASE_URL=postgresql://postgres:password@db:5432/docaiche
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./config:/app/config
      - ./logs:/app/logs

  db:
    image: postgres:14
    environment:
      - POSTGRES_DB=docaiche
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data

volumes:
  postgres_data:
  redis_data:
```

### Kubernetes Deployment

#### 1. ConfigMap

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: mcp-config
data:
  mcp.yaml: |
    server:
      host: 0.0.0.0
      port: 8000
      workers: 4
    # ... rest of config
```

#### 2. Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: docaiche-mcp
spec:
  replicas: 3
  selector:
    matchLabels:
      app: docaiche-mcp
  template:
    metadata:
      labels:
        app: docaiche-mcp
    spec:
      containers:
      - name: mcp
        image: docaiche-mcp:latest
        ports:
        - containerPort: 8000
        env:
        - name: MCP_SECRET_KEY
          valueFrom:
            secretKeyRef:
              name: mcp-secrets
              key: secret-key
        volumeMounts:
        - name: config
          mountPath: /app/config
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /ready
            port: 8000
          initialDelaySeconds: 5
          periodSeconds: 5
        resources:
          requests:
            memory: "256Mi"
            cpu: "250m"
          limits:
            memory: "512Mi"
            cpu: "500m"
      volumes:
      - name: config
        configMap:
          name: mcp-config
```

#### 3. Service

```yaml
apiVersion: v1
kind: Service
metadata:
  name: docaiche-mcp
spec:
  selector:
    app: docaiche-mcp
  ports:
  - port: 80
    targetPort: 8000
  type: LoadBalancer
```

### Production Server (Gunicorn)

```bash
# gunicorn_config.py
bind = "0.0.0.0:8000"
workers = 4
worker_class = "uvicorn.workers.UvicornWorker"
worker_connections = 1000
keepalive = 5
errorlog = "-"
accesslog = "-"
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Run with gunicorn
gunicorn src.mcp.main:app -c gunicorn_config.py
```

## Security Hardening

### 1. Generate RSA Keys

```bash
# Generate private key
openssl genrsa -out keys/private.pem 2048

# Generate public key
openssl rsa -in keys/private.pem -pubout -out keys/public.pem

# Set permissions
chmod 600 keys/private.pem
chmod 644 keys/public.pem
```

### 2. TLS Configuration

```nginx
# nginx.conf
server {
    listen 443 ssl http2;
    server_name mcp.docaiche.example.com;

    ssl_certificate /etc/ssl/certs/docaiche.crt;
    ssl_certificate_key /etc/ssl/private/docaiche.key;
    
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 3. Firewall Rules

```bash
# UFW example
ufw allow 22/tcp  # SSH
ufw allow 443/tcp # HTTPS
ufw allow 8000/tcp # MCP (internal only)
ufw enable
```

### 4. Security Headers

Add to nginx configuration:

```nginx
add_header X-Content-Type-Options "nosniff" always;
add_header X-Frame-Options "DENY" always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Content-Security-Policy "default-src 'self'" always;
```

## Monitoring Setup

### 1. Prometheus Configuration

```yaml
# prometheus.yml
global:
  scrape_interval: 15s

scrape_configs:
  - job_name: 'docaiche-mcp'
    static_configs:
      - targets: ['localhost:8000']
    metrics_path: '/metrics'
```

### 2. Grafana Dashboard

Import the provided dashboard from `monitoring/grafana/dashboards/mcp-overview.json`

Key metrics to monitor:
- Request rate and latency
- Error rates by endpoint
- Cache hit rates
- Connection pool usage
- Security violations

### 3. Alerting Rules

```yaml
# alerts.yml
groups:
  - name: mcp_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(mcp_requests_total{status="error"}[5m]) > 0.05
        for: 5m
        annotations:
          summary: "High error rate detected"
          
      - alert: HighLatency
        expr: histogram_quantile(0.95, mcp_request_duration_seconds) > 1
        for: 5m
        annotations:
          summary: "High request latency detected"
```

### 4. Log Aggregation

Configure structured logging to ship to ELK stack:

```yaml
# filebeat.yml
filebeat.inputs:
  - type: log
    enabled: true
    paths:
      - /app/logs/*.json
    json.keys_under_root: true
    json.add_error_key: true

output.elasticsearch:
  hosts: ["elasticsearch:9200"]
```

## Troubleshooting

### Common Issues

#### 1. Connection Refused

```bash
# Check if service is running
systemctl status docaiche-mcp

# Check logs
journalctl -u docaiche-mcp -f

# Verify port binding
netstat -tlnp | grep 8000
```

#### 2. Authentication Failures

```bash
# Verify JWT keys exist
ls -la keys/

# Test token generation
python -m src.mcp.tools.test_auth

# Check token expiry
jwt decode <token> --no-verify
```

#### 3. Performance Issues

```bash
# Check resource usage
htop

# Monitor connections
ss -tan | grep 8000 | wc -l

# Check cache performance
redis-cli INFO stats
```

#### 4. Rate Limiting

```bash
# Check current limits
curl -H "Authorization: Bearer <token>" \
  http://localhost:8000/api/rate-limit/status

# Monitor rate limit metrics
curl http://localhost:8000/metrics | grep rate_limit
```

### Debug Mode

Enable debug logging:

```bash
export LOG_LEVEL=DEBUG
export MCP_DEBUG=true
python -m src.mcp.main
```

## Production Checklist

### Pre-deployment

- [ ] Generate strong secret keys
- [ ] Configure RSA key pairs for JWT
- [ ] Set up database with proper credentials
- [ ] Configure Redis for caching
- [ ] Review and update CORS settings
- [ ] Set appropriate rate limits
- [ ] Configure log rotation

### Security

- [ ] Enable HTTPS/TLS
- [ ] Configure firewall rules
- [ ] Set security headers
- [ ] Enable rate limiting
- [ ] Configure CORS properly
- [ ] Rotate secrets regularly
- [ ] Enable audit logging

### Monitoring

- [ ] Set up Prometheus scraping
- [ ] Import Grafana dashboards
- [ ] Configure alerting rules
- [ ] Set up log aggregation
- [ ] Enable distributed tracing
- [ ] Configure health checks
- [ ] Set up uptime monitoring

### Performance

- [ ] Configure connection pooling
- [ ] Enable response compression
- [ ] Set up caching strategy
- [ ] Configure worker processes
- [ ] Enable HTTP/2
- [ ] Set appropriate timeouts
- [ ] Configure load balancing

### Backup and Recovery

- [ ] Database backup strategy
- [ ] Configuration backup
- [ ] Document recovery procedures
- [ ] Test restore process
- [ ] Set up automated backups

### Documentation

- [ ] Update API documentation
- [ ] Document custom configurations
- [ ] Create runbooks
- [ ] Document known issues
- [ ] Update changelog

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/docaiche/issues
- Documentation: https://docs.docaiche.example.com
- Community Forum: https://forum.docaiche.example.com