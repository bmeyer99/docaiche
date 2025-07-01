#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting E2E tests for Providers feature...${NC}"

# Check if container is running
if ! docker-compose ps admin-ui | grep -q "Up"; then
  echo -e "${RED}Error: admin-ui container is not running${NC}"
  echo "Please run: docker-compose up -d admin-ui"
  exit 1
fi

# Set test URL
export TEST_URL="http://localhost:4080"

# Create screenshots directory
mkdir -p screenshots

# Run the E2E tests
echo -e "${GREEN}Running E2E tests...${NC}"
npx jest --config=jest.e2e.config.js src/features/providers/__tests__/providers-page-complete-flow.e2e.test.js

# Check test results
if [ $? -eq 0 ]; then
  echo -e "${GREEN}✓ E2E tests passed successfully!${NC}"
else
  echo -e "${RED}✗ E2E tests failed${NC}"
  echo -e "${YELLOW}Screenshots saved in ./screenshots directory${NC}"
  exit 1
fi