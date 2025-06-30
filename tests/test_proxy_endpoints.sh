#!/bin/bash

# Test Docaiche API through admin-ui proxy
# This validates that all services are accessible through the single exposed port 4080

echo "Testing Docaiche services through admin-ui proxy (port 4080)"
echo "============================================================"

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

# Base URL through proxy
PROXY_BASE="http://localhost:4080"

echo -e "\n1. Testing API endpoints through proxy..."
# Test key API endpoints
endpoints=(
    "/api/v1/health"
    "/api/v1/stats" 
    "/api/v1/search?q=test"
    "/api/v1/config"
    "/api/v1/providers"
    "/api/v1/admin/dashboard"
)

for endpoint in "${endpoints[@]}"; do
    status=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_BASE$endpoint")
    if [ "$status" == "200" ]; then
        echo -e "${GREEN}✓${NC} $endpoint - Status: $status"
    else
        echo -e "${RED}✗${NC} $endpoint - Status: $status"
    fi
done

echo -e "\n2. Testing Grafana access through proxy..."
grafana_status=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_BASE/grafana/")
if [ "$grafana_status" == "302" ] || [ "$grafana_status" == "200" ]; then
    echo -e "${GREEN}✓${NC} Grafana accessible at $PROXY_BASE/grafana/ - Status: $grafana_status"
else
    echo -e "${RED}✗${NC} Grafana not accessible - Status: $grafana_status"
fi

echo -e "\n3. Testing direct ports are NOT exposed..."
# These should fail if properly configured
direct_ports=(
    "8000"  # API
    "3000"  # Grafana
    "3100"  # Loki
    "3001"  # AnythingLLM
    "6379"  # Redis
)

for port in "${direct_ports[@]}"; do
    if timeout 2 bash -c "echo >/dev/tcp/localhost/$port" 2>/dev/null; then
        echo -e "${RED}✗${NC} Port $port is exposed (should be internal only)"
    else
        echo -e "${GREEN}✓${NC} Port $port is not exposed (correct)"
    fi
done

echo -e "\n4. Testing admin-ui health..."
ui_health=$(curl -s -o /dev/null -w "%{http_code}" "$PROXY_BASE/api/health")
if [ "$ui_health" == "200" ]; then
    echo -e "${GREEN}✓${NC} Admin UI health check - Status: $ui_health"
else
    echo -e "${RED}✗${NC} Admin UI health check - Status: $ui_health"
fi

echo -e "\nProxy validation complete!"