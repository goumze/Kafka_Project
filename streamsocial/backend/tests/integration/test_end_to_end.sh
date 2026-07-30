#!/usr/bin/env bash
# StreamSocial integration / end-to-end API test suite.
# Prerequisites: stack running (./setup_python.sh from repo root).
#
# Usage:
#   ./test_end_to_end.sh              # all suites
#   ./test_end_to_end.sh health
#   ./test_end_to_end.sh event
#   ./test_end_to_end.sh consumer
#   ./test_end_to_end.sh metrics
#   ./test_end_to_end.sh cluster
#   ./test_end_to_end.sh scale        # produce + lag observation (needs live Kafka)
#   ./test_end_to_end.sh list

set +e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
BASE_URL="${BASE_URL:-http://localhost:8000}"

GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

TESTS_PASSED=0
TESTS_FAILED=0
TESTS_SKIPPED=0

section() { echo -e "\n${BLUE}▶ $1${NC}"; }
info()    { echo -e "${YELLOW}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[✓]${NC} $1"; TESTS_PASSED=$((TESTS_PASSED + 1)); }
error()   { echo -e "${RED}[✗]${NC} $1"; TESTS_FAILED=$((TESTS_FAILED + 1)); }
skip()    { echo -e "${YELLOW}[SKIP]${NC} $1"; TESTS_SKIPPED=$((TESTS_SKIPPED + 1)); }

need_jq() {
  if ! command -v jq >/dev/null 2>&1; then
    error "jq is required for integration tests (apt install jq / brew install jq)"
    exit 1
  fi
}

# GET/POST helpers: set RESPONSE, HTTP_CODE
http_get() {
  local url="$1"
  HTTP_CODE=$(curl -sS -o /tmp/ss_e2e_body.json -w "%{http_code}" "$url" 2>/tmp/ss_e2e_curl.err)
  RESPONSE=$(cat /tmp/ss_e2e_body.json 2>/dev/null || true)
}

http_post_json() {
  local url="$1"
  local body="$2"
  HTTP_CODE=$(curl -sS -o /tmp/ss_e2e_body.json -w "%{http_code}" \
    -X POST "$url" \
    -H "Content-Type: application/json" \
    -d "$body" 2>/tmp/ss_e2e_curl.err)
  RESPONSE=$(cat /tmp/ss_e2e_body.json 2>/dev/null || true)
}

assert_http_ok() {
  local name="$1"
  if [[ "$HTTP_CODE" == "200" || "$HTTP_CODE" == "201" || "$HTTP_CODE" == "202" ]]; then
    success "$name (HTTP $HTTP_CODE)"
    return 0
  fi
  error "$name (HTTP ${HTTP_CODE:-none})"
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
  return 1
}

assert_jq() {
  local name="$1"
  local expr="$2"
  if echo "$RESPONSE" | jq -e "$expr" >/dev/null 2>&1; then
    success "$name"
    return 0
  fi
  error "$name (jq: $expr)"
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
  return 1
}

# ── Health ──────────────────────────────────────────────────────────
test_health_check() {
  section "GET /health"
  http_get "$BASE_URL/health"
  assert_http_ok "health reachable" || return
  assert_jq "status healthy" '.status == "healthy"'
  echo "$RESPONSE" | jq '{status, service, timestamp}'
}

test_root_endpoint() {
  section "GET /"
  http_get "$BASE_URL/"
  assert_http_ok "root reachable" || return
  assert_jq "service present" '.service != null'
  echo "$RESPONSE" | jq '{service, version, consumer_mode, consumer_group_id, demo}'
}

test_health_controller() {
  echo -e "${CYAN}══ HEALTH ══${NC}"
  test_health_check
  test_root_endpoint
}

# ── Events ──────────────────────────────────────────────────────────
test_register_user() {
  section "POST /events/user/register"
  local users=("alice" "bob" "charlie")
  local emails=("alice@example.com" "bob@example.com" "charlie@example.com")
  local i
  for i in "${!users[@]}"; do
    http_post_json "$BASE_URL/events/user/register" \
      "{\"username\":\"${users[$i]}\",\"email\":\"${emails[$i]}\",\"source\":\"e2e\"}"
    if assert_http_ok "register ${users[$i]}"; then
      if echo "$RESPONSE" | jq -e '.success == true' >/dev/null 2>&1; then
        success "publish ok user=${users[$i]}"
      else
        # producer may return structured failure if brokers down
        error "register body not success for ${users[$i]}"
        echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
      fi
    fi
    sleep 0.2
  done
}

