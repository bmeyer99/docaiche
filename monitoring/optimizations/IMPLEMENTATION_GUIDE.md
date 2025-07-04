# Monitoring Optimization Implementation Guide

## Quick Start

To implement the monitoring optimizations, follow these steps:

### 1. Review Current Setup
```bash
# Check current monitoring stack status
docker-compose ps | grep -E "prometheus|victoriametrics|grafana|loki"

# Check current resource usage
docker stats --no-stream | grep -E "prometheus|victoriametrics|grafana|loki"
```

### 2. Backup Current Configuration
```bash
# Create backup directory
mkdir -p /data/backups/monitoring/pre-optimization

# Backup current data
docker exec victoriametrics tar -czf - /victoria-metrics-data > /data/backups/monitoring/pre-optimization/vm-data-$(date +%Y%m%d).tar.gz
```

### 3. Deploy Optimizations
```bash
# Stop current monitoring stack
docker-compose stop victoriametrics prometheus grafana

# Deploy with optimized configuration
docker-compose -f docker-compose.yml -f monitoring/optimizations/docker-compose.monitoring-optimized.yml up -d

# Wait for services to be healthy
sleep 30

# Check health status
./monitoring/maintenance/health-check.sh
```

### 4. Verify Implementation
```bash
# Check that recording rules are loaded
curl -s http://localhost:9090/api/v1/rules | jq '.data.groups[].name'

# Verify VictoriaMetrics optimization parameters
curl -s http://localhost:8428/api/v1/status/flags | jq '.data' | grep -E "dedup|downsampling|memory"

# Check Grafana dashboards
curl -s http://admin:admin@localhost:3000/api/search?type=dash-db | jq '.[].title'
```

## Configuration Details

### VictoriaMetrics Optimizations

1. **Memory Management**:
   - Uses 80% of available memory for better performance
   - 2GB max memory per query to prevent OOM
   - Dedicated cache directory on SSD

2. **Data Partitioning**:
   - Automatic deduplication for 30s intervals
   - Downsampling: 5m (30d), 15m (90d), 1h (365d)
   - 12-month retention period

3. **Query Performance**:
   - 16 concurrent queries max
   - 5-minute max query duration
   - Optimized cache configuration

### Backup Strategy

1. **Hot Backups** (every 6 hours):
   ```bash
   ./monitoring/backup/backup-strategy.sh hot
   ```

2. **Daily Backups**:
   ```bash
   ./monitoring/backup/backup-strategy.sh daily
   ```

3. **Weekly Full Backups**:
   ```bash
   ./monitoring/backup/backup-strategy.sh weekly
   ```

4. **Monthly Archives**:
   ```bash
   ./monitoring/backup/backup-strategy.sh monthly
   ```

### Maintenance Schedule

The maintenance container automatically runs:
- **Daily** (2 AM): Compaction, cache optimization, log cleanup
- **Weekly** (Sunday 3 AM): Query analysis, recording rule updates
- **Monthly** (1st at 4 AM): Full backup, retention enforcement
- **Every 5 minutes**: Health checks
- **Hourly**: Metrics collection

### Monitoring the Monitoring

Access the performance dashboards:
1. Query Performance: http://localhost:3000/d/query-performance
2. VictoriaMetrics Health: http://localhost:8428/metrics
3. Prometheus Status: http://localhost:9090/targets

### Troubleshooting

1. **High Query Latency**:
   ```bash
   # Check slow queries
   curl -s http://localhost:8428/api/v1/query_log | jq '.data' | head -20
   
   # Force cache rebuild
   curl -X POST http://localhost:8428/internal/resetRollupResultCache
   ```

2. **Storage Issues**:
   ```bash
   # Check storage usage
   ./monitoring/maintenance/health-check.sh
   
   # Force merge old partitions
   curl -X POST "http://localhost:8428/internal/force_merge?partition_prefix=$(date -d '30 days ago' +%Y%m)"
   ```

3. **Backup Failures**:
   ```bash
   # Check backup logs
   tail -f /var/log/monitoring-maintenance/backup.log
   
   # Verify backup integrity
   ./monitoring/backup/backup-strategy.sh verify /path/to/backup
   ```

## Performance Tuning

### Resource Allocation

Recommended minimum resources:
- VictoriaMetrics: 4 CPU, 8GB RAM, 500GB SSD
- Prometheus: 2 CPU, 4GB RAM
- Grafana: 1 CPU, 2GB RAM
- Maintenance: 1 CPU, 1GB RAM

### Storage Optimization

1. **Use separate volumes for**:
   - Data: Fast SSD (`/data/victoriametrics/data`)
   - Cache: Fast SSD (`/data/victoriametrics/cache`)
   - Snapshots: Standard storage (`/data/victoriametrics/snapshots`)
   - Backups: Cold storage (`/data/backups/monitoring`)

2. **Filesystem recommendations**:
   - XFS or ext4 with noatime
   - Separate partition for monitoring data
   - Regular defragmentation for HDDs

### Network Optimization

1. **Internal communication**:
   - Use Docker network for service discovery
   - Enable compression for remote write

2. **External access**:
   - Use Traefik for load balancing
   - Enable gzip compression
   - Set appropriate timeouts

## Monitoring Best Practices

1. **Label Management**:
   - Keep cardinality under control
   - Use consistent naming conventions
   - Regular cardinality audits

2. **Query Optimization**:
   - Use recording rules for repeated queries
   - Time-bound all queries
   - Leverage the query cache

3. **Data Lifecycle**:
   - Implement retention policies
   - Use downsampling for old data
   - Regular backup verification

## Security Considerations

1. **Backup Encryption**:
   - All backups encrypted with AES-256
   - Store encryption keys securely
   - Regular key rotation

2. **Access Control**:
   - Use authentication for all endpoints
   - Implement RBAC for Grafana
   - Audit log all configuration changes

3. **Network Security**:
   - Use TLS for external connections
   - Firewall rules for monitoring ports
   - Regular security updates

## Rollback Procedure

If issues occur, rollback to previous configuration:

```bash
# Stop optimized stack
docker-compose -f docker-compose.yml -f monitoring/optimizations/docker-compose.monitoring-optimized.yml down

# Restore from backup
./monitoring/backup/backup-strategy.sh restore /data/backups/monitoring/pre-optimization/vm-data-*.tar.gz

# Start original stack
docker-compose up -d victoriametrics prometheus grafana
```

## Support and Monitoring

- Check health status: `./monitoring/maintenance/health-check.sh`
- View maintenance logs: `/var/log/monitoring-maintenance/`
- Performance reports: `/var/log/monitoring-maintenance/metrics/`
- Backup status: `./monitoring/backup/backup-strategy.sh list`

For issues, check:
1. Container logs: `docker-compose logs -f victoriametrics`
2. Health check output
3. Grafana dashboards for anomalies
4. Backup verification status