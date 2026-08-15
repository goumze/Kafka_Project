#!/bin/bash

# StreamSocial Docker Compose Management Script (Linux/Mac/WSL)
# Orchestrates the full Kafka + Spring Boot microservices stack
#
# Usage:
#   ./manage-streamsocial.sh build
#   ./manage-streamsocial.sh start
#   ./manage-streamsocial.sh stop
#   ./manage-streamsocial.sh logs [service]
#   ./manage-streamsocial.sh status
#   ./manage-streamsocial.sh scale <replicas>
#   ./manage-streamsocial.sh demo

set -e

# ========================================
# Configuration
# ========================================

COMPOSE_FILE="streamsocial/Dockerfile"
STACK_NAME="streamsocial"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# ========================================
# Helper Functions
# ========================================

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${CYAN}ℹ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

show_header() {
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo "║  StreamSocial Docker Compose Manager     ║"
    echo "║  Kafka + Spring Boot Microservices       ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
}

test_docker() {
    if ! command -v docker &> /dev/null; then
        return 1
    fi
    return 0
}

test_docker_compose() {
    if ! docker compose version &> /dev/null; then
        return 1
    fi
    return 0
}

test_compose_file() {
    if [ ! -f "$COMPOSE_FILE" ]; then
        return 1
    fi
    return 0
}

# ========================================
# Main Functions
# ========================================

start_stack() {
    print_info "Starting StreamSocial Stack..."
    print_info "Building and starting all services..."
    
    docker compose -f "$COMPOSE_FILE" up -d --build
    
    print_info "Waiting for services to be healthy (30 seconds)..."
    sleep 30
    
    print_success "Stack started successfully"
    show_status
}

build_stack() {
    print_info "Building Docker images..."
    docker compose -f "$COMPOSE_FILE" build
    print_success "Build completed successfully"
}

stop_stack() {
    print_info "Stopping StreamSocial Stack..."
    docker compose -f "$COMPOSE_FILE" down
    print_success "Stack stopped"
}

restart_stack() {
    print_info "Restarting StreamSocial Stack..."
    docker compose -f "$COMPOSE_FILE" restart
    print_success "Stack restarted"
}

show_logs() {
    if [ -z "$1" ]; then
        print_info "Showing logs for all services (Ctrl+C to exit)..."
        docker compose -f "$COMPOSE_FILE" logs -f
    else
        print_info "Showing logs for service: $1"
        docker compose -f "$COMPOSE_FILE" logs -f "$1"
    fi
}

show_status() {
    print_info "Current Stack Status:"
    echo ""
    docker compose -f "$COMPOSE_FILE" ps
    echo ""
}

show_processes() {
    print_info "Listing all containers:"
    docker compose -f "$COMPOSE_FILE" ps -a
}

scale_service() {
    local replicas=$1
    
    if [ -z "$replicas" ]; then
        print_error "Replica count required for scale action"
        print_info "Usage: $0 scale <count>"
        exit 1
    fi
    
    print_info "Scaling kafka-consumer to $replicas replicas..."
    docker compose -f "$COMPOSE_FILE" up -d --scale kafka-consumer="$replicas"
    
    print_success "Service scaled to $replicas replicas"
    sleep 3
    show_status
}

