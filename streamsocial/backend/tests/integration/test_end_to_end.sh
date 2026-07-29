#!/bin/bash

# StreamSocial Controller API Testing Suite
# Tests all endpoints across Health, Event, Consumer, and Cluster controllers
# Usage: 
#   ./test_end_to_end.sh              # Run all tests
#   ./test_end_to_end.sh health       # Run only health controller tests
#   ./test_end_to_end.sh event        # Run only event controller tests
#   ./test_end_to_end.sh consumer     # Run only consumer controller tests
#   ./test_end_to_end.sh cluster      # Run only cluster controller tests
#   ./test_end_to_end.sh list         # Show available test options

set +e

BASE_URL="http://localhost:8000"

# Colors
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

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
    ((TESTS_PASSED++))
}

# Function to print error
error() {
    echo -e "${RED}[✗]${NC} $1"
    ((TESTS_FAILED++))
}

# ═══════════════════════════════════════════════════════════════════
# HEALTH CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════

test_health_check() {
    section "GET /health - Health Check"
    RESPONSE=$(curl -s $BASE_URL/health)
    
    if echo "$RESPONSE" | jq -e '.status == "healthy"' > /dev/null 2>&1; then
        success "Backend is healthy"
        echo "$RESPONSE" | jq '{status: .status, service: .service}'
    else
        error "Health check failed"
        echo "$RESPONSE" | jq '.'
    fi
}

test_root_endpoint() {
    section "GET / - Root Endpoint (API Info)"
    RESPONSE=$(curl -s $BASE_URL/)
    
    if echo "$RESPONSE" | jq -e '.service' > /dev/null 2>&1; then
        success "Root endpoint returns API info"
        echo "$RESPONSE" | jq '{service: .service, version: .version, kafka_integration: .kafka_integration}'
    else
        error "Root endpoint failed"
        echo "$RESPONSE" | jq '.'
    fi
}

# ═══════════════════════════════════════════════════════════════════
# EVENT CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════

test_register_user() {
    section "POST /events/user/register - User Registration"
    
    declare -a USERS=("alice" "bob" "charlie")
    declare -a EMAILS=("alice@example.com" "bob@example.com" "charlie@example.com")
    
    info "Publishing 3 user registration events..."
    
    for i in "${!USERS[@]}"; do
        USER="${USERS[$i]}"
        EMAIL="${EMAILS[$i]}"
        
        RESPONSE=$(curl -s -X POST $BASE_URL/events/user/register \
            -H "Content-Type: application/json" \
            -d "{\"username\":\"$USER\",\"email\":\"$EMAIL\",\"source\":\"test\"}")
        
        if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
            USER_ID=$(echo $RESPONSE | jq -r '.user_id')
            success "Event published for user '$USER' (ID: ${USER_ID:0:8})"
        else
            error "Failed to publish event for user '$USER'"
            echo "$RESPONSE" | jq '.'
        fi
        sleep 0.3
    done
}

test_get_recent_events() {
    section "GET /events/recent - Get Recent Events"
    RESPONSE=$(curl -s $BASE_URL/events/recent)
    
    if echo "$RESPONSE" | jq -e '.success == true' > /dev/null 2>&1; then
        success "Retrieved recent events"
        echo "$RESPONSE" | jq '{success: .success, event_count: .count, in_memory: .events_in_memory, message: .message}'
    else
        error "Failed to get recent events"
        echo "$RESPONSE" | jq '.'
    fi
}

# ═══════════════════════════════════════════════════════════════════
# CONSUMER CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════

test_consumer_stats() {
    section "GET /consumer/stats - Consumer Statistics"
    RESPONSE=$(curl -s $BASE_URL/consumer/stats)
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Retrieved consumer statistics"
        echo "$RESPONSE" | jq '{status: .status, running: .running, total_events_processed: .total_events_processed, events_in_memory: .events_in_memory}'
    else
        error "Failed to get consumer stats"
        echo "$RESPONSE" | jq '.'
    fi
}

