#!/bin/bash

# Metrics Collection Script for Monitoring Performance Analysis
# Collects and stores key metrics for trend analysis

set -euo pipefail

# Configuration
VM_URL="${VM_URL:-http://victoriametrics:8428}"
METRICS_DIR="/var/log/monitoring-maintenance/metrics"
RETENTION_DAYS="${RETENTION_DAYS:-90}"

# Ensure metrics directory exists
mkdir -p "$METRICS_DIR"

# Timestamp for this collection
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
METRICS_FILE="$METRICS_DIR/metrics_$TIMESTAMP.json"

# Collect metrics function
collect_metric() {
    local metric_name=$1
    local query=$2
    local result=$(curl -sf "$VM_URL/api/v1/query?query=$query" | jq -r '.data.result[0].value[1] // "null"')
    echo "$result"
}

# Main collection
main() {
    echo "Collecting metrics at $(date)..."
    
    # Start building JSON
    cat > "$METRICS_FILE" <<EOF
{
    "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
    "collection_time_unix": $(date +%s),
    "metrics": {
EOF
    
    # System metrics
    echo '        "system": {' >> "$METRICS_FILE"
    echo "            \"total_series\": $(collect_metric "total_series" "vm_rows")," >> "$METRICS_FILE"
    echo "            \"ingestion_rate\": $(collect_metric "ingestion_rate" "rate(vm_rows_inserted_total[5m])")," >> "$METRICS_FILE"
    echo "            \"query_rate\": $(collect_metric "query_rate" "rate(vm_http_requests_total{path=\"/api/v1/query\"}[5m])")," >> "$METRICS_FILE"
    echo "            \"storage_bytes\": $(collect_metric "storage_bytes" "vm_data_size_bytes")," >> "$METRICS_FILE"
    echo "            \"cache_hit_ratio\": $(collect_metric "cache_hit_ratio" "rate(vm_cache_hits_total[5m])/(rate(vm_cache_hits_total[5m])+rate(vm_cache_misses_total[5m]))")," >> "$METRICS_FILE"
    echo "            \"memory_usage_bytes\": $(collect_metric "memory_usage" "process_resident_memory_bytes{job=\"victoriametrics\"}")," >> "$METRICS_FILE"
    echo "            \"cpu_usage_percent\": $(collect_metric "cpu_usage" "rate(process_cpu_seconds_total{job=\"victoriametrics\"}[5m])*100")" >> "$METRICS_FILE"
    echo '        },' >> "$METRICS_FILE"
    
    # Query performance metrics
    echo '        "query_performance": {' >> "$METRICS_FILE"
    echo "            \"p50_latency\": $(collect_metric "p50_latency" "histogram_quantile(0.50,sum(rate(vm_query_duration_seconds_bucket[5m]))by(le))")," >> "$METRICS_FILE"
    echo "            \"p95_latency\": $(collect_metric "p95_latency" "histogram_quantile(0.95,sum(rate(vm_query_duration_seconds_bucket[5m]))by(le))")," >> "$METRICS_FILE"
    echo "            \"p99_latency\": $(collect_metric "p99_latency" "histogram_quantile(0.99,sum(rate(vm_query_duration_seconds_bucket[5m]))by(le))")," >> "$METRICS_FILE"
    echo "            \"concurrent_queries\": $(collect_metric "concurrent_queries" "vm_concurrent_queries")" >> "$METRICS_FILE"
    echo '        },' >> "$METRICS_FILE"
    
    # Service metrics
    echo '        "services": {' >> "$METRICS_FILE"
    echo "            \"api_requests_per_second\": $(collect_metric "api_rps" "sum(rate(http_requests_total{service=\"api\"}[5m]))")," >> "$METRICS_FILE"
    echo "            \"api_error_rate\": $(collect_metric "api_errors" "sum(rate(http_requests_total{service=\"api\",status=~\"5..\"}[5m]))/sum(rate(http_requests_total{service=\"api\"}[5m]))")," >> "$METRICS_FILE"
    echo "            \"weaviate_objects\": $(collect_metric "weaviate_objects" "sum(weaviate_objects_total)")," >> "$METRICS_FILE"
    echo "            \"redis_memory_bytes\": $(collect_metric "redis_memory" "redis_memory_used_bytes")" >> "$METRICS_FILE"
    echo '        },' >> "$METRICS_FILE"
    
    # Cardinality analysis
    echo '        "cardinality": {' >> "$METRICS_FILE"
    
    # Get top 5 metrics by cardinality
    local cardinality_data=$(curl -sf "$VM_URL/api/v1/label/__name__/values" | jq -r '.data[]' | head -20 | while read metric; do
        local count=$(curl -sf "$VM_URL/api/v1/series?match[]=$metric" | jq '.data | length')
        echo "{\"$metric\": $count}"
    done | jq -s 'add')
    
    echo "            \"top_metrics\": $cardinality_data" >> "$METRICS_FILE"
    echo '        }' >> "$METRICS_FILE"
    
    # Close JSON
    echo '    }' >> "$METRICS_FILE"
    echo '}' >> "$METRICS_FILE"
    
    # Validate JSON
    if jq . "$METRICS_FILE" > /dev/null 2>&1; then
        echo "Metrics collected successfully: $METRICS_FILE"
    else
        echo "Error: Invalid JSON in metrics file"
        exit 1
    fi
    
    # Clean old metrics files
    find "$METRICS_DIR" -name "metrics_*.json" -mtime +$RETENTION_DAYS -delete
    
    # Generate daily summary if it's the last collection of the day
    if [ "$(date +%H)" = "23" ]; then
        generate_daily_summary
    fi
}

# Generate daily summary
generate_daily_summary() {
    local today=$(date +%Y%m%d)
    local summary_file="$METRICS_DIR/daily_summary_$today.json"
    
    echo "Generating daily summary..."
    
    # Aggregate metrics from today
    jq -s '{
        date: "'$today'",
        metrics_count: length,
        averages: {
            ingestion_rate: (map(.metrics.system.ingestion_rate | tonumber) | add / length),
            query_rate: (map(.metrics.system.query_rate | tonumber) | add / length),
            cache_hit_ratio: (map(.metrics.system.cache_hit_ratio | tonumber) | add / length),
            p95_latency: (map(.metrics.query_performance.p95_latency | tonumber) | add / length)
        },
        peaks: {
            max_series: (map(.metrics.system.total_series | tonumber) | max),
            max_ingestion_rate: (map(.metrics.system.ingestion_rate | tonumber) | max),
            max_query_rate: (map(.metrics.system.query_rate | tonumber) | max),
            max_storage_bytes: (map(.metrics.system.storage_bytes | tonumber) | max)
        }
    }' "$METRICS_DIR"/metrics_${today}*.json > "$summary_file"
    
    echo "Daily summary created: $summary_file"
}

# Run main function
main