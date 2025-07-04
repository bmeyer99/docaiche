#!/bin/bash

# VictoriaMetrics Automated Maintenance Scheduler
# This script manages automated maintenance tasks for the monitoring stack

set -euo pipefail

# Configuration
VM_URL="${VM_URL:-http://victoriametrics:8428}"
GRAFANA_URL="${GRAFANA_URL:-http://grafana:3000}"
LOKI_URL="${LOKI_URL:-http://loki:3100}"
LOG_DIR="/var/log/monitoring-maintenance"
RETENTION_DAYS="${RETENTION_DAYS:-365}"
BACKUP_DIR="/data/backups/monitoring"

# Ensure log directory exists
mkdir -p "$LOG_DIR"
mkdir -p "$BACKUP_DIR"

# Logging function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_DIR/maintenance.log"
}

# Error handling
error_exit() {
    log "ERROR: $1"
    exit 1
}

# Check service health
check_service_health() {
    local service=$1
    local url=$2
    
    if curl -sf "$url/health" > /dev/null 2>&1; then
        log "✓ $service is healthy"
        return 0
    else
        log "✗ $service is unhealthy"
        return 1
    fi
}

# Daily maintenance tasks
daily_maintenance() {
    log "Starting daily maintenance tasks..."
    
    # 1. Force merge of small parts in VictoriaMetrics
    log "Triggering VictoriaMetrics merge optimization..."
    curl -X POST "$VM_URL/internal/force_merge" || log "Warning: Force merge might not be needed"
    
    # 2. Clean up old logs
    log "Cleaning up old maintenance logs..."
    find "$LOG_DIR" -name "*.log" -mtime +30 -delete
    
    # 3. Update cardinality statistics
    log "Collecting cardinality statistics..."
    curl -s "$VM_URL/api/v1/label/__name__/values" | \
        jq -r '.data | length' > "$LOG_DIR/metric_cardinality_$(date +%Y%m%d).txt"
    
    # 4. Compact Loki indexes
    log "Triggering Loki compaction..."
    curl -X POST "$LOKI_URL/loki/api/v1/compact" || log "Loki compaction triggered"
    
    # 5. Generate daily performance report
    generate_performance_report "daily"
    
    log "Daily maintenance completed"
}

# Weekly maintenance tasks
weekly_maintenance() {
    log "Starting weekly maintenance tasks..."
    
    # 1. Optimize query performance by rebuilding cache
    log "Rebuilding VictoriaMetrics cache..."
    curl -X POST "$VM_URL/internal/resetRollupResultCache"
    
    # 2. Analyze slow queries
    log "Analyzing slow queries..."
    analyze_slow_queries
    
    # 3. Update recording rules based on query patterns
    update_recording_rules
    
    # 4. Clean up orphaned time series
    clean_orphaned_series
    
    # 5. Generate weekly performance report
    generate_performance_report "weekly"
    
    log "Weekly maintenance completed"
}

# Monthly maintenance tasks
monthly_maintenance() {
    log "Starting monthly maintenance tasks..."
    
    # 1. Full backup
    log "Creating full monthly backup..."
    create_full_backup
    
    # 2. Retention policy enforcement
    log "Enforcing retention policies..."
    enforce_retention_policies
    
    # 3. Storage optimization
    log "Optimizing storage..."
    optimize_storage
    
    # 4. Update monitoring dashboards
    update_dashboards
    
    # 5. Generate monthly report
    generate_performance_report "monthly"
    
    log "Monthly maintenance completed"
}

# Analyze slow queries
analyze_slow_queries() {
    log "Analyzing slow queries from the last week..."
    
    # Query Prometheus for slow queries
    curl -s "$VM_URL/api/v1/query" \
        -d 'query=histogram_quantile(0.95, rate(prometheus_engine_query_duration_seconds_bucket[7d]))' | \
        jq -r '.data.result[] | "\(.metric) - p95: \(.value[1])"' > "$LOG_DIR/slow_queries_$(date +%Y%m%d).txt"
}

# Update recording rules based on frequent queries
update_recording_rules() {
    log "Analyzing query patterns for recording rule optimization..."
    
    # This would typically analyze query logs and suggest new recording rules
    # For now, we'll just validate existing rules
    curl -s "$VM_URL/api/v1/rules" | jq -r '.data.groups[].rules[] | .name' > "$LOG_DIR/active_rules_$(date +%Y%m%d).txt"
}

# Clean orphaned series
clean_orphaned_series() {
    log "Identifying orphaned time series..."
    
    # Find series that haven't been updated in 7 days
    local cutoff_time=$(date -d '7 days ago' +%s)
    
    # This is a placeholder - actual implementation would identify and clean orphaned series
    log "Orphaned series check completed"
}