test_consumer_start() {
    section "POST /consumer/start - Start Consumer"
    RESPONSE=$(curl -s -X POST $BASE_URL/consumer/start \
        -H "Content-Type: application/json")
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Consumer start endpoint called"
        echo "$RESPONSE" | jq '{status: .status, message: .message}'
    else
        error "Failed to start consumer"
        echo "$RESPONSE" | jq '.'
    fi
}

test_consumer_stop() {
    section "POST /consumer/stop - Stop Consumer"
    RESPONSE=$(curl -s -X POST $BASE_URL/consumer/stop \
        -H "Content-Type: application/json")
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Consumer stop endpoint called"
        echo "$RESPONSE" | jq '{status: .status, message: .message}'
    else
        error "Failed to stop consumer"
        echo "$RESPONSE" | jq '.'
    fi
}

# ═══════════════════════════════════════════════════════════════════
# CLUSTER CONTROLLER TESTS
# ═══════════════════════════════════════════════════════════════════

test_cluster_health() {
    section "GET /cluster/health - Cluster Health Status"
    RESPONSE=$(curl -s $BASE_URL/cluster/health)
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Retrieved cluster health"
        HEALTHY=$(echo "$RESPONSE" | jq '.healthy_count')
        TOTAL=$(echo "$RESPONSE" | jq '.total_brokers')
        echo "$RESPONSE" | jq "{status: .status, healthy_brokers: .healthy_count, total_brokers: .total_brokers}"
    else
        error "Failed to get cluster health"
        echo "$RESPONSE" | jq '.'
    fi
}

test_cluster_metadata() {
    section "GET /cluster/metadata - Cluster Metadata"
    RESPONSE=$(curl -s $BASE_URL/cluster/metadata)
    
    if echo "$RESPONSE" | jq -e '.topic' > /dev/null 2>&1; then
        success "Retrieved cluster metadata"
        echo "$RESPONSE" | jq '{topic: .topic, brokers: .brokers | length, bootstrap_servers: .bootstrap_servers | length, replication_factor: .replication_factor}'
    else
        error "Failed to get cluster metadata"
        echo "$RESPONSE" | jq '.'
    fi
}

test_cluster_partitions() {
    section "GET /cluster/partitions - Partition Leadership"
    RESPONSE=$(curl -s $BASE_URL/cluster/partitions)
    
    if echo "$RESPONSE" | jq -e '.topic' > /dev/null 2>&1; then
        success "Retrieved partition information"
        echo "$RESPONSE" | jq '{topic: .topic, partition_details_count: .partition_details | length}'
    else
        error "Failed to get partition info"
        echo "$RESPONSE" | jq '.'
    fi
}

test_consumer_lag() {
    section "GET /cluster/consumer-lag - Consumer Lag"
    RESPONSE=$(curl -s $BASE_URL/cluster/consumer-lag)
    
    if echo "$RESPONSE" | jq -e '.consumer_group' > /dev/null 2>&1; then
        success "Retrieved consumer lag"
        echo "$RESPONSE" | jq '{consumer_group: .consumer_group, lag_info_entries: .lag_info | length}'
    else
        error "Failed to get consumer lag"
        echo "$RESPONSE" | jq '.'
    fi
}

test_simulate_broker_failure() {
    section "POST /cluster/simulate-failure - Simulate Broker Failure"
    info "Simulating kafka-broker-2 failure..."
    
    RESPONSE=$(curl -s -X POST $BASE_URL/cluster/simulate-failure \
        -H "Content-Type: application/json" \
        -d '{"broker_name":"kafka-broker-2"}')
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Broker failure simulated"
        echo "$RESPONSE" | jq '{status: .status, broker: .broker, action: .action}'
        sleep 2
    else
        error "Failed to simulate broker failure"
        echo "$RESPONSE" | jq '.'
    fi
}

