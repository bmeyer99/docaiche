# MCP Search System - Production Deployment Guide

## Overview

This guide provides comprehensive instructions for deploying the MCP (Model Context Protocol) Search System in production environments. The system has been thoroughly tested and validated for production readiness.

## System Architecture Summary

The MCP Search System enhances the existing Docaiche search infrastructure with:

- **External Search Providers**: Brave, Google, DuckDuckGo integration
- **Multi-Tier Caching**: L1 (in-memory LRU) + L2 (Redis) caching
- **Text AI Enhancement**: LLM-powered search optimization
- **Performance Monitoring**: Real-time statistics and health monitoring
- **Admin UI Integration**: Complete management interface

## Pre-Deployment Checklist

### ✅ System Requirements

**Hardware Requirements:**
- **CPU**: Minimum 4 cores, Recommended 8+ cores
- **Memory**: Minimum 8GB RAM, Recommended 16GB+ RAM
- **Storage**: Minimum 50GB, Recommended 100GB+ SSD
- **Network**: Stable internet connection for external search providers

**Software Requirements:**
- **Python**: 3.12+ (tested and validated)
- **Redis**: 6.0+ for L2 caching
- **PostgreSQL**: 14+ for workspace and document storage
- **Docker**: 24.0+ (if using containerized deployment)
- **Node.js**: 18+ for Admin UI

### ✅ External Dependencies

**Required API Keys:**
- **Brave Search API**: Sign up at https://api.search.brave.com/
- **Google Custom Search API**: Configure at https://developers.google.com/custom-search
- **OpenAI API**: For LLM text analysis (optional but recommended)

**External Services:**
- **Redis Instance**: For L2 caching and session storage
- **PostgreSQL Database**: For workspace and document metadata
- **Monitoring Service**: Prometheus/Grafana (recommended)

## Deployment Steps

### Step 1: Environment Preparation

```bash
# 1. Clone repository and navigate to project
cd /opt/docaiche

# 2. Create production virtual environment
python3.12 -m venv venv
source venv/bin/activate

# 3. Install production dependencies
pip install -r requirements.txt
pip install gunicorn uvicorn[standard]

# 4. Set proper permissions
chmod +x scripts/*.sh
chown -R docaiche:docaiche /opt/docaiche
```

### Step 2: Configuration Setup

Create production configuration file:

```bash
# Create production environment file
cat > .env.production << 'EOF'
# Database Configuration
DATABASE_URL=postgresql://user:password@localhost:5432/docaiche_prod
REDIS_URL=redis://localhost:6379/0

# API Keys (Replace with your actual keys)
BRAVE_SEARCH_API_KEY=your_brave_api_key_here
GOOGLE_CUSTOM_SEARCH_API_KEY=your_google_api_key_here
GOOGLE_CUSTOM_SEARCH_ENGINE_ID=your_search_engine_id_here
OPENAI_API_KEY=your_openai_api_key_here

# MCP Configuration
MCP_ENABLE_EXTERNAL_SEARCH=true
MCP_ENABLE_HEDGED_REQUESTS=true
MCP_HEDGED_DELAY_SECONDS=0.15
MCP_MAX_CONCURRENT_PROVIDERS=3
MCP_CIRCUIT_BREAKER_THRESHOLD=5

# Cache Configuration
MCP_L1_CACHE_SIZE=1000
MCP_L2_CACHE_TTL=3600
MCP_COMPRESSION_THRESHOLD=1024

# Performance Configuration
MCP_ENABLE_PERFORMANCE_MONITORING=true
MCP_STATS_COLLECTION_INTERVAL=300

# Security Configuration
SECRET_KEY=your_secret_key_here
API_RATE_LIMIT_PER_MINUTE=1000
CORS_ORIGINS=["https://your-domain.com"]

# Logging Configuration
LOG_LEVEL=INFO
LOG_FORMAT=json
LOG_FILE=/var/log/docaiche/app.log
EOF
```

