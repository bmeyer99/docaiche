#!/bin/bash
#
# Test Provider Configuration Metrics in Prometheus
#

echo "🔍 Testing Provider Configuration Metrics"
echo "========================================"
echo ""

# Function to query Prometheus
query_prometheus() {
    local query="$1"
    local description="$2"
    
    echo "📊 $description"
    result=$(curl -s "http://localhost:9090/api/v1/query?query=$query" | jq -r '.data.result[0].value[1] // "No data"')
    echo "   Result: $result"
    echo ""
}

# Test provider initialization metrics
echo "Provider Initialization Metrics:"
echo "-------------------------------"
query_prometheus "sum(provider_initialization_count{status='success'})" "Total successful provider initializations"
query_prometheus "sum(provider_initialization_count{status='failed'})" "Total failed provider initializations"
query_prometheus "avg(provider_initialization_duration{status='success'})" "Average provider init duration (seconds)"

# Test provider configuration operation metrics
echo "Provider Configuration Operations:"
echo "---------------------------------"
query_prometheus "count(provider_config_operation_duration)" "Total provider config operations"
query_prometheus "sum by (provider_id) (provider_config_operation_duration{operation='initialize'})" "Init duration by provider"

# Test service restart metrics
echo "Service Restart Metrics:"
echo "-----------------------"
query_prometheus "sum(service_restart_count{status='success'})" "Total successful service restarts"
query_prometheus "sum(service_restart_count{status='failed'})" "Total failed service restarts"
query_prometheus "avg(service_restart_duration)" "Average service restart duration"

# Test model selection metrics
echo "Model Selection Metrics:"
echo "-----------------------"
query_prometheus "sum(model_selection_operation_duration{status='success'})" "Model selection operations"

echo ""
echo "📈 Dashboard Access"
echo "==================="
echo "Access the Grafana dashboard at:"
echo "http://localhost:3000/dashboards"
echo ""
echo "Look for: 'Provider & Service Configuration Monitoring'"
echo "in the 'DocAIche' folder"
echo ""
echo "Default credentials: admin/admin"
echo "(If changed, check your deployment configuration)"