test_get_recent_events() {
  section "GET /events/recent"
  http_get "$BASE_URL/events/recent"
  assert_http_ok "recent events" || return
  assert_jq "payload has success or events" 'has("success") or has("events") or has("count")'
  echo "$RESPONSE" | jq '{success, count, message, events_in_memory} // .'
}

test_bulk_generate_short() {
  section "POST /events/bulk/generate (short background load)"
  http_post_json "$BASE_URL/events/bulk/generate" \
    '{"events_per_second":200,"duration_seconds":5,"background":true}'
  assert_http_ok "bulk generate accepted" || return
  assert_jq "bulk started or configured" \
    '.success == true or .status == "started" or .config != null'
  echo "$RESPONSE" | jq '{success, message, config, observe_lag} // .'

  section "GET /events/bulk/status"
  http_get "$BASE_URL/events/bulk/status"
  assert_http_ok "bulk status" || return
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
}

test_event_controller() {
  echo -e "${CYAN}══ EVENT ══${NC}"
  test_register_user
  test_get_recent_events
  test_bulk_generate_short
}

# ── Consumer ────────────────────────────────────────────────────────
test_consumer_stats() {
  section "GET /consumer/stats"
  http_get "$BASE_URL/consumer/stats"
  assert_http_ok "consumer stats" || return
  assert_jq "has status" 'has("status")'
  echo "$RESPONSE" | jq '{status, mode, group_id, total_lag, scale_hint} // .'
}

test_consumer_lag() {
  section "GET /consumer/lag"
  http_get "$BASE_URL/consumer/lag"
  assert_http_ok "consumer lag HTTP" || return
  assert_jq "has group_id or total_lag" 'has("group_id") or has("total_lag")'
  # Soft check: error field should ideally be null/absent for full pass
  if echo "$RESPONSE" | jq -e '.error != null and .error != ""' >/dev/null 2>&1; then
    error "consumer lag reported error: $(echo "$RESPONSE" | jq -r '.error')"
    echo "$RESPONSE" | jq '{group_id, total_lag, error, source}'
  else
    success "consumer lag payload has no error"
    echo "$RESPONSE" | jq '{group_id, total_lag, partition_count, lag_by_topic, source}'
  fi
}

test_consumer_instances() {
  section "GET /consumer/instances"
  http_get "$BASE_URL/consumer/instances"
  assert_http_ok "consumer instances" || return
  echo "$RESPONSE" | jq '{total_in_process_instances, group_id, note} // .'
}

test_consumer_health() {
  section "GET /consumer/health"
  http_get "$BASE_URL/consumer/health"
  assert_http_ok "consumer health" || return
  echo "$RESPONSE" | jq . 2>/dev/null || echo "$RESPONSE"
}

test_consumer_start_disabled() {
  section "POST /consumer/start (compose mode: expect disabled)"
  http_post_json "$BASE_URL/consumer/start" '{}'
  assert_http_ok "start endpoint responds" || return
  # In scale mode this is intentionally disabled
  if echo "$RESPONSE" | jq -e '.status == "disabled" or .status == "started" or .status == "already_running"' >/dev/null 2>&1; then
    success "start status acceptable: $(echo "$RESPONSE" | jq -r '.status')"
  else
    error "unexpected start status"
    echo "$RESPONSE" | jq .
  fi
  echo "$RESPONSE" | jq '{status, message, group_id} // .'
}

test_consumer_stop() {
  section "POST /consumer/stop"
  http_post_json "$BASE_URL/consumer/stop" '{}'
  assert_http_ok "stop endpoint responds" || return
  echo "$RESPONSE" | jq '{status, message} // .'
}

test_consumer_controller() {
  echo -e "${CYAN}══ CONSUMER ══${NC}"
  test_consumer_stats
  test_consumer_lag
  test_consumer_instances
  test_consumer_health
  test_consumer_start_disabled
  test_consumer_stop
}

# ── Metrics ─────────────────────────────────────────────────────────
test_metrics() {
  section "GET /metrics"
  http_get "$BASE_URL/metrics"
  assert_http_ok "metrics" || return
  assert_jq "has total_lag or group_id" 'has("total_lag") or has("group_id") or has("consumer_group_id")'
  if echo "$RESPONSE" | jq -e '.error != null and .error != ""' >/dev/null 2>&1; then
    error "metrics lag error: $(echo "$RESPONSE" | jq -r '.error')"
  else
    success "metrics payload has no error"
  fi
  echo "$RESPONSE" | jq '{group_id, consumer_group_id, total_lag, error, demo} // .'
}