### Step 3: Database Migration

```bash
# 1. Initialize database schema
python scripts/init_database.py --env production

# 2. Run any pending migrations
python scripts/migrate_database.py --env production

# 3. Verify database health
python scripts/health_check.py --database --env production
```

### Step 4: Redis Configuration

Configure Redis for optimal performance:

```bash
# Create Redis configuration
cat > /etc/redis/redis-docaiche.conf << 'EOF'
# Network
bind 127.0.0.1
port 6379
timeout 300

# Memory
maxmemory 2gb
maxmemory-policy allkeys-lru

# Persistence
save 900 1
save 300 10
save 60 10000

# Performance
tcp-keepalive 300
tcp-backlog 511
databases 16
EOF

# Start Redis with custom configuration
sudo systemctl enable redis-server
sudo systemctl start redis-server
```

### Step 5: MCP System Initialization

```bash
# 1. Initialize MCP configuration
python scripts/init_mcp_system.py --env production

# 2. Configure external search providers
python scripts/configure_mcp_providers.py \
  --provider brave_search \
  --api-key "${BRAVE_SEARCH_API_KEY}" \
  --priority 1 \
  --max-results 10

python scripts/configure_mcp_providers.py \
  --provider google_search \
  --api-key "${GOOGLE_CUSTOM_SEARCH_API_KEY}" \
  --search-engine-id "${GOOGLE_CUSTOM_SEARCH_ENGINE_ID}" \
  --priority 2 \
  --max-results 10

# 3. Validate MCP system health
python scripts/validate_mcp_system.py --env production
```

### Step 6: Application Deployment

#### Option A: Direct Python Deployment

```bash
# 1. Start application with Gunicorn
gunicorn src.main:app \
  --bind 0.0.0.0:8000 \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --worker-connections 1000 \
  --max-requests 10000 \
  --max-requests-jitter 1000 \
  --timeout 30 \
  --keep-alive 2 \
  --env-file .env.production \
  --access-logfile /var/log/docaiche/access.log \
  --error-logfile /var/log/docaiche/error.log \
  --log-level info \
  --daemon

# 2. Verify application health
curl -f http://localhost:8000/api/v1/health
```

#### Option B: Docker Deployment

```bash
# 1. Build production Docker image
docker build -t docaiche-mcp:latest \
  --target production \
  --build-arg ENV=production .

# 2. Run production container
docker run -d \
  --name docaiche-mcp-prod \
  --restart unless-stopped \
  -p 8000:8000 \
  --env-file .env.production \
  -v /var/log/docaiche:/app/logs \
  -v /opt/docaiche/data:/app/data \
  docaiche-mcp:latest

# 3. Verify container health
docker exec docaiche-mcp-prod curl -f http://localhost:8000/api/v1/health
```

### Step 7: Admin UI Deployment

```bash
# 1. Navigate to admin UI directory
cd admin-ui

# 2. Install production dependencies
npm ci --only=production

# 3. Build production assets
npm run build

# 4. Deploy to web server (example with nginx)
sudo cp -r build/* /var/www/docaiche-admin/
sudo chown -R www-data:www-data /var/www/docaiche-admin/
```

### Step 8: Reverse Proxy Configuration

Configure Nginx as reverse proxy:

```nginx
# /etc/nginx/sites-available/docaiche
server {
    listen 80;
    server_name your-domain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    # SSL Configuration
    ssl_certificate /path/to/your/certificate.crt;
    ssl_certificate_key /path/to/your/private.key;
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-RSA-AES256-GCM-SHA512:DHE-RSA-AES256-GCM-SHA512;

    # API Proxy
    location /api/ {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_connect_timeout 30s;
        proxy_send_timeout 30s;
        proxy_read_timeout 30s;
    }

    # Admin UI
    location / {
        root /var/www/docaiche-admin;
        index index.html;
        try_files $uri $uri/ /index.html;
        
        # Cache static assets
        location ~* \.(js|css|png|jpg|jpeg|gif|ico|svg)$ {
            expires 1y;
            add_header Cache-Control "public, immutable";
        }
    }

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains";
}
```

