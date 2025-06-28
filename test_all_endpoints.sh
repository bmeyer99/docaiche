#!/bin/bash

# Docaiche API Comprehensive Testing Script
# This script tests all API endpoints with various scenarios

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BASE_URL="${API_BASE_URL:-http://localhost:4000/api/v1}"
DELAY_BETWEEN_TESTS=1  # Delay in seconds to respect rate limiting

# Test counter
PASSED=0
FAILED=0

# Function to print colored output
print_header() {
    echo -e "\n${BLUE}===============================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}===============================================${NC}"
}

print_test() {
    echo -e "\n${YELLOW}Testing: $1${NC}"
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
    ((PASSED++))
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
    ((FAILED++))
}

# Function to test endpoint
test_endpoint() {
    local method=$1
    local endpoint=$2
    local data=$3
    local expected_status=$4
    local description=$5
    
    print_test "$description"
    
    if [ "$method" == "GET" ]; then
        response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
    elif [ "$method" == "POST" ]; then
        response=$(curl -s -w "\n%{http_code}" -X POST "$BASE_URL$endpoint" \
            -H "Content-Type: application/json" \
            -d "$data")
    elif [ "$method" == "DELETE" ]; then
        response=$(curl -s -w "\n%{http_code}" -X DELETE "$BASE_URL$endpoint")
    fi
    
    # Extract status code (last line)
    status_code=$(echo "$response" | tail -n1)
    # Extract response body (all but last line)
    body=$(echo "$response" | sed '$d')
    
    if [ "$status_code" == "$expected_status" ]; then
        print_success "Status code: $status_code (Expected: $expected_status)"
        if command -v jq &> /dev/null && [ -n "$body" ]; then
            echo "$body" | jq . 2>/dev/null || echo "$body"
        else
            echo "$body"
        fi
    else
        print_error "Status code: $status_code (Expected: $expected_status)"
        echo "Response: $body"
    fi
    
    sleep $DELAY_BETWEEN_TESTS
}

# Start testing
echo -e "${BLUE}Docaiche API Endpoint Testing${NC}"
echo -e "${BLUE}Base URL: $BASE_URL${NC}"
echo -e "${BLUE}Starting tests...${NC}"

# 1. Health & Monitoring Endpoints
print_header "HEALTH & MONITORING ENDPOINTS"

test_endpoint "GET" "/health" "" "200" "Health Check"
test_endpoint "GET" "/stats" "" "200" "System Statistics"
test_endpoint "GET" "/analytics?timeRange=24h" "" "200" "Analytics (24h)"

# 2. Search Endpoints
print_header "SEARCH ENDPOINTS"

test_endpoint "GET" "/search?q=python%20async&limit=5" "" "200" "Search Documents (GET)"

test_endpoint "POST" "/search" \
    '{"query": "fastapi tutorial", "technology_hint": "python", "limit": 10}' \
    "200" "Search Documents (POST)"

test_endpoint "POST" "/feedback" \
    '{"content_id": "doc_001", "feedback_type": "helpful", "rating": 5}' \
    "202" "Submit Feedback"

test_endpoint "POST" "/signals" \
    '{"query_id": "q123", "session_id": "s456", "signal_type": "click", "content_id": "doc_001"}' \
    "202" "Submit Signal"

# 3. Configuration Endpoints
print_header "CONFIGURATION ENDPOINTS"

test_endpoint "GET" "/config" "" "200" "Get Configuration"
test_endpoint "GET" "/collections" "" "200" "Get Collections"

test_endpoint "POST" "/config" \
    '{"key": "app.debug", "value": false, "description": "Disable debug mode"}' \
    "202" "Update Configuration"

# 4. Provider Management Endpoints
print_header "PROVIDER MANAGEMENT ENDPOINTS"

test_endpoint "GET" "/providers" "" "200" "List Providers"

test_endpoint "POST" "/providers/ollama/test" \
    '{"base_url": "http://localhost:11434/api"}' \
    "200" "Test Ollama Provider"

test_endpoint "POST" "/providers/ollama/config" \
    '{"base_url": "http://localhost:11434/api", "model": "llama2"}' \
    "200" "Update Provider Config"

# 5. Admin Endpoints
print_header "ADMIN ENDPOINTS"

test_endpoint "GET" "/admin/search-content?limit=10" "" "200" "Admin Search Content"
test_endpoint "GET" "/admin/activity/recent?limit=5" "" "200" "Get Recent Activity"
test_endpoint "GET" "/admin/activity/searches?limit=5" "" "200" "Get Recent Searches"
test_endpoint "GET" "/admin/activity/errors?limit=5" "" "200" "Get Recent Errors"
test_endpoint "GET" "/admin/dashboard" "" "200" "Get Dashboard Data"

# Note: Being careful with DELETE endpoint
# test_endpoint "DELETE" "/content/test_doc_001" "" "202" "Flag Content for Removal"

# 6. Ingestion Endpoints
print_header "INGESTION ENDPOINTS"

# File upload test (creating a test file)
echo "Test content" > /tmp/test_doc.txt
curl -s -w "\n%{http_code}" -X POST "$BASE_URL/ingestion/upload" \
    -F "file=@/tmp/test_doc.txt" > /tmp/upload_response.txt
status_code=$(tail -n1 /tmp/upload_response.txt)
if [ "$status_code" == "200" ]; then
    print_success "Upload Document - Status: $status_code"
else
    print_error "Upload Document - Status: $status_code"
fi
rm -f /tmp/test_doc.txt /tmp/upload_response.txt

# 7. Enrichment Endpoints
print_header "ENRICHMENT ENDPOINTS"

# Note: These endpoints might return 503 if enrichment service is not available
test_endpoint "POST" "/enrichment/enrich" \
    '{"content_id": "doc_001", "priority": "normal"}' \
    "503" "Enrich Content (Expected 503 if service unavailable)"

test_endpoint "GET" "/enrichment/status/doc_001" "" "503" "Get Enrichment Status"
test_endpoint "GET" "/enrichment/metrics" "" "503" "Get Enrichment Metrics"
test_endpoint "GET" "/enrichment/health" "" "503" "Enrichment Health Check"

# Summary
print_header "TEST SUMMARY"
echo -e "${GREEN}Passed: $PASSED${NC}"
echo -e "${RED}Failed: $FAILED${NC}"
TOTAL=$((PASSED + FAILED))
echo -e "Total: $TOTAL"

if [ $FAILED -eq 0 ]; then
    echo -e "\n${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "\n${RED}Some tests failed!${NC}"
    exit 1
fi