#!/bin/bash

echo "=== Context7 Ingestion Check ==="
echo

# Check for Context7 in logs
echo "1. Checking for Context7 activity in logs..."
docker compose logs admin-ui --tail 500 | grep -i "context7" | wc -l | xargs echo "Context7 mentions in logs:"

echo
echo "2. Recent Context7 log entries:"
docker compose logs admin-ui --tail 500 | grep -i "context7" | tail -5

echo
echo "3. Checking for sync ingestion activity..."
docker compose logs admin-ui --tail 500 | grep -i "sync_ingestion\|_perform_sync_ingestion" | wc -l | xargs echo "Sync ingestion mentions:"

echo
echo "4. Checking for external search activity..."
docker compose logs admin-ui --tail 500 | grep -i "external_search\|external search" | wc -l | xargs echo "External search mentions:"

echo
echo "5. Checking for TTL-related activity..."
docker compose logs admin-ui --tail 500 | grep -i "ttl\|expires_at" | wc -l | xargs echo "TTL mentions:"

echo
echo "6. Checking database for Context7 entries..."
docker compose exec -T postgres psql -U docaiche_user -d docaiche_dev -c "SELECT COUNT(*) as context7_count FROM content_metadata WHERE enrichment_metadata::text LIKE '%context7%' OR processing_status LIKE '%context7%';" 2>/dev/null || echo "Database query failed"

echo
echo "7. Checking for recent ingestion pipeline metrics..."
docker compose logs admin-ui --tail 200 | grep "PIPELINE_METRICS.*context7" | tail -3

echo
echo "8. Checking MCP provider status..."
docker compose logs admin-ui --tail 200 | grep -i "mcp.*context7\|context7.*provider" | tail -3

echo
echo "=== Summary ==="
echo "If all counts are 0, Context7 ingestion is likely not happening."
echo "Check if:"
echo "- Context7 provider is enabled in MCP configuration"
echo "- External search is being triggered during searches"
echo "- Sync ingestion is properly configured"