#!/bin/bash
# Simple MCP Cache Hit E2E Test
# Tests cache behavior with repeated identical queries

echo "========================================================================"
echo "MCP Cache Hit E2E Test (Simple Version)"
echo "========================================================================"
echo "Test started at: $(date)"
echo "========================================================================"

# MCP endpoint URL
MCP_URL="http://localhost:4080/api/v1/mcp/search"

# Simple test query
QUERY_JSON='{
  "query": "test query for cache validation",
  "max_results": 5
}'

echo -e "\nTest Query:"
echo "$QUERY_JSON" | jq .

echo -e "\n========================================================================"
echo "1. FIRST QUERY (Cache Miss Expected)"
echo "------------------------------------------------------------------------"

# First query
START_1=$(date +%s%N)
RESPONSE_1=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON")
END_1=$(date +%s%N)

# Calculate time in milliseconds
TIME_1=$(( ($END_1 - $START_1) / 1000000 ))

echo "Response:"
echo "$RESPONSE_1" | jq .

CACHE_HIT_1=$(echo "$RESPONSE_1" | jq -r '.cache_hit // false')
echo -e "\nCache Hit: $CACHE_HIT_1"
echo "Response Time: ${TIME_1}ms"

# Store results for comparison
RESULTS_1=$(echo "$RESPONSE_1" | jq -c '.results')
NUM_RESULTS_1=$(echo "$RESPONSE_1" | jq '.results | length')

echo -e "\nWaiting 1 second..."
sleep 1

echo -e "\n========================================================================"
echo "2. SECOND QUERY (Cache Hit Expected)"
echo "------------------------------------------------------------------------"

# Second identical query
START_2=$(date +%s%N)
RESPONSE_2=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON")
END_2=$(date +%s%N)

# Calculate time in milliseconds
TIME_2=$(( ($END_2 - $START_2) / 1000000 ))

echo "Response:"
echo "$RESPONSE_2" | jq .

CACHE_HIT_2=$(echo "$RESPONSE_2" | jq -r '.cache_hit // false')
echo -e "\nCache Hit: $CACHE_HIT_2"
echo "Response Time: ${TIME_2}ms"

# Store results for comparison
RESULTS_2=$(echo "$RESPONSE_2" | jq -c '.results')
NUM_RESULTS_2=$(echo "$RESPONSE_2" | jq '.results | length')

echo -e "\n========================================================================"
echo "3. THIRD QUERY (Should Also Hit Cache)"
echo "------------------------------------------------------------------------"

# Third identical query
START_3=$(date +%s%N)
RESPONSE_3=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON")
END_3=$(date +%s%N)

# Calculate time in milliseconds
TIME_3=$(( ($END_3 - $START_3) / 1000000 ))

CACHE_HIT_3=$(echo "$RESPONSE_3" | jq -r '.cache_hit // false')
echo "Cache Hit: $CACHE_HIT_3"
echo "Response Time: ${TIME_3}ms"
echo "Number of Results: $(echo "$RESPONSE_3" | jq '.results | length')"

echo -e "\n========================================================================"
echo "ANALYSIS"
echo "========================================================================"

echo -e "\nCache Hit Pattern:"
echo "Query 1: Cache Hit = $CACHE_HIT_1 (Expected: false)"
echo "Query 2: Cache Hit = $CACHE_HIT_2 (Expected: true)"
echo "Query 3: Cache Hit = $CACHE_HIT_3 (Expected: true)"

echo -e "\nResponse Times:"
echo "Query 1: ${TIME_1}ms"
echo "Query 2: ${TIME_2}ms"
echo "Query 3: ${TIME_3}ms"

# Calculate average time for cache hits (if any)
if [ "$CACHE_HIT_2" = "true" ] || [ "$CACHE_HIT_3" = "true" ]; then
    if [ "$CACHE_HIT_2" = "true" ] && [ "$CACHE_HIT_3" = "true" ]; then
        AVG_CACHE_TIME=$(( ($TIME_2 + $TIME_3) / 2 ))
        echo "Average Cache Hit Time: ${AVG_CACHE_TIME}ms"
    fi
fi

echo -e "\nResult Consistency:"
echo "Query 1 Results: $NUM_RESULTS_1"
echo "Query 2 Results: $NUM_RESULTS_2"

if [ "$RESULTS_1" = "$RESULTS_2" ]; then
    echo "✅ Results are identical between queries"
else
    echo "❌ Results differ between queries"
fi

echo -e "\n========================================================================"
echo "VERDICT"
echo "========================================================================"

# Check if cache is working
if [ "$CACHE_HIT_2" = "true" ] || [ "$CACHE_HIT_3" = "true" ]; then
    echo "✅ Cache is functioning - hits detected"
    
    # Check performance improvement
    if [ "$TIME_2" -lt "$TIME_1" ] || [ "$TIME_3" -lt "$TIME_1" ]; then
        echo "✅ Cache provides performance benefit"
    else
        echo "⚠️  Cache hits not showing performance improvement"
    fi
else
    echo "❌ No cache hits detected - cache may not be working"
fi

# Additional diagnostics
echo -e "\n========================================================================"
echo "CACHE CONFIGURATION CHECK"
echo "========================================================================"

# Check MCP stats endpoint for cache information
echo -e "\nChecking MCP stats..."
STATS=$(curl -s -X GET "http://localhost:4080/api/v1/mcp/stats")
echo "$STATS" | jq .

echo -e "\n========================================================================"