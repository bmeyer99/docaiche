#!/bin/bash

# Test Ollama connectivity from Docker containers
echo "Testing Ollama connectivity..."
echo "=============================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to test a URL
test_url() {
    local url=$1
    local desc=$2
    echo -n "Testing $desc ($url)... "
    
    # Test from inside the API container
    result=$(docker exec docaiche-api-1 python -c "
import httpx
import asyncio
import json

async def test():
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get('$url')
            if response.status_code == 200:
                data = response.json()
                models = data.get('models', [])
                print(json.dumps({'success': True, 'models': len(models)}))
            else:
                print(json.dumps({'success': False, 'status': response.status_code}))
    except Exception as e:
        print(json.dumps({'success': False, 'error': str(e)}))

asyncio.run(test())
" 2>/dev/null)
    
    if [ $? -eq 0 ] && [ -n "$result" ]; then
        success=$(echo "$result" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('success', False))")
        if [ "$success" = "True" ]; then
            models=$(echo "$result" | python3 -c "import sys, json; print(json.loads(sys.stdin.read()).get('models', 0))")
            echo -e "${GREEN}✓ Connected (${models} models found)${NC}"
            return 0
        else
            error=$(echo "$result" | python3 -c "import sys, json; d=json.loads(sys.stdin.read()); print(d.get('error', f\"HTTP {d.get('status', 'unknown')}\"))")
            echo -e "${RED}✗ Failed: $error${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Failed: Container error${NC}"
        return 1
    fi
}

# Test from host first
echo "1. Testing from host machine:"
echo -n "   Checking if Ollama is running... "
if command -v ollama &> /dev/null; then
    if ollama list &> /dev/null; then
        echo -e "${GREEN}✓ Ollama is running${NC}"
        ollama_running=true
    else
        echo -e "${RED}✗ Ollama is not running${NC}"
        echo -e "${YELLOW}   Start Ollama with: ollama serve${NC}"
        ollama_running=false
    fi
else
    echo -e "${RED}✗ Ollama is not installed${NC}"
    echo -e "${YELLOW}   Install from: https://ollama.ai${NC}"
    ollama_running=false
fi

echo ""
echo "2. Testing from Docker container (docaiche-api-1):"

# Common Ollama URLs to test
declare -A urls=(
    ["Docker bridge (Linux)"]="http://172.17.0.1:11434/api/tags"
    ["Docker bridge alt (Linux)"]="http://172.18.0.1:11434/api/tags"
    ["Host internal (Mac/Win)"]="http://host.docker.internal:11434/api/tags"
    ["Direct IP (example)"]="http://192.168.1.100:11434/api/tags"
)

working_url=""
for desc in "${!urls[@]}"; do
    url="${urls[$desc]}"
    if test_url "$url" "$desc"; then
        working_url="$url"
        break
    fi
done

echo ""
echo "3. Recommendations:"
echo "==================="

if [ -n "$working_url" ]; then
    base_url=$(echo "$working_url" | sed 's|/api/tags||')
    echo -e "${GREEN}✓ Ollama is accessible from Docker!${NC}"
    echo ""
    echo "Use this base URL in your AI Providers configuration:"
    echo -e "${YELLOW}$base_url${NC}"
else
    echo -e "${RED}✗ Ollama is not accessible from Docker containers.${NC}"
    echo ""
    
    if [ "$ollama_running" = "true" ]; then
        echo "Ollama is running on the host, but Docker containers cannot reach it."
        echo ""
        echo "Try these solutions:"
        echo ""
        echo "1. On Linux, find your Docker bridge IP:"
        echo "   ${YELLOW}docker network inspect bridge | grep Gateway${NC}"
        echo "   Then use: ${YELLOW}http://<gateway-ip>:11434${NC}"
        echo ""
        echo "2. Check if Ollama is binding to all interfaces:"
        echo "   ${YELLOW}OLLAMA_HOST=0.0.0.0 ollama serve${NC}"
        echo ""
        echo "3. Check firewall settings:"
        echo "   ${YELLOW}sudo ufw status${NC}"
        echo "   If enabled, allow port 11434: ${YELLOW}sudo ufw allow 11434${NC}"
    else
        echo "Please install and start Ollama first:"
        echo "1. Install from: ${YELLOW}https://ollama.ai${NC}"
        echo "2. Start Ollama: ${YELLOW}ollama serve${NC}"
        echo "3. Pull a model: ${YELLOW}ollama pull llama2${NC}"
    fi
fi

echo ""
echo "4. Current Docker network configuration:"
echo "========================================"
docker network inspect bridge | grep -E "(Gateway|Subnet)" | head -4

echo ""
echo "For more help, see: /home/lab/docaiche/OLLAMA_SETUP.md"