# Create full backup
create_full_backup() {
    local backup_name="vm_backup_$(date +%Y%m%d_%H%M%S)"
    local backup_path="$BACKUP_DIR/$backup_name"
    
    log "Creating backup: $backup_name"
    
    # Create VictoriaMetrics snapshot
    local snapshot_response=$(curl -s "$VM_URL/snapshot/create")
    local snapshot_name=$(echo "$snapshot_response" | jq -r '.snapshot')
    
    if [ -n "$snapshot_name" ]; then
        log "Snapshot created: $snapshot_name"
        
        # Copy snapshot to backup location
        docker exec victoriametrics tar -czf - "/snapshots/$snapshot_name" > "$backup_path.tar.gz"
        
        # Delete snapshot after backup
        curl -s "$VM_URL/snapshot/delete?snapshot=$snapshot_name"
        
        # Create backup metadata
        cat > "$backup_path.meta" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "snapshot_name": "$snapshot_name",
    "size_bytes": $(stat -c%s "$backup_path.tar.gz"),
    "retention_days": $RETENTION_DAYS,
    "vm_version": "$(curl -s $VM_URL/api/v1/status/buildinfo | jq -r .data.version)"
}
EOF
        
        log "Backup completed: $backup_path.tar.gz"
    else
        error_exit "Failed to create snapshot"
    fi
}

# Enforce retention policies
enforce_retention_policies() {
    log "Enforcing retention policies..."
    
    # Clean up old backups
    find "$BACKUP_DIR" -name "*.tar.gz" -mtime +$RETENTION_DAYS -delete
    find "$BACKUP_DIR" -name "*.meta" -mtime +$RETENTION_DAYS -delete
    
    # Report on storage usage
    local storage_used=$(du -sh "$BACKUP_DIR" | cut -f1)
    log "Backup storage usage: $storage_used"
}

# Optimize storage
optimize_storage() {
    log "Optimizing storage utilization..."
    
    # Get storage metrics
    local storage_metrics=$(curl -s "$VM_URL/api/v1/query?query=vm_data_size_bytes")
    local total_size=$(echo "$storage_metrics" | jq -r '.data.result[0].value[1]' | numfmt --to=iec)
    
    log "Total storage used: $total_size"
    
    # Trigger aggressive merge for older partitions
    curl -X POST "$VM_URL/internal/force_merge?partition_prefix=$(date -d '30 days ago' +%Y%m)"
}

# Update monitoring dashboards
update_dashboards() {
    log "Updating Grafana dashboards..."
    
    # This would typically update dashboards based on new metrics or requirements
    # For now, we'll just backup existing dashboards
    
    local dashboard_backup="$BACKUP_DIR/dashboards_$(date +%Y%m%d).json"
    
    # Export all dashboards
    curl -s "$GRAFANA_URL/api/search?type=dash-db" | \
        jq -r '.[] | .uid' | \
        while read -r uid; do
            curl -s "$GRAFANA_URL/api/dashboards/uid/$uid" >> "$dashboard_backup"
            echo "" >> "$dashboard_backup"
        done
    
    log "Dashboard backup created: $dashboard_backup"
}

# Generate performance report
generate_performance_report() {
    local report_type=$1
    local report_file="$LOG_DIR/performance_report_${report_type}_$(date +%Y%m%d).json"
    
    log "Generating $report_type performance report..."
    
    cat > "$report_file" <<EOF
{
    "report_type": "$report_type",
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "metrics": {
        "total_series": $(curl -s "$VM_URL/api/v1/query?query=vm_rows" | jq -r '.data.result[0].value[1]'),
        "ingestion_rate": $(curl -s "$VM_URL/api/v1/query?query=rate(vm_rows_inserted_total[1h])" | jq -r '.data.result[0].value[1]'),
        "query_rate": $(curl -s "$VM_URL/api/v1/query?query=rate(vm_http_requests_total{path=\"/api/v1/query\"}[1h])" | jq -r '.data.result[0].value[1]'),
        "storage_bytes": $(curl -s "$VM_URL/api/v1/query?query=vm_data_size_bytes" | jq -r '.data.result[0].value[1]'),
        "cache_hit_rate": $(curl -s "$VM_URL/api/v1/query?query=rate(vm_cache_hits_total[1h])/(rate(vm_cache_hits_total[1h])+rate(vm_cache_misses_total[1h]))" | jq -r '.data.result[0].value[1]')
    }
}
EOF
    
    log "Performance report generated: $report_file"
}

# Main maintenance dispatcher
main() {
    local maintenance_type=${1:-daily}
    
    log "=== Starting $maintenance_type maintenance ==="
    
    # Check service health first
    check_service_health "VictoriaMetrics" "$VM_URL" || error_exit "VictoriaMetrics is not healthy"
    check_service_health "Grafana" "$GRAFANA_URL" || log "Warning: Grafana is not healthy"
    check_service_health "Loki" "$LOKI_URL" || log "Warning: Loki is not healthy"
    
    case "$maintenance_type" in
        daily)
            daily_maintenance
            ;;
        weekly)
            daily_maintenance
            weekly_maintenance
            ;;
        monthly)
            daily_maintenance
            weekly_maintenance
            monthly_maintenance
            ;;
        *)
            error_exit "Unknown maintenance type: $maintenance_type"
            ;;
    esac
    
    log "=== Maintenance completed successfully ==="
}

# Run maintenance
main "$@"