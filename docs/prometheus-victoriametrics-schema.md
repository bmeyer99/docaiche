# Prometheus Metrics Storage with VictoriaMetrics

## Overview

This document describes the storage architecture for Prometheus metrics in the DocAIche project. The system uses **VictoriaMetrics** as the long-term storage backend for Prometheus metrics.

## Storage Architecture

### VictoriaMetrics Storage Model

VictoriaMetrics handles its own storage internally and **does not require any PostgreSQL schema**. It uses its own efficient time-series database engine with the following characteristics:

1. **Internal Storage**: VictoriaMetrics stores all metrics data in its own optimized format at `/storage` (mounted as a Docker volume)
2. **No External Database Required**: Unlike some metrics solutions, VictoriaMetrics does not use PostgreSQL or any other external database
3. **Built-in Compression**: Automatically compresses time-series data for efficient storage
4. **Deduplication**: Removes duplicate data points based on configured scrape intervals

### Current Configuration

Based on the `docker-compose.yml` configuration:

```yaml
victoriametrics:
  image: victoriametrics/victoria-metrics:v1.101.0
  command:
    - '-storageDataPath=/storage'
    - '-retentionPeriod=12'        # 12 months retention
    - '-dedup.minScrapeInterval=30s'
  volumes:
    - victoriametrics_data:/storage
```

### Data Flow

1. **Prometheus** scrapes metrics from various targets (API, Redis, Weaviate, etc.)
2. **Remote Write**: Prometheus sends metrics to VictoriaMetrics via remote write API
3. **Storage**: VictoriaMetrics stores the data in its internal format
4. **Query**: Both Prometheus and Grafana can query VictoriaMetrics for historical data

## Prometheus Configuration

The `prometheus.yml` file configures the integration:

```yaml
# Remote write configuration for VictoriaMetrics
remote_write:
  - url: http://victoriametrics:8428/api/v1/write
    queue_config:
      capacity: 10000
      max_shards: 30

# Remote read configuration for VictoriaMetrics
remote_read:
  - url: http://victoriametrics:8428/api/v1/read
    read_recent: true
```

## Grafana Integration

Grafana is configured to use VictoriaMetrics as a Prometheus-compatible data source:

```yaml
datasources:
  - name: VictoriaMetrics
    type: prometheus
    url: http://victoriametrics:8428
```

## Storage Requirements

### Disk Space Estimation

With the current configuration:
- **Retention Period**: 12 months
- **Scrape Interval**: 30 seconds
- **Estimated Storage**: ~50-100GB for a typical setup (depends on number of metrics)

### Volume Management

The `victoriametrics_data` Docker volume stores all metrics data. To backup or restore:

```bash
# Backup
docker run --rm -v victoriametrics_data:/data -v $(pwd):/backup alpine tar czf /backup/vm-backup.tar.gz -C /data .

# Restore
docker run --rm -v victoriametrics_data:/data -v $(pwd):/backup alpine tar xzf /backup/vm-backup.tar.gz -C /data
```

## No Additional Schema Required

**Important**: VictoriaMetrics manages its own storage format internally. There is no need to:
- Create PostgreSQL tables for metrics
- Define any database schema
- Set up any external storage backend

The system is fully self-contained within the VictoriaMetrics container and its volume.

## Monitoring VictoriaMetrics

VictoriaMetrics exposes its own metrics at `http://victoriametrics:8428/metrics` which include:
- Storage usage
- Ingestion rate
- Query performance
- Memory usage

These metrics are scraped by Prometheus for monitoring the monitoring system itself.

## API Endpoints

The application exposes metrics-related endpoints through `/api/v1/metrics/`:
- `/api/v1/metrics/query` - Execute PromQL queries
- `/api/v1/metrics/dashboards` - List available Grafana dashboards
- `/api/v1/metrics/alerts` - Get active alerts
- `/api/v1/metrics/targets` - View scrape targets status

All metrics queries are proxied through the API to either Prometheus or VictoriaMetrics depending on the time range.

## Summary

VictoriaMetrics provides a complete, self-contained solution for long-term Prometheus metrics storage. It requires no external database schema or configuration beyond the Docker setup already in place. The system is designed to be maintenance-free with automatic data management and retention policies.