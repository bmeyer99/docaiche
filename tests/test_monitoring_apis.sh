#!/bin/bash

echo "Testing Monitoring API Endpoints..."
echo "=================================="

echo -e "\n1. Testing Prometheus endpoint:"
curl -s http://localhost:4080/prometheus/api/v1/query?query=up | jq -r '.status' || echo "Failed"

echo -e "\n2. Testing Loki endpoint:"
curl -s http://localhost:4080/loki/loki/api/v1/labels | jq -r '.status' || echo "Failed"

echo -e "\n3. Testing container metrics:"
curl -s "http://localhost:4080/prometheus/api/v1/query_range?query=rate(container_cpu_usage_seconds_total[5m])&start=$(date -d '1 hour ago' +%s)&end=$(date +%s)&step=30s" | jq -r '.status' || echo "Failed"

echo -e "\n4. Testing Redis metrics:"
curl -s "http://localhost:4080/prometheus/api/v1/query?query=redis_uptime_in_seconds" | jq -r '.status' || echo "Failed"

echo -e "\nAll tests completed!"