#!/bin/bash

# DocAIche Page Monitor Script
# This script monitors any page in the DocAIche app for issues

# Default values
DEFAULT_URL="http://192.168.4.199:4080/dashboard/providers"
DEFAULT_DURATION=30

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Help function
show_help() {
    echo -e "${BLUE}DocAIche Page Monitor${NC}"
    echo ""
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -u, --url URL          URL to monitor (default: $DEFAULT_URL)"
    echo "  -d, --duration SEC     Duration in seconds (default: $DEFAULT_DURATION)"
    echo "  -h, --help            Show this help message"
    echo ""
    echo "Examples:"
    echo "  # Monitor the providers page for 30 seconds"
    echo "  $0"
    echo ""
    echo "  # Monitor analytics page for 60 seconds"
    echo "  $0 -u http://192.168.4.199:4080/dashboard/analytics -d 60"
    echo ""
    echo "  # Monitor search page for 2 minutes"
    echo "  $0 --url http://192.168.4.199:4080/dashboard/search --duration 120"
    echo ""
    echo "Common pages to monitor:"
    echo "  - /dashboard/providers     - AI Providers configuration"
    echo "  - /dashboard/analytics     - Analytics dashboard"
    echo "  - /dashboard/search        - Search interface"
    echo "  - /dashboard/settings      - System settings"
    echo "  - /dashboard              - Main dashboard"
}

# Parse command line arguments
URL=$DEFAULT_URL
DURATION=$DEFAULT_DURATION

while [[ $# -gt 0 ]]; do
    case $1 in
        -u|--url)
            URL="$2"
            shift 2
            ;;
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

# Check if Puppeteer is installed
if [ ! -d "test-scripts/node_modules/puppeteer" ]; then
    echo -e "${YELLOW}Installing Puppeteer...${NC}"
    mkdir -p test-scripts
    cd test-scripts
    npm install puppeteer
    cd ..
fi

# Create reports directory
mkdir -p monitor-reports

# Run the monitor
echo -e "${GREEN}Starting page monitor...${NC}"
echo -e "URL: ${BLUE}$URL${NC}"
echo -e "Duration: ${BLUE}$DURATION seconds${NC}"
echo ""

# Run the monitor script and save output
node test-monitor-page.js "$URL" "$DURATION" 2>&1 | tee "monitor-reports/monitor-$(date +%Y%m%d-%H%M%S).log"

# Move screenshots and reports to the reports directory
mv screenshot-*.png monitor-reports/ 2>/dev/null || true
mv monitor-report-*.json monitor-reports/ 2>/dev/null || true

echo ""
echo -e "${GREEN}Monitor complete!${NC}"
echo -e "Reports saved in: ${BLUE}monitor-reports/${NC}"