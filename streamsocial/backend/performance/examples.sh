#!/bin/bash
################################################################################
# StreamSocial Performance - Quick Examples
# Copy-paste ready commands for common scenarios
################################################################################

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}StreamSocial Kafka - Quick Examples${NC}\n"
echo "Copy-paste any of these commands:\n"

echo -e "${YELLOW}[1] INITIAL SETUP${NC}"
echo "  chmod +x run.sh"
echo "  ./run.sh --setup"
echo ""

echo -e "${YELLOW}[2] START KAFKA (in Terminal 1)${NC}"
echo "  ./run.sh --kafka"
echo ""

echo -e "${YELLOW}[3] START API (in Terminal 2)${NC}"
echo "  ./run.sh --api"
echo ""

echo -e "${YELLOW}[4] GENERATE EVENTS (in Terminal 3)${NC}"
echo "  # Default: 1000 events/sec for 60 seconds"
echo "  ./run.sh --generate"
echo ""
echo "  # Custom: 5000 events/sec for 60 seconds"
echo "  ./run.sh --generate 5000 60"
echo ""
echo "  # High load: 10000 events/sec for 30 seconds"
echo "  ./run.sh --generate 10000 30"
echo ""

echo -e "${YELLOW}[5] MONITOR LAG (in Terminal 4)${NC}"
echo "  # Refresh every 5 seconds (default)"
echo "  ./run.sh --monitor"
echo ""
echo "  # Refresh every 2 seconds"
echo "  ./run.sh --monitor 2"
echo ""

echo -e "${YELLOW}[6] START CONSUMER INSTANCES${NC}"
echo "  # Start 1 consumer"
echo "  ./run.sh --consumers 1"
echo ""
echo "  # Start 3 consumers (auto-rebalancing)"
echo "  ./run.sh --consumers 3"
echo ""
echo "  # Start 5 consumers"
echo "  ./run.sh --consumers 5"
echo ""

echo -e "${YELLOW}[7] CHECK STATUS${NC}"
echo "  # Overall health"
echo "  ./run.sh --health"
echo ""
echo "  # List all consumer instances"
echo "  ./run.sh --list-consumers"
echo ""
echo "  # Consumer statistics"
echo "  ./run.sh --stats"
echo ""
echo "  # Consumer lag metrics"
echo "  ./run.sh --lag"
echo ""

echo -e "${YELLOW}[8] STOP & CLEANUP${NC}"
echo "  # Stop Kafka cluster"
echo "  ./run.sh --stop-kafka"
echo ""
echo "  # Stop all containers and volumes"
echo "  ./run.sh --cleanup"
echo ""

echo -e "${YELLOW}[9] AUTOMATED TESTS${NC}"
echo "  # Full load test (automatic)"
echo "  ./run.sh --load-test"
echo ""
echo "  # Scaling test with 3 consumers"
echo "  ./run.sh --scale-test 3"
echo ""
echo "  # Scaling test with 5 consumers"
echo "  ./run.sh --scale-test 5"
echo ""

echo -e "${YELLOW}[10] COMPLETE WORKFLOW EXAMPLE${NC}"
cat << 'EOF'

# Terminal 1: Start Kafka
./run.sh --kafka

# Terminal 2: Start API
./run.sh --api

# Terminal 3: Monitor (opens live dashboard)
./run.sh --monitor

# Terminal 4: Generate high-volume events
./run.sh --generate 5000 120

# Wait 30 seconds, then scale up consumers in Terminal 5
./run.sh --consumers 1
# Observe lag spike then recovery

# After 30 more seconds
./run.sh --consumers 2
# Observe lag decreasing further

# And again
./run.sh --consumers 3
# Observe lag continues to decrease

# Check final stats
./run.sh --stats
EOF
echo ""

echo -e "${YELLOW}[11] GET HELP${NC}"
echo "  ./run.sh --help"
echo ""

echo -e "${GREEN}Ready to start? Run the commands above in different terminals!${NC}"
