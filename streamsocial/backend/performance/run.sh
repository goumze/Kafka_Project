#!/bin/bash
################################################################################
# StreamSocial Kafka Performance & Testing Suite
# All-in-one shell script for managing Kafka cluster, API, and consumers
# 
# Usage:
#   ./run.sh --help                    # Show this help
#   ./run.sh --kafka                   # Start Kafka cluster
#   ./run.sh --api                     # Start backend API
#   ./run.sh --generate [rate] [sec]   # Generate events
#   ./run.sh --monitor                 # Monitor consumer lag
#   ./run.sh --consumers [N]           # Start N consumer instances
#   ./run.sh --health                  # Health check
#
# Examples:
#   ./run.sh --kafka                   # Start 3-broker cluster
#   ./run.sh --api &                   # Start API in background
#   ./run.sh --generate 5000 60        # Generate 5000 events/sec for 60s
#   ./run.sh --monitor                 # Real-time monitoring
#   ./run.sh --consumers 3             # Start 3 consumer instances
#
################################################################################

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
BACKEND_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PROJECT_ROOT="$(dirname "$BACKEND_DIR")"
API_URL="${API_URL:-http://localhost:8000}"
KAFKA_BROKERS="${KAFKA_BROKERS:-localhost:9092,localhost:9093,localhost:9094}"

################################################################################
# Utility Functions
################################################################################

log() {
    echo -e "${BLUE}[$(date +'%H:%M:%S')]${NC} $1"
}

success() {
    echo -e "${GREEN}✓${NC} $1"
}

error() {
    echo -e "${RED}✗${NC} $1" >&2
}

warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════════╗"
    echo "║  $1"
    echo "╚════════════════════════════════════════════════════════════════╝"
    echo ""
}

