#!/bin/bash

# StreamSocial End-to-End Testing Script
# Demonstrates simultaneous event production and consumption
# Usage: ./test_end_to_end.sh

set -e

BASE_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  StreamSocial End-to-End Event Flow Test                       ║"
echo "║  Producer → Kafka Topic → Consumer (Real-time Demo)            ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Function to print section headers
section() {
    echo -e "\n${BLUE}▶ $1${NC}"
}

# Function to print info
info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Function to print success
success() {
    echo -e "${GREEN}[✓]${NC} $1"
}

# Function to print error
error() {
    echo -e "${RED}[✗]${NC} $1"
}

# ========== PHASE 1: VERIFY BACKEND IS RUNNING ==========
section "Phase 1: Verifying Backend Service"

if curl -s $BASE_URL/health | jq -e '.status == "healthy"' > /dev/null 2>&1; then
    success "Backend is running on $BASE_URL"
else
    error "Backend is not running! Start it with: python streamsocial/backend/main.py"
    exit 1
fi

# ========== PHASE 2: CHECK INITIAL STATE ==========
section "Phase 2: Checking Initial Consumer State"

INITIAL_STATS=$(curl -s $BASE_URL/consumer/stats)
INITIAL_COUNT=$(echo $INITIAL_STATS | jq '.total_events_processed')
info "Initial events processed: $INITIAL_COUNT"
echo "$INITIAL_STATS" | jq '{status: .status, running: .running, total_events: .total_events_processed}'

# ========== PHASE 3: GENERATE TEST EVENTS ==========
section "Phase 3: Generating Test Events (Producer)"

# Array of test events
declare -a USERS=("alice" "bob" "charlie" "diana" "eve")
declare -a EMAILS=("alice@example.com" "bob@example.com" "charlie@example.com" "diana@example.com" "eve@example.com")

info "Sending 5 user registration events..."

for i in "${!USERS[@]}"; do
    USER="${USERS[$i]}"
    EMAIL="${EMAILS[$i]}"
    
    RESPONSE=$(curl -s -X POST $BASE_URL/events/user/register \
        -H "Content-Type: application/json" \
        -d "{\"username\":\"$USER\",\"email\":\"$EMAIL\"}")
    
    USER_ID=$(echo $RESPONSE | jq -r '.user_id')
    EVENT_ID=$(echo $RESPONSE | jq -r '.event_id')
    
    echo -e "  ${GREEN}→${NC} Event #$((i+1)): User '$USER' registered (Event ID: ${EVENT_ID:0:8})..."
    sleep 0.5
done

# ========== PHASE 4: MONITOR CONSUMPTION IN REAL-TIME ==========
section "Phase 4: Monitoring Real-Time Event Consumption"

info "Fetching recent events from consumer..."
echo ""

RECENT_EVENTS=$(curl -s $BASE_URL/events/recent)
EVENTS_COUNT=$(echo $RECENT_EVENTS | jq '.count')
EVENTS_IN_MEMORY=$(echo $RECENT_EVENTS | jq '.events_in_memory')

info "Consumer statistics:"
echo "$RECENT_EVENTS" | jq '{events_processed: .count, in_memory: .events_in_memory}'

echo ""
info "Recent events consumed:"
echo "$RECENT_EVENTS" | jq '.events[] | {event_id: .event_id[0:8], type: .event_type, user: .event_data.username}' | head -20

# ========== PHASE 5: VERIFY EVENT FLOW ==========
section "Phase 5: Verifying Event Flow"

CONSUMER_STATS=$(curl -s $BASE_URL/consumer/stats)
FINAL_COUNT=$(echo $CONSUMER_STATS | jq '.total_events_processed')
EVENTS_ADDED=$((FINAL_COUNT - INITIAL_COUNT))

info "Initial events in consumer: $INITIAL_COUNT"
info "Final events in consumer: $FINAL_COUNT"
info "New events processed: $EVENTS_ADDED"

if [ $EVENTS_ADDED -gt 0 ]; then
    success "Event flow verified! $EVENTS_ADDED events successfully produced and consumed"
else
    error "No events were consumed. Check if consumer is running."
fi

echo "$CONSUMER_STATS" | jq '{status: .status, running: .running, total_processed: .total_events_processed, lag: .consumer_lag}'

# ========== PHASE 6: CLUSTER HEALTH CHECK ==========
section "Phase 6: Verifying Cluster Health"

HEALTH=$(curl -s $BASE_URL/cluster/health)
HEALTHY=$(echo $HEALTH | jq '.healthy_count')
TOTAL=$(echo $HEALTH | jq '.total_brokers')

info "Cluster health: $HEALTHY/$TOTAL brokers healthy"
echo "$HEALTH" | jq '.brokers | to_entries[] | "\(.key): \(.value.status)"'

# ========== PHASE 7: CONSUMER LAG ANALYSIS ==========
section "Phase 7: Consumer Lag Analysis"

LAG_INFO=$(curl -s $BASE_URL/cluster/consumer-lag)
info "Consumer group: streamsocial_event_consumers"
echo "$LAG_INFO" | jq '.lag_info | .[]' | head -10

# ========== FINAL SUMMARY ==========
echo ""
echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║ TEST SUMMARY                                                    ║"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

echo -e "${GREEN}✓ Producer (Event Sender)${NC}"
echo "  • Sent 5 user registration events"
echo "  • Events: alice, bob, charlie, diana, eve"

echo ""
echo -e "${GREEN}✓ Consumer (Event Receiver)${NC}"
echo "  • Status: Active"
echo "  • Total events processed: $FINAL_COUNT"
echo "  • New events consumed: $EVENTS_ADDED"
echo "  • Events in memory: $EVENTS_IN_MEMORY"

echo ""
echo -e "${GREEN}✓ Kafka Cluster${NC}"
echo "  • Brokers: $HEALTHY/$TOTAL healthy"
echo "  • Topic: streamsocial_events"
echo "  • Consumer Group: streamsocial_event_consumers"

echo ""
echo -e "${GREEN}✓ Event Flow${NC}"
if [ $EVENTS_ADDED -gt 0 ]; then
    echo "  • Status: ${GREEN}WORKING${NC}"
    echo "  • Flow: Events sent → Kafka → Consumer received"
else
    echo "  • Status: ${RED}FAILED${NC}"
fi

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗"
echo "║ Next Steps                                                      ║"
echo "╚════════════════════════════════════════════════════════════════╝${NC}"
echo ""
echo "1. View live consumer: curl $BASE_URL/events/recent | jq"
echo "2. Check consumer stats: curl $BASE_URL/consumer/stats | jq"
echo "3. Test failure scenarios: ./test_phase_6_7.sh"
echo "4. Monitor cluster: curl $BASE_URL/cluster/health | jq"
echo ""
