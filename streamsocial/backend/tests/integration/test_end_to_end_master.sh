#!/usr/bin/env bash
# StreamSocial — master integration test runner.
# Prerequisites: app stack is up (./setup_python.sh or ./setup_python.sh --start-only).
#
# Usage (from repo root):
#   ./test_end_to_end_master.sh           # run all suites listed below
#   ./test_end_to_end_master.sh --help
#
# Env:
#   BASE_URL   API base (default http://localhost:8000)
#   CONTINUE_ON_FAIL=1  run remaining suites even if one fails (default: stop)

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

E2E="${SCRIPT_DIR}/streamsocial/backend/tests/integration/test_end_to_end.sh"
BASE_URL="${BASE_URL:-http://localhost:8000}"
CONTINUE_ON_FAIL="${CONTINUE_ON_FAIL:-0}"

GREEN='\033[0;32m'
RED='\033[0;31m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
  cat <<'HELP'
StreamSocial master integration runner.

Prerequisites:
  ./setup_python.sh              # or --start-only if stack already built

Usage:
  ./test_end_to_end_master.sh
  CONTINUE_ON_FAIL=1 ./test_end_to_end_master.sh
  BASE_URL=http://localhost:8000 ./test_end_to_end_master.sh

Runs (in order):
  test_end_to_end.sh           # all
  test_end_to_end.sh health
  test_end_to_end.sh event
  test_end_to_end.sh consumer
  test_end_to_end.sh metrics
  test_end_to_end.sh cluster
  test_end_to_end.sh scale
HELP
  exit 0
fi

if [[ ! -x "$E2E" ]]; then
  if [[ -f "$E2E" ]]; then
    chmod +x "$E2E"
  else
    echo -e "${RED}Missing e2e script: $E2E${NC}" >&2
    exit 1
  fi
fi

if ! curl -sf "${BASE_URL}/health" >/dev/null 2>&1; then
  echo -e "${RED}Backend not reachable at ${BASE_URL}/health${NC}" >&2
  echo -e "${YELLOW}Start the app first: ./setup_python.sh${NC}" >&2
  exit 1
fi

# Suites in the order requested by the user
SUITES=(
  ""
  "health"
  "event"
  "consumer"
  "metrics"
  "cluster"
  "scale"
)

PASSED=0
FAILED=0
FAILED_NAMES=()

echo -e "${CYAN}"
echo "╔════════════════════════════════════════════════════════════════╗"
echo "║  StreamSocial Master Integration Runner                        ║"
echo "║  BASE_URL=${BASE_URL}"
echo "╚════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

run_suite() {
  local label="$1"
  shift
  echo -e "\n${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
  echo -e "${CYAN}▶ MASTER: ${label}${NC}"
  echo -e "${CYAN}  command: $*${NC}"
  echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"

  if "$@"; then
    echo -e "${GREEN}✔ MASTER suite OK: ${label}${NC}"
    PASSED=$((PASSED + 1))
    return 0
  fi

  echo -e "${RED}✘ MASTER suite FAIL: ${label}${NC}"
  FAILED=$((FAILED + 1))
  FAILED_NAMES+=("$label")
  return 1
}

for suite in "${SUITES[@]}"; do
  if [[ -z "$suite" ]]; then
    label="all"
    cmd=( "$E2E" )
  else
    label="$suite"
    cmd=( "$E2E" "$suite" )
  fi

  if ! run_suite "$label" "${cmd[@]}"; then
    if [[ "$CONTINUE_ON_FAIL" != "1" ]]; then
      echo -e "${YELLOW}Stopping early (set CONTINUE_ON_FAIL=1 to run all suites).${NC}"
      break
    fi
  fi
done

echo ""
echo -e "${CYAN}╔════════════════════════════════════════════════════════════════╗${NC}"
echo -e "${CYAN}║  MASTER SUMMARY                                                ║${NC}"
echo -e "${CYAN}╚════════════════════════════════════════════════════════════════╝${NC}"
echo -e "${GREEN}Suites passed: ${PASSED}${NC}"
echo -e "${RED}Suites failed: ${FAILED}${NC}"
if [[ "${#FAILED_NAMES[@]}" -gt 0 ]]; then
  echo -e "${RED}Failed: ${FAILED_NAMES[*]}${NC}"
fi
echo ""

if [[ "$FAILED" -gt 0 ]]; then
  exit 1
fi
exit 0