show_help() {
    cat << 'EOF'
╔════════════════════════════════════════════════════════════════╗
║        StreamSocial Kafka Performance Testing Suite            ║
║                   All-in-One Command Center                    ║
╚════════════════════════════════════════════════════════════════╝

COMMANDS:
  --help, -h              Show this help message
  --setup                 Install dependencies and check setup
  --kafka                 Start Kafka cluster (docker-compose)
  --stop-kafka            Stop Kafka cluster
  --api                   Start backend API server
  --api-logs              Show API server logs
  --generate [RATE] [SEC] Generate bulk events
                          Default: 1000 events/sec, 60 seconds
                          Example: --generate 5000 120
  --monitor [INTERVAL]    Real-time consumer monitoring
                          Default: 5 second refresh
                          Example: --monitor 2
  --consumers [N]         Start N consumer instances
                          Default: 1
                          Example: --consumers 5
  --stop-consumers [N]    Stop N consumer instances
  --list-consumers        List all active consumer instances
  --health                Check API and consumer health
  --stats [INSTANCE]      Get consumer statistics
                          Example: --stats consumer-1
  --lag [INSTANCE]        Get consumer lag metrics
                          Example: --lag consumer-1
  --load-test             Run full load test (generates data + monitoring)
  --scale-test [N]        Run scaling test with N consumers
  --cleanup               Remove all containers and volumes

QUICK START:
  1. Setup:
     $ ./run.sh --setup
     $ ./run.sh --kafka

  2. Start API (new terminal):
     $ ./run.sh --api

  3. Generate events (new terminal):
     $ ./run.sh --generate 5000 60

  4. Monitor lag (new terminal):
     $ ./run.sh --monitor

  5. Scale consumers (new terminal):
     $ ./run.sh --consumers 3

WORKFLOWS:

  Basic Load Test:
    $ ./run.sh --kafka
    $ ./run.sh --api &
    $ ./run.sh --generate 1000 60
    $ ./run.sh --stats

  Scaling Test:
    $ ./run.sh --kafka
    $ ./run.sh --api &
    $ ./run.sh --scale-test 5

  Real-time Monitoring:
    $ ./run.sh --monitor --interval 2

ENVIRONMENT VARIABLES:
  API_URL              API endpoint (default: http://localhost:8000)
  KAFKA_BROKERS        Kafka bootstrap servers
  BACKEND_DIR          Backend directory path

EOF
}

################################################################################
# Kafka Management
################################################################################

start_kafka() {
    print_header "Starting Kafka Cluster"
    
    if ! command -v docker-compose &> /dev/null; then
        error "docker-compose not found. Please install Docker and Docker Compose."
        return 1
    fi
    
    cd "$PROJECT_ROOT"
    
    log "Starting Kafka cluster with docker-compose..."
    docker-compose up -d
    
    log "Waiting for brokers to be healthy..."
    for i in {1..30}; do
        if docker-compose ps | grep -q "kafka-1.*healthy"; then
            success "Kafka cluster is ready!"
            echo ""
            log "Kafka brokers:"
            echo "  - localhost:9092 (kafka-1)"
            echo "  - localhost:9093 (kafka-2)"
            echo "  - localhost:9094 (kafka-3)"
            echo ""
            log "Kafka UI: http://localhost:8080"
            return 0
        fi
        echo -n "."
        sleep 1
    done
    
    error "Kafka cluster failed to start"
    return 1
}

stop_kafka() {
    print_header "Stopping Kafka Cluster"
    cd "$PROJECT_ROOT"
    log "Stopping all containers..."
    docker-compose down
    success "Kafka cluster stopped"
}

################################################################################
# API Server Management
################################################################################

start_api() {
    print_header "Starting Backend API Server"
    
    cd "$BACKEND_DIR"
    
    if ! command -v python3 &> /dev/null; then
        error "Python 3 not found. Please install Python 3."
        return 1
    fi
    
    log "Checking dependencies..."
    if ! python3 -c "import fastapi" 2>/dev/null; then
        warning "FastAPI not installed. Installing dependencies..."
        pip install -q -r requirements.txt
    fi
    
    log "Starting API server on $API_URL..."
    python3 -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload
}

show_api_logs() {
    print_header "API Server Logs"
    docker logs -f streamsocial-api 2>/dev/null || {
        error "API container not running. Start with: ./run.sh --api"
    }
}

################################################################################
# Health Checks
################################################################################

check_health() {
    print_header "System Health Check"
    
    # Check Kafka
    log "Checking Kafka cluster..."
    if docker ps | grep -q kafka-1; then
        success "Kafka cluster is running"
    else
        error "Kafka cluster is not running"
    fi
    
    # Check API
    log "Checking API server..."
    if curl -s "$API_URL/health" > /dev/null 2>&1; then
        success "API server is responding"
        
        # Get consumer health
        log "Checking consumer instances..."
        if command -v jq &> /dev/null; then
            curl -s "$API_URL/consumer/health" | jq '.'
        else
            curl -s "$API_URL/consumer/health"
        fi
    else
        error "API server is not responding at $API_URL"
    fi
}

################################################################################
# Event Generation
################################################################################

generate_events() {
    local rate="${1:-1000}"
    local duration="${2:-60}"
    
    print_header "Bulk Event Generation"
    
    if ! curl -s "$API_URL/health" > /dev/null; then
        error "API server not responding at $API_URL"
        return 1
    fi
    
    local total_events=$((rate * duration))
    
    log "Configuration:"
    echo "  Events/sec: $rate"
    echo "  Duration: $duration seconds"
    echo "  Total events: $total_events"
    echo ""
    
    log "Generating events..."
    
    cd "$BACKEND_DIR"
    
    python3 - <<PYTHON
import requests
import json
import time
from datetime import datetime

api_url = "$API_URL"
rate = $rate
duration = $duration

payload = {
    "events_per_second": rate,
    "duration_seconds": duration,
    "num_unique_users": 10000,
    "num_unique_content": 50000
}

start = datetime.now()
response = requests.post(f"{api_url}/events/bulk/generate", json=payload)

if response.status_code == 200:
    result = response.json()
    elapsed = (datetime.now() - start).total_seconds()
    
    print("\n✓ Generation completed successfully!")
    print(f"\nResults:")
    stats = result.get('statistics', {})
    print(f"  Total Events: {stats.get('total_events', 0):,}")
    print(f"  Duration: {stats.get('duration_seconds', 0):.1f}s")
    print(f"  Throughput: {stats.get('average_throughput', 0):.0f} events/sec")
    print(f"  Errors: {stats.get('errors', 0)}")
else:
    print(f"✗ Generation failed: {response.status_code}")
    print(response.text)
PYTHON
}

################################################################################
# Consumer Management
################################################################################

start_consumers() {
    local num_consumers="${1:-1}"
    
    print_header "Starting Consumer Instances"
    
    log "Starting $num_consumers consumer instance(s)..."
    
    cd "$BACKEND_DIR"
    
    for i in $(seq 1 $num_consumers); do
        local instance_id="consumer-$i"
        log "Starting $instance_id..."
        
        python3 - <<PYTHON
import requests
import json

api_url = "$API_URL"
instance_id = "$instance_id"

response = requests.post(f"{api_url}/consumer/start", params={"instance_id": instance_id})
result = response.json()

if response.status_code == 200:
    print(f"✓ {instance_id} started")
else:
    print(f"✗ Failed to start {instance_id}: {result.get('error', 'Unknown error')}")
PYTHON
        
        sleep 1
    done
    
    success "All consumer instances started"
    echo ""
    log "Check status with: ./run.sh --list-consumers"
}

stop_consumers() {
    local num_consumers="${1:-1}"
    
    print_header "Stopping Consumer Instances"
    
    cd "$BACKEND_DIR"
    
    for i in $(seq 1 $num_consumers); do
        local instance_id="consumer-$i"
        log "Stopping $instance_id..."
        
        python3 - <<PYTHON
import requests

api_url = "$API_URL"
instance_id = "$instance_id"

response = requests.post(f"{api_url}/consumer/stop", params={"instance_id": instance_id})
if response.status_code == 200:
    print(f"✓ {instance_id} stopped")
PYTHON
    done
    
    success "All specified consumer instances stopped"
}

list_consumers() {
    print_header "Active Consumer Instances"
    
    cd "$BACKEND_DIR"
    
    python3 - <<PYTHON
import requests
import json

api_url = "$API_URL"

response = requests.get(f"{api_url}/consumer/instances")
if response.status_code == 200:
    data = response.json()
    
    print(f"Total Instances: {data.get('total_instances', 0)}")
    print(f"Consumer Group: {data.get('group_id', 'N/A')}\n")
    
    for inst in data.get('instances', []):
        status = "🟢 Running" if inst.get('running') else "🔴 Stopped"
        print(f"{status} {inst.get('instance_id')}")
        print(f"    Partitions: {inst.get('assigned_partitions')}")
        print(f"    Events: {inst.get('total_events'):,}")
        print(f"    Lag: {inst.get('total_lag'):,}\n")
else:
    print("✗ Failed to get instances")
PYTHON
}

get_stats() {
    local instance_id="$1"
    
    print_header "Consumer Statistics"
    
    cd "$BACKEND_DIR"
    
    python3 - <<PYTHON
import requests
import json

api_url = "$API_URL"
instance_id = "$instance_id"

params = {}
if instance_id:
    params['instance_id'] = instance_id

response = requests.get(f"{api_url}/consumer/stats", params=params)
if response.status_code == 200:
    data = response.json()
    
    print(f"Instance: {data.get('instance_id', 'primary')}")
    print(f"Status: {data.get('status', 'unknown')}")
    print(f"Total Events: {data.get('total_events', 0):,}")
    print(f"Uptime: {data.get('uptime_seconds', 0):.1f}s")
    print(f"Throughput: {data.get('throughput_events_per_sec', 0):.0f} events/sec")
    print(f"Assigned Partitions: {data.get('assigned_partitions', 0)}")
    print(f"Total Lag: {data.get('total_lag', 0):,}")
    print(f"Errors: {data.get('errors', 0)}")
    print(f"Handler Errors: {data.get('handler_errors', 0)}\n")
    
    print("Events by Topic:")
    for topic, count in data.get('events_by_topic', {}).items():
        pct = (count / data.get('total_events', 1) * 100) if data.get('total_events') else 0
        print(f"  {topic}: {count:,} ({pct:.1f}%)")
else:
    print("✗ Failed to get stats")
PYTHON
}

get_lag() {
    local instance_id="$1"
    
    print_header "Consumer Lag Metrics"
    
    cd "$BACKEND_DIR"
    
    python3 - <<PYTHON
import requests
import json

api_url = "$API_URL"
instance_id = "$instance_id"

params = {}
if instance_id:
    params['instance_id'] = instance_id

response = requests.get(f"{api_url}/consumer/lag", params=params)
if response.status_code == 200:
    data = response.json()
    
    print(f"Instance: {data.get('instance_id', 'primary')}")
    print(f"Total Lag: {data.get('total_lag', 0):,} messages\n")
    
    print("Lag by Topic:")
    for topic, partitions in data.get('lag_by_topic', {}).items():
        total_lag = sum(p['lag'] for p in partitions.values())
        print(f"\n  {topic}:")
        print(f"    Total Lag: {total_lag:,}")
        print(f"    Partitions: {len(partitions)}")
        
        # Show top 5 partitions with highest lag
        top_partitions = sorted(
            [(pid, p['lag']) for pid, p in partitions.items()],
            key=lambda x: x[1],
            reverse=True
        )[:5]
        
        if top_partitions:
            print(f"    Top 5 by Lag:")
            for pid, lag in top_partitions:
                print(f"      Partition {pid}: {lag:,}")
else:
    print("✗ Failed to get lag metrics")
PYTHON
}

################################################################################
# Monitoring
################################################################################

monitor() {
    local interval="${1:-5}"
    
    print_header "Real-Time Consumer Monitoring (refresh: ${interval}s)"
    log "Press Ctrl+C to exit\n"
    
    cd "$BACKEND_DIR"
    
    while true; do
        clear
        echo "StreamSocial Kafka - Live Monitor ($(date +'%Y-%m-%d %H:%M:%S'))"
        echo "Refresh interval: ${interval}s (Press Ctrl+C to exit)"
        echo "════════════════════════════════════════════════════════════════════"
        echo ""
        
        python3 - <<PYTHON
import requests
import json
from datetime import datetime

api_url = "$API_URL"

# Get stats
stats_response = requests.get(f"{api_url}/consumer/stats")
lag_response = requests.get(f"{api_url}/consumer/lag")

if stats_response.status_code == 200:
    stats = stats_response.json()
    
    print(f"Instances: {stats.get('instance_id', 'primary')}")
    print(f"Status: {stats.get('status', 'unknown')}")
    print(f"Total Events: {stats.get('total_events', 0):,}")
    print(f"Throughput: {stats.get('throughput_events_per_sec', 0):.0f} events/sec")
    print(f"Uptime: {stats.get('uptime_seconds', 0):.1f}s")
    print(f"Assigned Partitions: {stats.get('assigned_partitions', 0)}")
    print(f"Errors: {stats.get('errors', 0)}")
    print("")
    
    if lag_response.status_code == 200:
        lag = lag_response.json()
        print(f"CONSUMER LAG")
        print(f"Total Lag: {lag.get('total_lag', 0):,} messages")
        print("")
        
        for topic, partitions in lag.get('lag_by_topic', {}).items():
            total_lag = sum(p['lag'] for p in partitions.values())
            print(f"{topic}:")
            print(f"  Partitions: {len(partitions)}, Total Lag: {total_lag:,}")
else:
    print("⚠ API not responding")
PYTHON
        
        sleep $interval
    done
}

################################################################################
# Automated Tests
################################################################################

load_test() {
    print_header "Full Load Test Workflow"
    
    log "This test will:"
    echo "  1. Generate 5000 events/sec for 60 seconds"
    echo "  2. Monitor consumer lag"
    echo "  3. Display final statistics"
    echo ""
    
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 1
    fi
    
    # Start monitoring in background
    log "Starting monitoring..."
    cd "$BACKEND_DIR"
    
    # Generate events
    log "Generating events..."
    python3 - <<PYTHON &
import requests
import time

api_url = "$API_URL"
payload = {
    "events_per_second": 5000,
    "duration_seconds": 60,
    "num_unique_users": 50000,
    "num_unique_content": 50000
}

requests.post(f"{api_url}/events/bulk/generate", json=payload)
PYTHON
    
    gen_pid=$!
    
    # Monitor for 70 seconds
    for i in {1..14}; do
        sleep 5
        clear
        echo "Load Test Progress: $((i*5))/70 seconds"
        echo "════════════════════════════════════════════════════════════════════"
        
        python3 - <<PYTHON
import requests
stats = requests.get("$API_URL/consumer/stats").json()
lag = requests.get("$API_URL/consumer/lag").json()
print(f"Events Processed: {stats.get('total_events', 0):,}")
print(f"Throughput: {stats.get('throughput_events_per_sec', 0):.0f} events/sec")
print(f"Total Lag: {lag.get('total_lag', 0):,}")
PYTHON
    done
    
    wait $gen_pid
    
    # Final stats
    echo ""
    get_stats
}

scale_test() {
    local num_consumers="${1:-1}"
    
    print_header "Consumer Scaling Test"
    
    if [ $num_consumers -lt 1 ]; then
        error "Number of consumers must be >= 1"
        return 1
    fi
    
    log "This test will:"
    echo "  1. Generate sustained load"
    echo "  2. Start consumers one at a time"
    echo "  3. Show performance impact of scaling"
    echo ""
    
    read -p "Continue? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 1
    fi
    
    # Start event generation
    log "Starting sustained event generation (5000 events/sec)..."
    cd "$BACKEND_DIR"
    
    python3 - <<PYTHON &
import requests
requests.post("$API_URL/events/bulk/generate", json={
    "events_per_second": 5000,
    "duration_seconds": $((10 * num_consumers + 30)),
    "num_unique_users": 50000,
    "num_unique_content": 50000
})
PYTHON
    
    gen_pid=$!
    
    # Start consumers one by one
    for i in $(seq 1 $num_consumers); do
        log "Monitoring for 10 seconds..."
        
        for s in {1..10}; do
            sleep 1
            clear
            echo "Scaling Test - Monitoring Gap Before Instance $i"
            echo "════════════════════════════════════════════════════════════════════"
            
            python3 - <<PYTHON
import requests
stats = requests.get("$API_URL/consumer/stats").json()
lag = requests.get("$API_URL/consumer/lag").json()
print(f"Events: {stats.get('total_events', 0):,}")
print(f"Lag: {lag.get('total_lag', 0):,}")
PYTHON
        done
        
        log "Starting consumer instance $i..."
        start_consumers 1
        
        log "Monitoring for 20 seconds after scaling..."
        for s in {1..20}; do
            sleep 1
            clear
            echo "Scaling Test - After Starting Instance $i"
            echo "════════════════════════════════════════════════════════════════════"
            
            python3 - <<PYTHON
import requests
stats = requests.get("$API_URL/consumer/stats").json()
lag = requests.get("$API_URL/consumer/lag").json()
instances = requests.get("$API_URL/consumer/instances").json()
print(f"Active Instances: {instances.get('total_instances', 0)}")
print(f"Events: {stats.get('total_events', 0):,}")
print(f"Throughput: {stats.get('throughput_events_per_sec', 0):.0f} events/sec")
print(f"Lag: {lag.get('total_lag', 0):,}")
PYTHON
        done
    done
    
    wait $gen_pid
    success "Scaling test completed"
}

cleanup() {
    print_header "Cleanup"
    
    read -p "Remove all containers and volumes? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        return 1
    fi
    
    log "Stopping all containers..."
    cd "$PROJECT_ROOT"
    docker-compose down -v
    
    success "Cleanup completed"
}

################################################################################
# Setup & Dependencies
################################################################################

setup() {
    print_header "Setup & Dependency Check"
    
    log "Checking prerequisites...\n"
    
    # Check Docker
    if command -v docker &> /dev/null; then
        success "Docker is installed ($(docker --version))"
    else
        error "Docker is not installed"
        return 1
    fi
    
    # Check Docker Compose
    if command -v docker-compose &> /dev/null; then
        success "Docker Compose is installed ($(docker-compose --version | head -1))"
    else
        error "Docker Compose is not installed"
        return 1
    fi
    
    # Check Python
    if command -v python3 &> /dev/null; then
        success "Python 3 is installed ($(python3 --version))"
    else
        error "Python 3 is not installed"
        return 1
    fi
    
    # Check pip
    if command -v pip &> /dev/null; then
        success "pip is installed"
    else
        error "pip is not installed"
        return 1
    fi
    
    # Install Python dependencies
    log "\nInstalling Python dependencies..."
    pip install -q -r "$BACKEND_DIR/requirements.txt"
    success "Python dependencies installed"
    
    echo ""
    success "Setup completed successfully!"
    echo ""
    log "Next steps:"
    echo "  1. Start Kafka: ./run.sh --kafka"
    echo "  2. Start API: ./run.sh --api"
    echo "  3. Generate events: ./run.sh --generate 5000 60"
}

################################################################################
# Main Entry Point
################################################################################

main() {
    if [ $# -eq 0 ]; then
        show_help
        return 0
    fi
    
    case "$1" in
        --help|-h)
            show_help
            ;;
        --setup)
            setup
            ;;
        --kafka)
            start_kafka
            ;;
        --stop-kafka)
            stop_kafka
            ;;
        --api)
            start_api
            ;;
        --api-logs)
            show_api_logs
            ;;
        --generate)
            generate_events "$2" "$3"
            ;;
        --monitor)
            monitor "${2:-5}"
            ;;
        --consumers)
            start_consumers "${2:-1}"
            ;;
        --stop-consumers)
            stop_consumers "${2:-1}"
            ;;
        --list-consumers)
            list_consumers
            ;;
        --health)
            check_health
            ;;
        --stats)
            get_stats "$2"
            ;;
        --lag)
            get_lag "$2"
            ;;
        --load-test)
            load_test
            ;;
        --scale-test)
            scale_test "${2:-1}"
            ;;
        --cleanup)
            cleanup
            ;;
        *)
            error "Unknown command: $1"
            echo ""
            show_help
            return 1
            ;;
    esac
}

# Run main function
main "$@"
