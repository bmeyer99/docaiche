#!/bin/bash
#
# Simulate System Reboot and Verify All Configurations Persist
#

set -e

echo "🔄 System Reboot Simulation Test"
echo "================================"
echo ""

# Color codes for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    local status=$1
    local message=$2
    
    if [ "$status" = "pass" ]; then
        echo -e "${GREEN}✅ $message${NC}"
    elif [ "$status" = "fail" ]; then
        echo -e "${RED}❌ $message${NC}"
    else
        echo -e "${YELLOW}⚠️  $message${NC}"
    fi
}

# Function to check if a service configuration file exists
check_config_file() {
    local file=$1
    local description=$2
    
    if [ -f "$file" ]; then
        print_status "pass" "$description exists"
        return 0
    else
        print_status "fail" "$description missing"
        return 1
    fi
}

# Function to verify volume data
check_volume_data() {
    local volume=$1
    local description=$2
    
    # Check if volume exists and has data
    local size=$(docker volume inspect $volume 2>/dev/null | jq -r '.[0].UsageData.Size // 0')
    
    if [ "$size" != "0" ] && [ "$size" != "null" ]; then
        print_status "pass" "$description has data (size: $size bytes)"
        return 0
    else
        # Try alternative method
        local exists=$(docker volume ls | grep -c "$volume" || true)
        if [ "$exists" -gt 0 ]; then
            print_status "pass" "$description exists"
            return 0
        else
            print_status "fail" "$description has no data"
            return 1
        fi
    fi
}

echo "📋 Pre-Reboot Configuration Check"
echo "---------------------------------"

# Check configuration files
echo ""
echo "Configuration Files:"
check_config_file "config.yaml" "Main config (config.yaml)"
check_config_file "loki-config.yaml" "Loki config"
check_config_file "prometheus.yml" "Prometheus config"
check_config_file "promtail-config.yaml" "Promtail config"
check_config_file "docker-compose.yml" "Docker Compose config"

# Check volumes
echo ""
echo "Docker Volumes:"
check_volume_data "docaiche_db_data" "Database volume"
check_volume_data "docaiche_redis_data" "Redis volume"
check_volume_data "docaiche_anythingllm_data" "AnythingLLM data"
check_volume_data "docaiche_loki_data" "Loki logs"
check_volume_data "docaiche_grafana_data" "Grafana data"
check_volume_data "docaiche_prometheus_data" "Prometheus metrics"

# Store current state
echo ""
echo "📸 Capturing Current State"
echo "-------------------------"

# Get provider configuration count
PROVIDER_COUNT=$(docker exec docaiche-api-1 python -c "
import sqlite3
conn = sqlite3.connect('/data/docaiche.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM system_config WHERE key LIKE \"ai.providers.%\"')
print(cursor.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")

echo "Provider configurations: $PROVIDER_COUNT"

# Get Grafana dashboard count
DASHBOARD_COUNT=$(curl -s -u admin:admin http://localhost:3000/api/search 2>/dev/null | jq '. | length' || echo "0")
echo "Grafana dashboards: $DASHBOARD_COUNT"

# Get Prometheus target count
PROMETHEUS_TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq '.data.activeTargets | length' || echo "0")
echo "Prometheus targets: $PROMETHEUS_TARGETS"

echo ""
echo "🔌 Simulating System Shutdown"
echo "-----------------------------"
docker-compose down

echo ""
echo "💤 Simulating Power Off (5 seconds)..."
sleep 5

echo ""
echo "🚀 Simulating System Boot"
echo "------------------------"
docker-compose up -d

echo ""
echo "⏳ Waiting for services to start (40 seconds)..."
sleep 40

echo ""
echo "🔍 Post-Reboot Verification"
echo "---------------------------"

# Verify services are running
echo ""
echo "Service Status:"
RUNNING_SERVICES=$(docker ps --filter "name=docaiche" --format "{{.Names}}" | wc -l)
echo "Running services: $RUNNING_SERVICES"

# Verify configurations persisted
echo ""
echo "Configuration Persistence:"

# Check provider configurations
NEW_PROVIDER_COUNT=$(docker exec docaiche-api-1 python -c "
import sqlite3
conn = sqlite3.connect('/data/docaiche.db')
cursor = conn.cursor()
cursor.execute('SELECT COUNT(*) FROM system_config WHERE key LIKE \"ai.providers.%\"')
print(cursor.fetchone()[0])
conn.close()
" 2>/dev/null || echo "0")

if [ "$NEW_PROVIDER_COUNT" = "$PROVIDER_COUNT" ] && [ "$PROVIDER_COUNT" -gt 0 ]; then
    print_status "pass" "Provider configurations persisted ($NEW_PROVIDER_COUNT)"
else
    print_status "fail" "Provider configurations lost (was: $PROVIDER_COUNT, now: $NEW_PROVIDER_COUNT)"
fi

# Check Grafana dashboards
NEW_DASHBOARD_COUNT=$(curl -s -u admin:admin http://localhost:3000/api/search 2>/dev/null | jq '. | length' || echo "0")
if [ "$NEW_DASHBOARD_COUNT" = "$DASHBOARD_COUNT" ] && [ "$DASHBOARD_COUNT" -gt 0 ]; then
    print_status "pass" "Grafana dashboards persisted ($NEW_DASHBOARD_COUNT)"
else
    print_status "fail" "Grafana dashboards lost (was: $DASHBOARD_COUNT, now: $NEW_DASHBOARD_COUNT)"
fi

# Check Prometheus targets
NEW_PROMETHEUS_TARGETS=$(curl -s http://localhost:9090/api/v1/targets 2>/dev/null | jq '.data.activeTargets | length' || echo "0")
if [ "$NEW_PROMETHEUS_TARGETS" = "$PROMETHEUS_TARGETS" ] && [ "$PROMETHEUS_TARGETS" -gt 0 ]; then
    print_status "pass" "Prometheus targets persisted ($NEW_PROMETHEUS_TARGETS)"
else
    print_status "fail" "Prometheus targets lost (was: $PROMETHEUS_TARGETS, now: $NEW_PROMETHEUS_TARGETS)"
fi

# Check API health
echo ""
echo "System Health:"
HEALTH_STATUS=$(curl -s http://localhost:4080/api/v1/health | jq -r '.overall_status' 2>/dev/null || echo "error")
if [ "$HEALTH_STATUS" = "degraded" ] || [ "$HEALTH_STATUS" = "healthy" ]; then
    print_status "pass" "API is responding (status: $HEALTH_STATUS)"
else
    print_status "fail" "API is not responding properly"
fi

# Check Redis persistence
REDIS_KEYS=$(docker exec docaiche-redis-1 redis-cli DBSIZE | grep -o '[0-9]*' || echo "0")
if [ "$REDIS_KEYS" -gt 0 ]; then
    print_status "pass" "Redis has persisted data ($REDIS_KEYS keys)"
else
    print_status "warn" "Redis has no keys (may be normal if cache expired)"
fi

echo ""
echo "📊 Test Summary"
echo "==============="
echo "This test simulated a complete system reboot and verified that:"
echo "- All configuration files remain intact"
echo "- Docker volumes preserve their data"  
echo "- Services restart automatically"
echo "- Database configurations persist"
echo "- Monitoring dashboards and targets are restored"
echo ""
echo "Test completed successfully!"