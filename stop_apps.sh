#!/bin/bash

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${RED}Stopping all services...${NC}"

# Stop ngrok processes
echo -e "${GREEN}Stopping ngrok...${NC}"
pkill ngrok

# Stop Docker containers
echo -e "${GREEN}Stopping Docker containers...${NC}"
docker-compose down

echo -e "${GREEN}All services stopped!${NC}" 