test_metrics_lag() {
  section "GET /metrics/lag"
  http_get "$BASE_URL/metrics/lag"
  assert_http_ok "metrics/lag" || return
  echo "$RESPONSE" | jq '{group_id, total_lag, error} // .'
}

test_metrics_suite() {
  echo -e "${CYAN}══ METRICS ══${NC}"
  test_metrics
  test_metrics_lag
}

# ── Cluster ─────────────────────────────────────────────────────────
test_cluster_health() {
  section "GET /cluster/health"
  http_get "$BASE_URL/cluster/health"
  assert_http_ok "cluster health" || return
  assert_jq "has status" 'has("status")'
  echo "$RESPONSE" | jq '{status, healthy_count, total_brokers, ops_enabled} // .'
}

test_cluster_metadata() {
  section "GET /cluster/metadata"
  http_get "$BASE_URL/cluster/metadata"
  assert_http_ok "cluster metadata" || return
  echo "$RESPONSE" | jq '{topic, brokers: (.brokers|length? // .), bootstrap_servers, replication_factor, error} // .'
}

test_cluster_partitions() {
  section "GET /cluster/partitions"
  http_get "$BASE_URL/cluster/partitions"
  assert_http_ok "cluster partitions" || return
  echo "$RESPONSE" | jq '{topic, partition_details_count: (.partition_details|length? // 0), error} // .'
}

test_cluster_consumer_lag() {
  section "GET /cluster/consumer-lag"
  http_get "$BASE_URL/cluster/consumer-lag"
  assert_http_ok "cluster consumer-lag" || return
  echo "$RESPONSE" | jq '{consumer_group, group_id, total_lag, error} // .'
}

test_cluster_failure_ops() {
  section "POST /cluster/simulate-failure + recover (optional)"
  # Only meaningful when CLUSTER_OPS_ENABLED=true and docker socket mounted
  http_post_json "$BASE_URL/cluster/simulate-failure" '{"broker_name":"kafka-broker-2"}'
  if [[ "$HTTP_CODE" != "200" ]]; then
    skip "simulate-failure not available (HTTP $HTTP_CODE) — enable CLUSTER_OPS_ENABLED if needed"
    return
  fi
  if echo "$RESPONSE" | jq -e '.status == "disabled" or .enabled == false or .ops_enabled == false' >/dev/null 2>&1; then
    skip "cluster ops disabled: $(echo "$RESPONSE" | jq -r '.message // .status // "disabled"')"
    return
  fi
  if echo "$RESPONSE" | jq -e '.status' >/dev/null 2>&1; then
    success "simulate-failure responded"
    echo "$RESPONSE" | jq '{status, broker, action, message} // .'
  else
    error "simulate-failure unexpected body"
    echo "$RESPONSE" | jq .
    return
  fi
  sleep 2
  http_post_json "$BASE_URL/cluster/recover-failure" '{"broker_name":"kafka-broker-2"}'
  if assert_http_ok "recover-failure"; then
    echo "$RESPONSE" | jq '{status, broker, action} // .'
  fi
}

test_cluster_controller() {
  echo -e "${CYAN}══ CLUSTER ══${NC}"
  test_cluster_health
  test_cluster_metadata
  test_cluster_partitions
  test_cluster_consumer_lag
  test_cluster_failure_ops
}

