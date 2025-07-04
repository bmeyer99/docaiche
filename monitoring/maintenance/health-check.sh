#!/bin/bash

# Monitoring Stack Health Check Script
# Performs quick health checks on all monitoring components

set -euo pipefail

# Configuration
VM_URL="${VM_URL:-http://victoriametrics:8428}"
PROMETHEUS_URL="${PROMETHEUS_URL:-http://prometheus:9090}"
GRAFANA_URL="${GRAFANA_URL:-http://grafana:3000}"
LOKI_URL="${LOKI_URL:-http://loki:3100}"
ALERT_WEBHOOK="${ALERT_WEBHOOK:-}"

# Health status
HEALTH_STATUS="healthy"
FAILED_CHECKS=()

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check function
check_service() {
    local service_name=$1
    local health_url=$2
    local timeout=${3:-5}
    
    if curl -sf --max-time "$timeout" "$health_url" > /dev/null 2>&1; then
        echo -e "${GREEN}✓${NC} $service_name is healthy"
        return 0
    else
        echo -e "${RED}✗${NC} $service_name is unhealthy"
        FAILED_CHECKS+=("$service_name")
        HEALTH_STATUS="unhealthy"
        return 1
    fi
}

# Check VictoriaMetrics specific metrics
check_vm_metrics() {
    echo -e "\n${YELLOW}VictoriaMetrics Metrics:${NC}"
    
    # Check ingestion rate
    local ingestion_rate=$(curl -sf "$VM_URL/api/v1/query?query=rate(vm_rows_inserted_total[1m])" | jq -r '.data.result[0].value[1] // 0')
    echo "  Ingestion rate: ${ingestion_rate} rows/sec"
    
    # Check active series
    local active_series=$(curl -sf "$VM_URL/api/v1/query?query=vm_rows" | jq -r '.data.result[0].value[1] // 0')
    echo "  Active series: ${active_series}"
    
    # Check storage size
    local storage_size=$(curl -sf "$VM_URL/api/v1/query?query=vm_data_size_bytes" | jq -r '.data.result[0].value[1] // 0' | numfmt --to=iec)
    echo "  Storage size: ${storage_size}"
    
    # Check cache hit ratio
    local cache_hit_ratio=$(curl -sf "$VM_URL/api/v1/query?query=rate(vm_cache_hits_total[5m])/(rate(vm_cache_hits_total[5m])+rate(vm_cache_misses_total[5m]))" | jq -r '.data.result[0].value[1] // 0')
    cache_hit_percentage=$(echo "$cache_hit_ratio * 100" | bc -l | xargs printf "%.2f")
    echo "  Cache hit ratio: ${cache_hit_percentage}%"
    
    # Warn if metrics are concerning
    if (( $(echo "$ingestion_rate < 1" | bc -l) )); then
        echo -e "  ${YELLOW}⚠ Warning: Low ingestion rate${NC}"
    fi
    
    if (( $(echo "$cache_hit_ratio < 0.5" | bc -l) )); then
        echo -e "  ${YELLOW}⚠ Warning: Low cache hit ratio${NC}"
    fi
}

# Check disk space
check_disk_space() {
    echo -e "\n${YELLOW}Disk Space:${NC}"
    
    # Check main data directories
    for dir in /data/victoriametrics /data/backups /var/lib/grafana /loki; do
        if [ -d "$dir" ]; then
            local usage=$(df -h "$dir" 2>/dev/null | tail -1 | awk '{print $5}' | sed 's/%//')
            local available=$(df -h "$dir" 2>/dev/null | tail -1 | awk '{print $4}')
            
            if [ -n "$usage" ]; then
                if [ "$usage" -gt 85 ]; then
                    echo -e "  ${RED}✗${NC} $dir: ${usage}% used (${available} available)"
                    FAILED_CHECKS+=("disk_space_$dir")
                elif [ "$usage" -gt 70 ]; then
                    echo -e "  ${YELLOW}⚠${NC} $dir: ${usage}% used (${available} available)"
                else
                    echo -e "  ${GREEN}✓${NC} $dir: ${usage}% used (${available} available)"
                fi
            fi
        fi
    done
}

# Check recent errors in logs
check_recent_errors() {
    echo -e "\n${YELLOW}Recent Errors (last 5 minutes):${NC}"
    
    # Query Loki for recent errors
    local error_count=$(curl -sf "$LOKI_URL/loki/api/v1/query_range?query={job=~\".+\"} |~ \"error|ERROR|Error\"&limit=100&start=$(date -d '5 minutes ago' +%s)000000000" | jq -r '.data.result | length // 0')
    
    if [ "$error_count" -gt 50 ]; then
        echo -e "  ${RED}✗${NC} High error rate: $error_count errors in last 5 minutes"
        FAILED_CHECKS+=("high_error_rate")
    elif [ "$error_count" -gt 10 ]; then
        echo -e "  ${YELLOW}⚠${NC} Moderate error rate: $error_count errors in last 5 minutes"
    else
        echo -e "  ${GREEN}✓${NC} Low error rate: $error_count errors in last 5 minutes"
    fi
}

# Send alert if unhealthy
send_alert() {
    if [ "$HEALTH_STATUS" = "unhealthy" ] && [ -n "$ALERT_WEBHOOK" ]; then
        local failed_list=$(IFS=,; echo "${FAILED_CHECKS[*]}")
        curl -sf -X POST "$ALERT_WEBHOOK" \
            -H "Content-Type: application/json" \
            -d "{
                \"status\": \"unhealthy\",
                \"failed_checks\": \"$failed_list\",
                \"timestamp\": \"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",
                \"host\": \"$(hostname)\"
            }" || echo "Failed to send alert"
    fi
}

# Main health check
main() {
    echo -e "${YELLOW}=== Monitoring Stack Health Check ===${NC}"
    echo "Timestamp: $(date)"
    echo ""
    
    # Check all services
    echo -e "${YELLOW}Service Health:${NC}"
    check_service "VictoriaMetrics" "$VM_URL/health"
    check_service "Prometheus" "$PROMETHEUS_URL/-/healthy"
    check_service "Grafana" "$GRAFANA_URL/api/health"
    check_service "Loki" "$LOKI_URL/ready"
    
    # Check VictoriaMetrics specific metrics
    check_vm_metrics
    
    # Check disk space
    check_disk_space
    
    # Check recent errors
    check_recent_errors
    
    # Summary
    echo -e "\n${YELLOW}=== Summary ===${NC}"
    if [ "$HEALTH_STATUS" = "healthy" ]; then
        echo -e "${GREEN}Overall Status: HEALTHY${NC}"
        exit 0
    else
        echo -e "${RED}Overall Status: UNHEALTHY${NC}"
        echo "Failed checks: ${FAILED_CHECKS[*]}"
        send_alert
        exit 1
    fi
}

# Run main function
main