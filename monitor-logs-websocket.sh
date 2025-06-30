#!/bin/bash

# DocAIche Logs WebSocket Monitor Script
# This script monitors the logs page for WebSocket activity

# Default values
DEFAULT_URL="http://192.168.4.199:4080/dashboard/logs"
DEFAULT_DURATION=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo -e "${BLUE}DocAIche Logs WebSocket Monitor${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -d, --duration SEC     Duration in seconds (default: $DEFAULT_DURATION)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "This script monitors the logs page for WebSocket connections and activity."
}

# Parse command line arguments
DURATION=$DEFAULT_DURATION

while [[ $# -gt 0 ]]; do
    case $1 in
        -d|--duration)
            DURATION="$2"
            shift 2
            ;;
        -h|--help)
            show_help
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown option: $1${NC}"
            show_help
            exit 1
            ;;
    esac
done

# Check if node is installed
if ! command -v node &> /dev/null; then
    echo -e "${RED}Error: Node.js is not installed${NC}"
    echo "Please install Node.js to run this monitor"
    exit 1
fi

# Check if puppeteer is installed in admin-ui
if [ ! -d "admin-ui/node_modules/puppeteer" ]; then
    echo -e "${YELLOW}Installing Puppeteer...${NC}"
    cd admin-ui
    npm install puppeteer
    cd ..
fi

# Create reports directory
mkdir -p monitor-reports

# Run the monitor
echo -e "${GREEN}Starting WebSocket monitor for logs page...${NC}"
echo -e "URL: ${BLUE}$DEFAULT_URL${NC}"
echo -e "Duration: ${BLUE}$DURATION seconds${NC}"
echo ""

# Run the monitor script
cd admin-ui && node ../test-logs-websocket-monitor.js "$DEFAULT_URL" "$DURATION"

# Move reports and screenshots to reports directory
cd ..
mv logs-monitor-*.png monitor-reports/ 2>/dev/null || true
mv logs-websocket-report-*.json monitor-reports/ 2>/dev/null || true

echo ""
echo -e "${GREEN}Monitor complete!${NC}"
echo -e "Reports saved in: ${BLUE}monitor-reports/${NC}"

# Show latest report location
LATEST_REPORT=$(ls -t monitor-reports/logs-websocket-report-*.json | head -1)
if [ -n "$LATEST_REPORT" ]; then
    echo -e "Latest report: ${BLUE}$LATEST_REPORT${NC}"
    echo ""
    echo "To view the report:"
    echo "  cat $LATEST_REPORT | jq ."
fi