## Post-Deployment Verification

### Health Check Validation

```bash
# 1. API Health Check
curl -f https://your-domain.com/api/v1/health

# 2. MCP System Health Check
curl -f https://your-domain.com/api/v1/mcp/config

# 3. External Search Providers Check
curl -f https://your-domain.com/api/v1/mcp/providers

# 4. Performance Statistics Check
curl -f https://your-domain.com/api/v1/mcp/stats
```

### Performance Validation

```bash
# Run performance validation script
python scripts/validate_production_performance.py \
  --url https://your-domain.com \
  --test-external-search \
  --test-caching \
  --test-concurrent-load

# Expected Results:
# ✅ L1 Cache: < 0.1ms average
# ✅ External Search: < 2s average
# ✅ System Throughput: > 100 RPS
# ✅ Memory Usage: < 500MB growth
```

### Functional Testing

```bash
# Test complete search workflow
python scripts/test_production_workflow.py \
  --url https://your-domain.com \
  --api-key "${API_KEY}" \
  --test-scenarios comprehensive

# Test MCP provider functionality
python scripts/test_mcp_providers.py \
  --url https://your-domain.com \
  --test-all-providers
```

## Monitoring and Alerting

### Prometheus Metrics

The system exposes metrics at `/api/v1/metrics`:

```yaml
# prometheus.yml
- job_name: 'docaiche-mcp'
  static_configs:
    - targets: ['localhost:8000']
  metrics_path: '/api/v1/metrics'
  scrape_interval: 30s
```

### Key Metrics to Monitor

**Application Metrics:**
- `docaiche_search_requests_total`
- `docaiche_search_duration_seconds`
- `docaiche_cache_hits_total`
- `docaiche_cache_misses_total`
- `docaiche_external_search_requests_total`
- `docaiche_external_search_failures_total`

**System Metrics:**
- CPU usage < 80%
- Memory usage < 16GB
- Disk usage < 80%
- Network latency < 100ms

### Alerting Rules

```yaml
# alerts.yml
groups:
- name: docaiche-mcp
  rules:
  - alert: DocaicheHighErrorRate
    expr: rate(docaiche_search_errors_total[5m]) > 0.1
    for: 2m
    annotations:
      summary: "High error rate in Docaiche MCP system"

  - alert: DocaicheCacheHitRateLow
    expr: docaiche_cache_hit_ratio < 0.8
    for: 5m
    annotations:
      summary: "Cache hit ratio below threshold"

  - alert: DocaicheExternalSearchDown
    expr: docaiche_external_search_providers_healthy < 1
    for: 1m
    annotations:
      summary: "No healthy external search providers"
```

## Maintenance and Operations

### Daily Operations

```bash
# 1. Check system health
curl -s https://your-domain.com/api/v1/health | jq .

# 2. Monitor performance stats
curl -s https://your-domain.com/api/v1/mcp/stats | jq .

# 3. Check logs for errors
tail -f /var/log/docaiche/error.log | grep ERROR

# 4. Monitor cache performance
redis-cli info stats | grep cache
```

### Weekly Maintenance

```bash
# 1. Update performance statistics
python scripts/weekly_performance_report.py

# 2. Clean old cache entries
python scripts/cache_maintenance.py --clean-expired

# 3. Backup configuration
python scripts/backup_mcp_config.py --output /backup/mcp-config-$(date +%Y%m%d).json

# 4. Update provider performance metrics
python scripts/update_provider_metrics.py
```

### Monthly Maintenance

