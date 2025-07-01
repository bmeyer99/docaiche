#!/bin/bash
#
# Test Service Configuration Persistence
# This script verifies that all service configurations survive Docker restarts
#

set -e

echo "🧪 Testing Service Configuration Persistence"
echo "============================================"

# Function to check service health
check_services_health() {
    echo "Checking service health..."
    local health_status=$(curl -s http://localhost:4080/api/v1/health | jq -r '.overall_status')
    echo "Overall health status: $health_status"
}

# Function to get a test value from database
get_test_config() {
    docker exec docaiche-api-1 python -c "
import sqlite3
conn = sqlite3.connect('/data/docaiche.db')
cursor = conn.cursor()
cursor.execute('SELECT value FROM system_config WHERE key = ?', ('test.persistence.marker',))
result = cursor.fetchone()
print(result[0] if result else 'NOT_FOUND')
conn.close()
"
}

# Function to set a test value in database
set_test_config() {
    local value="$1"
    docker exec docaiche-api-1 python -c "
import sqlite3
import json
conn = sqlite3.connect('/data/docaiche.db')
cursor = conn.cursor()
cursor.execute('''
    INSERT OR REPLACE INTO system_config (key, value, schema_version, updated_at, updated_by)
    VALUES (?, ?, ?, datetime('now'), ?)
''', ('test.persistence.marker', json.dumps({'value': '$value', 'timestamp': '$(date -u +%Y-%m-%dT%H:%M:%SZ)'}), '1.0', 'persistence-test'))
conn.commit()
conn.close()
"
}

# Function to check Redis persistence
check_redis_persistence() {
    docker exec docaiche-redis-1 redis-cli GET "test:persistence:marker"
}

# Function to set Redis test value
set_redis_value() {
    local value="$1"
    docker exec docaiche-redis-1 redis-cli SET "test:persistence:marker" "$value" EX 3600
}

# Function to check Grafana dashboard count
check_grafana_dashboards() {
    # Wait a bit for Grafana to be ready
    sleep 5
    curl -s -u admin:admin http://localhost:3000/api/search | jq '. | length'
}

# Function to check Prometheus targets
check_prometheus_targets() {
    curl -s http://localhost:9090/api/v1/targets | jq '.data.activeTargets | length'
}

echo ""
echo "📊 Step 1: Checking initial state"
echo "---------------------------------"
check_services_health

echo ""
echo "💾 Step 2: Setting test markers"
echo "-------------------------------"
TEST_MARKER="persistence-test-$(date +%s)"
echo "Setting database marker: $TEST_MARKER"
set_test_config "$TEST_MARKER"

echo "Setting Redis marker: $TEST_MARKER"
set_redis_value "$TEST_MARKER"

echo ""
echo "✅ Step 3: Verifying markers are set"
echo "-----------------------------------"
echo "Database marker: $(get_test_config)"
echo "Redis marker: $(check_redis_persistence)"
echo "Grafana dashboards: $(check_grafana_dashboards)"
echo "Prometheus targets: $(check_prometheus_targets)"

echo ""
echo "🔄 Step 4: Restarting all services"
echo "---------------------------------"
docker-compose restart

echo "Waiting for services to come back up..."
sleep 30

echo ""
echo "🔍 Step 5: Checking persistence after restart"
echo "--------------------------------------------"
check_services_health

echo "Database marker: $(get_test_config)"
echo "Redis marker: $(check_redis_persistence)"
echo "Grafana dashboards: $(check_grafana_dashboards)"
echo "Prometheus targets: $(check_prometheus_targets)"

echo ""
echo "🛑 Step 6: Stopping and starting services"
echo "----------------------------------------"
docker-compose down
docker-compose up -d

echo "Waiting for services to come back up..."
sleep 40

echo ""
echo "🔍 Step 7: Final persistence check"
echo "---------------------------------"
check_services_health

DB_MARKER=$(get_test_config)
REDIS_MARKER=$(check_redis_persistence)
GRAFANA_DASHBOARDS=$(check_grafana_dashboards)
PROMETHEUS_TARGETS=$(check_prometheus_targets)

echo "Database marker: $DB_MARKER"
echo "Redis marker: $REDIS_MARKER"
echo "Grafana dashboards: $GRAFANA_DASHBOARDS"
echo "Prometheus targets: $PROMETHEUS_TARGETS"

echo ""
echo "📋 Test Results Summary"
echo "====================="

if [[ "$DB_MARKER" == *"$TEST_MARKER"* ]]; then
    echo "✅ Database persistence: PASSED"
else
    echo "❌ Database persistence: FAILED"
fi

if [[ "$REDIS_MARKER" == "$TEST_MARKER" ]]; then
    echo "✅ Redis persistence: PASSED"
else
    echo "❌ Redis persistence: FAILED"
fi

if [[ "$GRAFANA_DASHBOARDS" -gt 0 ]]; then
    echo "✅ Grafana persistence: PASSED"
else
    echo "❌ Grafana persistence: FAILED"
fi

if [[ "$PROMETHEUS_TARGETS" -gt 0 ]]; then
    echo "✅ Prometheus persistence: PASSED"
else
    echo "❌ Prometheus persistence: FAILED"
fi

echo ""
echo "Test completed!"