# ── Scale / lag narrative ───────────────────────────────────────────
test_scale_narrative() {
  echo -e "${CYAN}══ SCALE / LAG NARRATIVE ══${NC}"
  section "Baseline lag"
  http_get "$BASE_URL/consumer/lag"
  assert_http_ok "baseline lag" || return
  local lag_before
  lag_before=$(echo "$RESPONSE" | jq -r '.total_lag // 0')
  info "total_lag before load: $lag_before"
  if echo "$RESPONSE" | jq -e '.error != null and .error != ""' >/dev/null 2>&1; then
    error "lag API error blocks scale narrative: $(echo "$RESPONSE" | jq -r '.error')"
    info "Worker logs may still show lag_report; fix lag probe config and rebuild API."
  fi

  section "Produce background load"
  http_post_json "$BASE_URL/events/bulk/generate" \
    '{"events_per_second":1500,"duration_seconds":15,"background":true}'
  assert_http_ok "loadgen started" || return
  success "load generation requested"
  echo "$RESPONSE" | jq '{success, message, config} // .'

  info "Waiting 12s for produce/consume..."
  sleep 12

  section "Lag after load"
  http_get "$BASE_URL/metrics"
  assert_http_ok "metrics after load" || return
  local lag_after
  lag_after=$(echo "$RESPONSE" | jq -r '.total_lag // 0')
  info "total_lag after load (API): $lag_after"
  echo "$RESPONSE" | jq '{total_lag, error, consumer_group_id, demo}'

  section "Compose consumer scale hint"
  info "Scale command: docker compose -f ${REPO_ROOT}/docker-compose.yml up -d --scale kafka-consumer=3"
  if command -v docker >/dev/null 2>&1; then
    local n
    n=$(docker ps --filter name=kafka-consumer --format '{{.Names}}' 2>/dev/null | wc -l | tr -d ' ')
    info "running kafka-consumer containers: ${n}"
    if [[ "${n}" -ge 1 ]]; then
      success "at least one kafka-consumer container is running"
    else
      error "no kafka-consumer containers found — start stack with ./setup_python.sh"
    fi
  else
    skip "docker not available to count consumers"
  fi
}

test_all() {
  echo -e "${CYAN}"
  echo "╔════════════════════════════════════════════════════════════════╗"
  echo "║  StreamSocial Integration Test Suite                           ║"
  echo "║  Base URL: ${BASE_URL}"
  echo "╚════════════════════════════════════════════════════════════════╝"
  echo -e "${NC}"
  test_health_controller
  test_event_controller
  test_consumer_controller
  test_metrics_suite
  test_cluster_controller
  test_scale_narrative
}

show_help() {
  echo -e "${CYAN}StreamSocial integration tests${NC}"
  echo ""
  echo "Prerequisites:"
  echo "  From repo root: ./setup_python.sh"
  echo "  API must answer ${BASE_URL}/health"
  echo ""
  echo "Usage: $0 [OPTION]"
  echo "  (none)|all   Full suite"
  echo "  health       Health + root"
  echo "  event        Register, recent, bulk generate"
  echo "  consumer     Stats, lag, instances, start/stop"
  echo "  metrics      /metrics and /metrics/lag"
  echo "  cluster      Cluster endpoints (+ optional failure ops)"
  echo "  scale        Produce + lag observation narrative"
  echo "  list|help    This message"
  echo ""
  echo "Env: BASE_URL (default http://localhost:8000)"
}

verify_backend() {
  section "Verifying backend at $BASE_URL"
  need_jq
  if curl -sf "$BASE_URL/health" >/dev/null 2>&1; then
    success "Backend is running"
  else
    error "Backend is NOT reachable at $BASE_URL"
    echo ""
    echo -e "${YELLOW}Start the app first:${NC}"
    echo "  cd ${REPO_ROOT}"
    echo "  ./setup_python.sh"
    echo "  # or: ./setup_python.sh --start-only"
    echo ""
    exit 1
  fi
}

print_summary() {
  echo ""
  echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}║  TEST RESULTS SUMMARY                                          ║${NC}"
  echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
  echo -e "${GREEN}✓ PASSED:  $TESTS_PASSED${NC}"
  echo -e "${RED}✗ FAILED:  $TESTS_FAILED${NC}"
  echo -e "${YELLOW}○ SKIPPED: $TESTS_SKIPPED${NC}"
  echo ""
  if [[ "$TESTS_FAILED" -gt 0 ]]; then
    exit 1
  fi
  exit 0
}

OPTION="${1:-all}"
case "$OPTION" in
  health)   verify_backend; test_health_controller; print_summary ;;
  event)    verify_backend; test_event_controller; print_summary ;;
  consumer) verify_backend; test_consumer_controller; print_summary ;;
  metrics)  verify_backend; test_metrics_suite; print_summary ;;
  cluster)  verify_backend; test_cluster_controller; print_summary ;;
  scale)    verify_backend; test_scale_narrative; print_summary ;;
  all|--all|"")
    verify_backend; test_all; print_summary
    ;;
  list|help|--help|-h) show_help; exit 0 ;;
  *)
    echo -e "${RED}Unknown option: $OPTION${NC}"
    show_help
    exit 1
    ;;
esac