```bash
# 1. Full system health audit
python scripts/monthly_health_audit.py

# 2. Performance optimization review
python scripts/performance_optimization_review.py

# 3. Security updates
python scripts/security_update_check.py

# 4. Capacity planning review
python scripts/capacity_planning_analysis.py
```

## Troubleshooting

### Common Issues and Solutions

**1. External Search Provider Failures**
```bash
# Check provider status
curl -s https://your-domain.com/api/v1/mcp/providers | jq '.providers[] | select(.health.status != "healthy")'

# Reset circuit breaker
python scripts/reset_circuit_breaker.py --provider brave_search

# Update API credentials
python scripts/update_provider_credentials.py --provider brave_search --api-key new_key
```

**2. Cache Performance Issues**
```bash
# Check cache statistics
curl -s https://your-domain.com/api/v1/mcp/stats | jq '.stats.cache_metrics'

# Clear L1 cache
python scripts/clear_l1_cache.py

# Restart Redis (L2 cache)
sudo systemctl restart redis-server
```

**3. High Memory Usage**
```bash
# Check memory usage by component
python scripts/memory_analysis.py

# Adjust cache sizes
python scripts/optimize_cache_sizes.py --l1-size 500 --l2-ttl 1800

# Restart application
sudo systemctl restart docaiche-mcp
```

**4. External Search Timeouts**
```bash
# Check timeout configuration
python scripts/check_timeout_config.py

# Adjust adaptive timeouts
python scripts/adjust_adaptive_timeouts.py --increase-timeout 1.5

# Enable circuit breakers
python scripts/enable_circuit_breakers.py --threshold 3
```

## Security Considerations

### API Security

- **Rate Limiting**: Configured per endpoint
- **Authentication**: JWT tokens for API access
- **CORS**: Restricted to authorized domains
- **HTTPS**: Enforced for all communications

### Data Security

- **API Keys**: Stored securely with encryption
- **Search Queries**: Logged with PII redaction
- **Cache Data**: Encrypted at rest
- **Database**: TLS connections required

### Network Security

- **Firewall**: Restrict access to necessary ports
- **VPN**: Optional for admin access
- **SSL/TLS**: Latest protocols and ciphers
- **Security Headers**: Comprehensive protection

## Performance Optimization

### Recommended Settings

**Production Configuration:**
```yaml
# High-performance settings
mcp_config:
  l1_cache_size: 2000
  l2_cache_ttl: 7200
  max_concurrent_providers: 5
  hedged_delay_seconds: 0.1
  circuit_breaker_threshold: 3
  compression_threshold: 512
  
performance_tuning:
  worker_processes: 8
  worker_connections: 2000
  max_requests: 50000
  keep_alive_timeout: 5
```

**Redis Optimization:**
```
maxmemory 4gb
maxmemory-policy allkeys-lru
tcp-keepalive 60
tcp-backlog 2048
```

## Scaling Considerations

### Horizontal Scaling

- **Load Balancing**: Multiple application instances
- **Redis Clustering**: For high-availability caching
- **Database Replication**: Read replicas for queries
- **CDN Integration**: For static assets

### Vertical Scaling

- **CPU**: 16+ cores for high throughput
- **Memory**: 32GB+ for large cache sizes
- **Storage**: NVMe SSD for optimal performance
- **Network**: 10Gbps for external search providers

## Support and Documentation

### Additional Resources

- **API Documentation**: `/docs` endpoint
- **Admin UI Guide**: `docs/ADMIN_UI_GUIDE.md`
- **Developer Documentation**: `docs/DEVELOPER_GUIDE.md`
- **Troubleshooting Guide**: `docs/TROUBLESHOOTING.md`

### Support Contacts

- **Technical Issues**: Create GitHub issue
- **Performance Questions**: Review performance documentation
- **Security Concerns**: Follow security reporting guidelines

---

**Deployment completed successfully!** 🚀

The MCP Search System is now ready for production use with comprehensive monitoring, security, and performance optimization.