test_recover_broker_failure() {
    section "POST /cluster/recover-failure - Recover Broker"
    info "Recovering kafka-broker-2..."
    
    RESPONSE=$(curl -s -X POST $BASE_URL/cluster/recover-failure \
        -H "Content-Type: application/json" \
        -d '{"broker_name":"kafka-broker-2"}')
    
    if echo "$RESPONSE" | jq -e '.status' > /dev/null 2>&1; then
        success "Broker recovery initiated"
        echo "$RESPONSE" | jq '{status: .status, broker: .broker, action: .action}'
        sleep 2
    else
        error "Failed to recover broker"
        echo "$RESPONSE" | jq '.'
    fi
}

# ═══════════════════════════════════════════════════════════════════
# TEST SUITES - GROUP BY CONTROLLER
# ═══════════════════════════════════════════════════════════════════

test_health_controller() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  HEALTH CONTROLLER TESTS                                       ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    test_health_check
    test_root_endpoint
}

test_event_controller() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  EVENT CONTROLLER TESTS                                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    test_register_user
    test_get_recent_events
}

test_consumer_controller() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  CONSUMER CONTROLLER TESTS                                     ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    test_consumer_stats
    test_consumer_start
    test_consumer_stop
}

test_cluster_controller() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  CLUSTER CONTROLLER TESTS                                      ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    test_cluster_health
    test_cluster_metadata
    test_cluster_partitions
    test_consumer_lag
    test_simulate_broker_failure
    test_recover_broker_failure
}

test_all() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  StreamSocial Complete Controller API Test Suite               ║"
    echo "║  Testing all endpoints across all controllers                  ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    
    test_health_controller
    test_event_controller
    test_consumer_controller
    test_cluster_controller
}

# ═══════════════════════════════════════════════════════════════════
# HELP AND TEST LISTING
# ═══════════════════════════════════════════════════════════════════

show_help() {
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  StreamSocial Controller API Test Suite                        ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo ""
    echo -e "${BLUE}USAGE:${NC}"
    echo "  ./test_end_to_end.sh [OPTION]"
    echo ""
    echo -e "${BLUE}OPTIONS:${NC}"
    echo "  (no args)      Run all controller tests"
    echo "  health         Test Health Controller only"
    echo "  event          Test Event Controller only"
    echo "  consumer       Test Consumer Controller only"
    echo "  cluster        Test Cluster Controller only"
    echo "  list           Show this help message"
    echo "  help           Show this help message"
    echo ""
    echo -e "${BLUE}EXAMPLES:${NC}"
    echo "  ./test_end_to_end.sh                # Run all tests"
    echo "  ./test_end_to_end.sh health         # Only health tests"
    echo "  ./test_end_to_end.sh cluster        # Only cluster tests"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# MAIN - BACKEND VERIFICATION AND ROUTING
# ═══════════════════════════════════════════════════════════════════

verify_backend() {
    section "Verifying Backend Service"
    
    if curl -s $BASE_URL/health > /dev/null 2>&1; then
        success "Backend is running on $BASE_URL"
    else
        error "Backend is NOT running!"
        echo ""
        echo -e "${YELLOW}Please start the backend first:${NC}"
        echo "  cd /workspaces/Kafka_Project/streamsocial/backend"
        echo "  python main.py"
        echo ""
        exit 1
    fi
}

print_summary() {
    echo ""
    echo -e "${CYAN}"
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  TEST RESULTS SUMMARY                                          ║"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
    echo -e "${GREEN}✓ PASSED: $TESTS_PASSED${NC}"
    echo -e "${RED}✗ FAILED: $TESTS_FAILED${NC}"
    echo ""
}

# ═══════════════════════════════════════════════════════════════════
# MAIN EXECUTION - ARGUMENT ROUTING
# ═══════════════════════════════════════════════════════════════════

OPTION="${1:---all}"

case "$OPTION" in
    health)
        verify_backend
        test_health_controller
        print_summary
        ;;
    event)
        verify_backend
        test_event_controller
        print_summary
        ;;
    consumer)
        verify_backend
        test_consumer_controller
        print_summary
        ;;
    cluster)
        verify_backend
        test_cluster_controller
        print_summary
        ;;
    list|help|--help|-h)
        show_help
        ;;
    --all|"")
        verify_backend
        test_all
        print_summary
        ;;
    *)
        echo -e "${RED}Unknown option: $OPTION${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac

exit 0
