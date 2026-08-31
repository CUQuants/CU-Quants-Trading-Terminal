#!/usr/bin/env bash
# dev-local.sh — run the trading terminal (backend + frontend) natively, no
# Docker, so it can reach a CU Quants gateway on a localhost URL.
#
# Backend  : http://127.0.0.1:8000   (FastAPI, reads backend/.env)
# Dashboard: http://127.0.0.1:5173   (Vite)
#
# Both run in the foreground; Ctrl-C stops both. See DEV_TESTING.md for the
# full end-to-end setup (gateway + credentials + placing a test order).
#
#   scripts/dev-local.sh
#   SKIP_INSTALL=1 scripts/dev-local.sh          # skip uv sync / npm install
#   BACKEND_PORT=9000 FRONTEND_PORT=5000 scripts/dev-local.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"

log()  { printf '\033[1;34m[dev-local]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[dev-local] warning:\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[dev-local] error:\033[0m %s\n' "$*" >&2; exit 1; }

command -v uv  >/dev/null || die "uv not found — https://docs.astral.sh/uv/"
command -v npm >/dev/null || die "npm not found — install Node.js"
[ -f "$BACKEND/.env" ] || die "$BACKEND/.env missing — cp backend/.env.example backend/.env and fill in CUQ_PROXY_* (see DEV_TESTING.md)"

# --- preflight: required env + is the gateway up? -----------------------
missing=""
for v in CUQ_PROXY_URL CUQ_PROXY_API_KEY CUQ_PROXY_SECRET CUQ_PROXY_OPERATOR_ID CUQ_PROXY_OPERATOR_NAME; do
  grep -qE "^${v}=.+" "$BACKEND/.env" || missing="$missing $v"
done
[ -z "$missing" ] || die "backend/.env is missing or blank:$missing
  (these are the terminal's names — map them from the gateway's creds file:
   CUQ_OPERATOR_API_KEY->CUQ_PROXY_API_KEY, _API_SECRET->CUQ_PROXY_SECRET,
   _ID->CUQ_PROXY_OPERATOR_ID, _NAME->CUQ_PROXY_OPERATOR_NAME, base URL->CUQ_PROXY_URL)"

GW="$(grep -E '^CUQ_PROXY_URL=' "$BACKEND/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
if curl -fsS -m 3 "$GW/healthz" >/dev/null 2>&1; then
  log "gateway reachable at $GW"
else
  warn "gateway at $GW did not answer /healthz — start it first:"
  warn "    (cd ../trading-gateway && scripts/dev-gateway.sh up)"
fi

# --- dependencies ------------------------------------------------------------
if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  log "backend deps (uv sync)"
  (cd "$BACKEND" && uv sync --quiet)
  if [ ! -d "$FRONTEND/node_modules" ]; then
    log "frontend deps (npm install)"
    (cd "$FRONTEND" && npm install --silent)
  fi
fi

# --- run both; kill the whole process group on exit --------------------------
trap 'kill 0' EXIT INT TERM

log "backend  -> http://127.0.0.1:$BACKEND_PORT   (routes OKX through $GW)"
( cd "$BACKEND" && exec uv run uvicorn app:app --reload --port "$BACKEND_PORT" ) &
backend_pid=$!

log "frontend -> http://127.0.0.1:$FRONTEND_PORT"
( cd "$FRONTEND" && VITE_API_URL="http://localhost:$BACKEND_PORT" \
    exec npm run dev -- --port "$FRONTEND_PORT" --strictPort ) &
frontend_pid=$!

log "both running (backend $backend_pid, frontend $frontend_pid) — Ctrl-C to stop both"
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done
warn "one process exited — stopping the other"
