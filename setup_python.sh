#!/usr/bin/env bash
# StreamSocial — application setup & start only.
# Does NOT run tests (use ./test_end_to_end_master.sh).
#
# Usage (from repo root):
#   ./setup_python.sh              # deps (if needed) + start full stack
#   ./setup_python.sh --start-only # skip venv/pip; just compose up + wait healthy
#   ./setup_python.sh --deps-only  # install Python deps only
#   ./setup_python.sh --help

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

REQ_FILE="${SCRIPT_DIR}/streamsocial/backend/requirements.txt"
COMPOSE_FILE="${SCRIPT_DIR}/docker-compose.yml"
VENV_DIR="${SCRIPT_DIR}/venv"
BASE_URL="${BASE_URL:-http://localhost:8000}"
HEALTH_URL="${BASE_URL}/health"
MAX_WAIT_SEC="${MAX_WAIT_SEC:-180}"

MODE="full"
case "${1:-}" in
  --start-only|-s) MODE="start-only" ;;
  --deps-only|-d)  MODE="deps-only" ;;
  --help|-h)
    cat <<'HELP'
StreamSocial — application setup & start only.
Does NOT run tests (use ./test_end_to_end_master.sh).

Usage (from repo root):
  ./setup_python.sh              # deps (if needed) + start full stack
  ./setup_python.sh --start-only # skip venv/pip; just compose up + wait healthy
  ./setup_python.sh --deps-only  # install Python deps only
  ./setup_python.sh --help
HELP
    exit 0
    ;;
  "") ;;
  *)
    echo "Unknown option: $1 (try --help)"
    exit 1
    ;;
esac

log()  { echo "[setup] $*"; }
fail() { echo "[setup] ERROR: $*" >&2; exit 1; }

require_file() {
  [[ -f "$1" ]] || fail "missing required file: $1"
}

install_deps() {
  require_file "$REQ_FILE"

  if ! command -v python3 >/dev/null 2>&1; then
    log "python3 not found; attempting apt install (may need privileges)..."
    if command -v apt-get >/dev/null 2>&1; then
      sudo apt-get update -y
      sudo apt-get install -y python3 python3-venv python3-pip
    else
      fail "python3 is required"
    fi
  fi

  if [[ ! -d "$VENV_DIR" ]]; then
    log "Creating virtualenv at $VENV_DIR"
    python3 -m venv "$VENV_DIR"
  else
    log "Reusing virtualenv at $VENV_DIR"
  fi

  # shellcheck disable=SC1091
  source "${VENV_DIR}/bin/activate"
  log "Upgrading pip..."
  pip install --upgrade pip >/dev/null
  log "Installing application dependencies from $REQ_FILE"
  pip install -r "$REQ_FILE"
  log "Python ready: $(python --version 2>&1)"
}

start_app() {
  require_file "$COMPOSE_FILE"
  command -v docker >/dev/null 2>&1 || fail "docker is required"
  docker compose version >/dev/null 2>&1 || fail "docker compose plugin is required"

  log "Starting StreamSocial stack (Kafka + API + consumers)..."
  docker compose -f "$COMPOSE_FILE" up -d --build

  log "Waiting for API health at ${HEALTH_URL} (timeout ${MAX_WAIT_SEC}s)..."
  local elapsed=0
  until curl -sf "$HEALTH_URL" >/dev/null 2>&1; do
    sleep 5
    elapsed=$((elapsed + 5))
    if (( elapsed >= MAX_WAIT_SEC )); then
      log "Last compose ps:"
      docker compose -f "$COMPOSE_FILE" ps || true
      fail "API did not become healthy within ${MAX_WAIT_SEC}s"
    fi
    if (( elapsed % 15 == 0 )); then
      log "still waiting... ${elapsed}s"
    fi
  done

  log "API is healthy."
  curl -sS "$HEALTH_URL" || true
  echo ""
  log "Services:"
  docker compose -f "$COMPOSE_FILE" ps
  echo ""
  log "App URLs:"
  log "  API:      ${BASE_URL}"
  log "  Health:   ${HEALTH_URL}"
  log "  Docs:     ${BASE_URL}/docs"
  log "  Kafka UI: http://localhost:8080"
  log "Scale consumers: docker compose up -d --scale kafka-consumer=N"
  log "Integration tests: ./test_end_to_end_master.sh"
  log "Setup complete (app started; tests not run)."
}

case "$MODE" in
  deps-only)
    install_deps
    ;;
  start-only)
    start_app
    ;;
  full)
    install_deps
    start_app
    ;;
esac