run_demo() {
    show_header
    print_info "Starting StreamSocial Demo..."
    echo ""
    
    # Start stack
    echo -e "${CYAN}Step 1: Starting the stack...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d --build
    print_success "Stack starting (waiting for Kafka brokers to be healthy)..."
    sleep 30
    
    # Show status
    echo ""
    echo -e "${CYAN}Step 2: Stack Status:${NC}"
    docker compose -f "$COMPOSE_FILE" ps
    
    # Generate events
    echo ""
    echo -e "${CYAN}Step 3: Generating test events...${NC}"
    print_info "Sending 100 test events to Kafka..."
    
    # Wait for API to be ready
    sleep 10
    
    # Try to generate events (might fail if API not fully ready, that's ok)
    if curl -s -X POST "http://localhost:8000/api/events/bulk/generate?count=100" > /dev/null 2>&1; then
        print_success "Events generated successfully"
    else
        print_warning "Could not generate events yet (API might still be starting)"
        print_info "Try again in a few seconds when the API is fully ready"
    fi
    
    # Show Kafka UI
    echo ""
    echo -e "${CYAN}Step 4: Access Services:${NC}"
    print_info "Kafka UI:      http://localhost:8080"
    print_info "API Health:    http://localhost:8000/actuator/health"
    print_info "API Metrics:   http://localhost:8000/actuator/metrics"
    
    # Scale consumer
    echo ""
    echo -e "${CYAN}Step 5: Scaling consumer workers...${NC}"
    docker compose -f "$COMPOSE_FILE" up -d --scale kafka-consumer=3
    print_success "Scaled kafka-consumer to 3 replicas"
    
    # Show final status
    echo ""
    echo -e "${CYAN}Final Stack Status:${NC}"
    docker compose -f "$COMPOSE_FILE" ps
    
    echo ""
    echo "╔════════════════════════════════════════════╗"
    echo -e "║ ${GREEN}Demo Started Successfully!${NC}              ║"
    echo "║                                          ║"
    echo -e "║ ${CYAN}Open Kafka UI to monitor:${NC}               ║"
    echo "║ → http://localhost:8080                 ║"
    echo "║                                          ║"
    echo -e "║ ${CYAN}API Endpoints:${NC}                          ║"
    echo "║ → POST /api/events/bulk/generate        ║"
    echo "║ → GET  /actuator/health                 ║"
    echo "║ → GET  /actuator/metrics                ║"
    echo "║                                          ║"
    echo -e "║ ${CYAN}View logs:${NC}                              ║"
    echo "║ → ./manage-streamsocial.sh logs         ║"
    echo "║                                          ║"
    echo -e "║ ${CYAN}Stop stack:${NC}                             ║"
    echo "║ → ./manage-streamsocial.sh stop         ║"
    echo "╚════════════════════════════════════════════╝"
    echo ""
}

show_help() {
    cat << EOF
Usage: $0 <action> [parameters]

Actions:
  start              Build and start all services (default)
  build              Build Docker images only
  stop               Stop and remove containers
  logs [service]     Display logs (optional: specify service)
  status             Show container status
  ps                 List all containers
  restart            Restart running containers
  scale <replicas>   Scale kafka-consumer service
  demo               Run interactive demo
  help               Show this help message

Examples:
  $0 start                      # Start stack with build
  $0 build                      # Build images only
  $0 logs                       # View all logs
  $0 logs kafka-consumer        # View consumer logs
  $0 logs backend-api           # View API logs
  $0 status                     # Show status
  $0 scale 3                    # Scale to 3 consumers
  $0 stop                       # Stop everything
  $0 demo                       # Run demo with scaling

EOF
}

# ========================================
# Main Execution
# ========================================

# Show header
show_header

# Validate prerequisites
print_info "Validating prerequisites..."

if ! test_docker; then
    print_error "Docker is not installed or not in PATH"
    print_info "Please install Docker from https://www.docker.com"
    exit 1
fi
print_success "Docker is installed"

if ! test_docker_compose; then
    print_error "Docker Compose is not available"
    print_info "Please ensure Docker is updated with Compose support"
    exit 1
fi
print_success "Docker Compose is available"

if ! test_compose_file; then
    print_error "Compose file not found: $COMPOSE_FILE"
    print_info "Please run this script from the project root"
    exit 1
fi
print_success "Compose file found"

echo ""

# Get action (default to start)
ACTION="${1:-start}"

# Execute action
case "$ACTION" in
    start)
        start_stack
        ;;
    build)
        build_stack
        ;;
    stop|down)
        stop_stack
        ;;
    restart)
        restart_stack
        ;;
    logs)
        show_logs "$2"
        ;;
    status)
        show_status
        ;;
    ps)
        show_processes
        ;;
    scale)
        scale_service "$2"
        ;;
    demo)
        run_demo
        ;;
    help|-h|--help)
        show_help
        ;;
    *)
        print_error "Unknown action: $ACTION"
        echo ""
        show_help
        exit 1
        ;;
esac

print_success "Operation completed"
echo ""
