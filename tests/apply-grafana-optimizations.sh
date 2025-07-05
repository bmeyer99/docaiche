#!/bin/bash

# Apply Grafana Performance Optimizations Script
# This script applies all the performance optimizations for faster dashboard loading

set -e

echo "=== Applying Grafana Performance Optimizations ==="

# Backup current configurations
echo "1. Creating backups..."
cp prometheus.yml prometheus.yml.backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true
cp loki-config.yaml loki-config.yaml.backup-$(date +%Y%m%d-%H%M%S) 2>/dev/null || true

# Apply optimized configurations
echo "2. Applying optimized configurations..."
cp prometheus-optimized.yml prometheus.yml
cp loki-config-optimized.yaml loki-config.yaml

# Validate configurations
echo "3. Validating configurations..."
docker run --rm -v $(pwd):/config --entrypoint promtool prom/prometheus:latest check config /config/prometheus.yml || {
    echo "ERROR: Prometheus configuration validation failed!"
    exit 1
}

# Copy recording rules to the correct volume mount location
echo "4. Setting up recording rules..."
docker-compose exec -T prometheus sh -c "cat > /etc/prometheus/prometheus-recording-rules.yml" < prometheus-recording-rules.yml || {
    echo "WARNING: Could not copy recording rules directly, will be picked up on restart"
}

# Rebuild and restart monitoring services
echo "5. Rebuilding monitoring services..."
docker-compose up -d --build prometheus loki promtail grafana

# Wait for services to be healthy
echo "6. Waiting for services to be healthy..."
for service in prometheus loki grafana; do
    echo -n "   Waiting for $service..."
    for i in {1..30}; do
        if docker-compose exec -T $service wget --spider -q http://localhost:${port:-9090}/-/healthy 2>/dev/null || \
           docker-compose exec -T $service wget --spider -q http://localhost:${port:-3100}/ready 2>/dev/null || \
           docker-compose exec -T $service curl -sf http://localhost:${port:-3000}/api/health >/dev/null 2>&1; then
            echo " OK"
            break
        fi
        sleep 2
        echo -n "."
    done
done

# Reload Prometheus configuration
echo "7. Reloading Prometheus configuration..."
curl -X POST http://localhost:4080/prometheus/-/reload 2>/dev/null || {
    echo "WARNING: Could not reload Prometheus config via API, will use restart"
}

# Display status
echo "8. Checking optimization status..."
echo ""
echo "=== Recording Rules Status ==="
curl -s http://localhost:4080/prometheus/api/v1/rules | jq -r '.data.groups[].rules[] | select(.type=="recording") | .name' 2>/dev/null || echo "Recording rules will be available after 2-3 minutes"

echo ""
echo "=== Optimization Complete ==="
echo ""
echo "Next steps:"
echo "1. Wait 2-3 minutes for recording rules to populate"
echo "2. Access Grafana at http://localhost:4080/grafana"
echo "3. Import the optimized dashboard from: grafana/dashboards/performance-optimized-dashboard.json"
echo "4. Monitor performance improvements using the new dashboard"
echo ""
echo "For detailed information, see: GRAFANA_PERFORMANCE_OPTIMIZATION.md"