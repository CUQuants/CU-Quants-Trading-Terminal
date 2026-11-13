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

# --- preflight: tools ---------------------------------------------------------
command -v uv  >/dev/null || die "uv not found — install it with:
    curl -LsSf https://astral.sh/uv/install.sh | sh     (or: brew install uv)
  then open a new terminal and re-run this script."
command -v node >/dev/null && command -v npm >/dev/null || die "Node.js not found — install Node 22 LTS:
    brew install node@22     (or https://nodejs.org, or: nvm install)
  then open a new terminal and re-run this script."
node -e '
  const [M, m] = process.versions.node.split(".").map(Number);
  process.exit((M === 20 && m >= 19) || (M === 22 && m >= 12) || M > 22 ? 0 : 1);
' || die "Node $(node -v) is too old — Vite needs 20.19+ or 22.12+. Install Node 22 LTS
    (brew install node@22, or: nvm install && nvm use — frontend/.nvmrc pins it)."

# The backend depends on the proxy-client SDK as a sibling checkout
# (backend/pyproject.toml -> ../../proxy-client).
PROXY_CLIENT="$(cd "$ROOT/.." && pwd)/proxy-client"
[ -d "$PROXY_CLIENT" ] || die "proxy-client SDK not found at $PROXY_CLIENT — clone it next to this repo:
    git clone https://github.com/CUQuants/proxy-client.git \"$PROXY_CLIENT\""

# --- preflight: backend/.env --------------------------------------------------
if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  die "created backend/.env from the template — open it and fill in the five
  CUQ_PROXY_* values from your operator credential, then re-run this script."
fi

missing=""
for v in CUQ_PROXY_URL CUQ_PROXY_API_KEY CUQ_PROXY_SECRET CUQ_PROXY_OPERATOR_ID CUQ_PROXY_OPERATOR_NAME; do
  val="$(grep -E "^${v}=" "$BACKEND/.env" | head -1 | cut -d= -f2-)"
  tmpl="$(grep -E "^${v}=" "$BACKEND/.env.example" | head -1 | cut -d= -f2-)"
  # blank, or still the placeholder from .env.example
  if [ -z "$val" ] || [ "$val" = "$tmpl" ]; then missing="$missing $v"; fi
done
[ -z "$missing" ] || die "backend/.env still has blank or placeholder values for:$missing
  Fill them in from your operator credential (see README → \"Get your credentials\")."

GW="$(grep -E '^CUQ_PROXY_URL=' "$BACKEND/.env" | head -1 | cut -d= -f2- | tr -d '"'"'"' \r')"
if curl -fsS -m 3 "$GW/healthz" >/dev/null 2>&1; then
  log "gateway reachable at $GW"
else
  warn "gateway at $GW did not answer /healthz."
  case "$GW" in
    *localhost*|*127.0.0.1*)
      warn "  it's a local gateway — start it first: (cd ../trading-gateway && scripts/dev-gateway.sh up)" ;;
    *)
      warn "  check CUQ_PROXY_URL in backend/.env, your network/VPN, or ask whoever issued your credential." ;;
  esac
fi

# --- dependencies ------------------------------------------------------------
if [ "${SKIP_INSTALL:-0}" != "1" ]; then
  log "backend deps (uv sync — downloads Python 3.12 on first run if needed)"
  (cd "$BACKEND" && uv sync --quiet)
  # Reinstall when package-lock.json changed since the last install (e.g. after git pull).
  if [ ! -f "$FRONTEND/node_modules/.package-lock.json" ] \
     || [ "$FRONTEND/package-lock.json" -nt "$FRONTEND/node_modules/.package-lock.json" ]; then
    log "frontend deps (npm install)"
    (cd "$FRONTEND" && npm install --silent --no-fund --no-audit)
  fi
fi

# --- run both; kill the whole process group on exit --------------------------
# HUP matters: closing the terminal window sends SIGHUP, not INT. Without it
# the script dies untrapped and `uv run uvicorn` (which ignores HUP) is
# orphaned, still holding the backend port. `kill 0` signals this script too,
# so ignore TERM here and `wait` for the children: otherwise the script dies
# first, the shell prints its prompt, and uvicorn's shutdown logs land after
# it, which makes it look hung.
cleanup() {
  trap - EXIT INT HUP
  trap '' TERM
  kill 0 2>/dev/null || true
  wait 2>/dev/null || true
  log "stopped"
  exit 0
}
trap cleanup EXIT INT TERM HUP

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
