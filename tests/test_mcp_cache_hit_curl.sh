#!/bin/bash
# MCP Cache Hit E2E Test using curl
# This test validates cache hit behavior through the MCP endpoint

echo "========================================================================"
echo "MCP Cache Hit E2E Test (using curl)"
echo "========================================================================"
echo "Test started at: $(date)"
echo "========================================================================"

# MCP endpoint URL
MCP_URL="http://localhost:4080/api/v1/mcp/search"

# Test query JSON
QUERY_JSON='{
  "query": "python asyncio tutorial examples best practices",
  "workspace": "python_docs",
  "technology_hint": "python",
  "max_results": 10,
  "force_external": false
}'

echo -e "\nTest Query:"
echo "$QUERY_JSON" | jq .

echo -e "\n========================================================================"
echo "1. FIRST QUERY (Expected Cache Miss)"
echo "------------------------------------------------------------------------"

# First query - should be cache miss
START_TIME_1=$(date +%s.%N)
RESPONSE_1=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON" \
  -w "\n{\"http_code\": %{http_code}, \"time_total\": %{time_total}}")
END_TIME_1=$(date +%s.%N)

# Extract HTTP code and response body
HTTP_CODE_1=$(echo "$RESPONSE_1" | tail -n 1 | jq -r '.http_code')
TIME_TOTAL_1=$(echo "$RESPONSE_1" | tail -n 1 | jq -r '.time_total')
BODY_1=$(echo "$RESPONSE_1" | head -n -1)

echo "HTTP Status Code: $HTTP_CODE_1"
echo "Response Time: ${TIME_TOTAL_1}s"

if [ "$HTTP_CODE_1" = "200" ]; then
    # Parse response
    CACHE_HIT_1=$(echo "$BODY_1" | jq -r '.cache_hit // false')
    CORRELATION_ID_1=$(echo "$BODY_1" | jq -r '.correlation_id // "N/A"')
    NUM_RESULTS_1=$(echo "$BODY_1" | jq -r '.results | length')
    EXEC_TIME_1=$(echo "$BODY_1" | jq -r '.execution_time_ms // "N/A"')
    
    echo "Cache Hit: $CACHE_HIT_1"
    echo "Correlation ID: $CORRELATION_ID_1"
    echo "Number of Results: $NUM_RESULTS_1"
    echo "Execution Time (reported): ${EXEC_TIME_1}ms"
    
    # Show first result
    if [ "$NUM_RESULTS_1" -gt 0 ]; then
        echo -e "\nFirst Result:"
        echo "$BODY_1" | jq -r '.results[0] | "  Title: \(.title // "N/A")\n  URL: \(.url // "N/A")\n  Provider: \(.provider // "N/A")\n  Score: \(.relevance_score // "N/A")"'
    fi
else
    echo "Error Response:"
    echo "$BODY_1" | jq . 2>/dev/null || echo "$BODY_1"
fi

# Wait to ensure cache is written
echo -e "\nWaiting 2 seconds to ensure cache is written..."
sleep 2

echo -e "\n========================================================================"
echo "2. SECOND QUERY (Expected Cache Hit)"
echo "------------------------------------------------------------------------"

# Second query - should be cache hit
START_TIME_2=$(date +%s.%N)
RESPONSE_2=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$QUERY_JSON" \
  -w "\n{\"http_code\": %{http_code}, \"time_total\": %{time_total}}")
END_TIME_2=$(date +%s.%N)

# Extract HTTP code and response body
HTTP_CODE_2=$(echo "$RESPONSE_2" | tail -n 1 | jq -r '.http_code')
TIME_TOTAL_2=$(echo "$RESPONSE_2" | tail -n 1 | jq -r '.time_total')
BODY_2=$(echo "$RESPONSE_2" | head -n -1)

echo "HTTP Status Code: $HTTP_CODE_2"
echo "Response Time: ${TIME_TOTAL_2}s"

if [ "$HTTP_CODE_2" = "200" ]; then
    # Parse response
    CACHE_HIT_2=$(echo "$BODY_2" | jq -r '.cache_hit // false')
    CORRELATION_ID_2=$(echo "$BODY_2" | jq -r '.correlation_id // "N/A"')
    NUM_RESULTS_2=$(echo "$BODY_2" | jq -r '.results | length')
    EXEC_TIME_2=$(echo "$BODY_2" | jq -r '.execution_time_ms // "N/A"')
    
    echo "Cache Hit: $CACHE_HIT_2"
    echo "Correlation ID: $CORRELATION_ID_2"
    echo "Number of Results: $NUM_RESULTS_2"
    echo "Execution Time (reported): ${EXEC_TIME_2}ms"
    
    if [ "$CACHE_HIT_2" = "true" ]; then
        echo -e "\n✅ CACHE HIT CONFIRMED!"
    else
        echo -e "\n❌ CACHE MISS - This was expected to be a cache hit!"
    fi
else
    echo "Error Response:"
    echo "$BODY_2" | jq . 2>/dev/null || echo "$BODY_2"
fi

echo -e "\n========================================================================"
echo "3. PERFORMANCE COMPARISON"
echo "------------------------------------------------------------------------"

# Convert to milliseconds for comparison
TIME_MS_1=$(echo "$TIME_TOTAL_1 * 1000" | bc)
TIME_MS_2=$(echo "$TIME_TOTAL_2 * 1000" | bc)

echo "First Query Time: ${TIME_MS_1}ms"
echo "Second Query Time: ${TIME_MS_2}ms"

# Calculate speedup
if (( $(echo "$TIME_MS_2 < $TIME_MS_1" | bc -l) )); then
    SPEEDUP=$(echo "scale=1; ($TIME_MS_1 - $TIME_MS_2) / $TIME_MS_1 * 100" | bc)
    echo "✅ Cache Hit was ${SPEEDUP}% faster"
else
    echo "❌ Cache Hit was not faster - unexpected!"
fi

echo -e "\n========================================================================"
echo "4. RESULT COMPARISON"
echo "------------------------------------------------------------------------"

if [ "$HTTP_CODE_1" = "200" ] && [ "$HTTP_CODE_2" = "200" ]; then
    echo "First query results: $NUM_RESULTS_1"
    echo "Second query results: $NUM_RESULTS_2"
    
    if [ "$NUM_RESULTS_1" = "$NUM_RESULTS_2" ]; then
        echo "✅ Same number of results"
        
        # Compare first result URLs
        URL_1=$(echo "$BODY_1" | jq -r '.results[0].url // ""')
        URL_2=$(echo "$BODY_2" | jq -r '.results[0].url // ""')
        
        if [ "$URL_1" = "$URL_2" ]; then
            echo "✅ First result URLs match"
        else
            echo "❌ First result URLs differ"
        fi
    else
        echo "❌ Different number of results"
    fi
fi

echo -e "\n========================================================================"
echo "5. TESTING CACHE WITH QUERY VARIATION"
echo "------------------------------------------------------------------------"

# Query with extra space
VARIED_QUERY_JSON='{
  "query": "python asyncio tutorial examples  best practices",
  "workspace": "python_docs",
  "technology_hint": "python",
  "max_results": 10,
  "force_external": false
}'

RESPONSE_3=$(curl -s -X POST "$MCP_URL" \
  -H "Content-Type: application/json" \
  -d "$VARIED_QUERY_JSON")

if [ $? -eq 0 ]; then
    CACHE_HIT_3=$(echo "$RESPONSE_3" | jq -r '.cache_hit // false')
    echo "Query with extra space - Cache Hit: $CACHE_HIT_3"
    
    if [ "$CACHE_HIT_3" = "true" ]; then
        echo "✅ Cache normalization working - minor variations still hit cache"
    else
        echo "ℹ️  Cache is exact match only - variations cause cache miss"
    fi
fi

echo -e "\n========================================================================"
echo "TEST SUMMARY"
echo "========================================================================"

# Summary checks
echo "Test Results:"

if [ "$CACHE_HIT_2" = "true" ]; then
    echo "✅ Cache hit occurred on second query"
else
    echo "❌ Cache hit did not occur on second query"
fi

if (( $(echo "$TIME_MS_2 < $TIME_MS_1" | bc -l) )); then
    echo "✅ Cache hit was faster (${SPEEDUP}% improvement)"
else
    echo "❌ Cache hit was not faster"
fi

if [ "$NUM_RESULTS_1" = "$NUM_RESULTS_2" ]; then
    echo "✅ Results are consistent between queries"
else
    echo "❌ Results differ between queries"
fi

echo -e "\n========================================================================"
if [ "$CACHE_HIT_2" = "true" ] && (( $(echo "$TIME_MS_2 < $TIME_MS_1" | bc -l) )) && [ "$NUM_RESULTS_1" = "$NUM_RESULTS_2" ]; then
    echo "✅ ALL TESTS PASSED - Cache is working correctly!"
else
    echo "❌ SOME TESTS FAILED - Cache may have issues"
fi
echo "========================================================================"