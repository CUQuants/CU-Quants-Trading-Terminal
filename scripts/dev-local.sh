#!/usr/bin/env bash
# dev-local.sh — run the trading terminal (backend + frontend) natively, no
# Docker, so it can reach a CU Quants gateway on a localhost URL.
#
# Backend  : http://127.0.0.1:8000   (FastAPI, reads backend/.env)
# Dashboard: http://localhost:5173   (Vite; proxies /api -> the backend)
#
# Open the dashboard and sign in with your own gateway credential: the four
# `proxy:` values from your xlrts config.yaml. backend/.env only says where the
# gateway is (CUQ_PROXY_URL); it holds no trader credentials.
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

# uv installs the proxy-client SDK straight from GitHub (see backend/pyproject.toml),
# which needs git on PATH.
command -v git >/dev/null || die "git not found. uv needs it to install proxy-client from GitHub.
    xcode-select --install     (macOS)   or your package manager on Linux"

# --- preflight: backend/.env --------------------------------------------------
if [ ! -f "$BACKEND/.env" ]; then
  cp "$BACKEND/.env.example" "$BACKEND/.env"
  die "created backend/.env from the template — open it and set CUQ_PROXY_URL to
  your gateway's URL, then re-run this script."
fi

val="$(grep -E "^CUQ_PROXY_URL=" "$BACKEND/.env" | head -1 | cut -d= -f2-)"
tmpl="$(grep -E "^CUQ_PROXY_URL=" "$BACKEND/.env.example" | head -1 | cut -d= -f2-)"
if [ -z "$val" ] || [ "$val" = "$tmpl" ]; then
  die "backend/.env has a blank or placeholder CUQ_PROXY_URL. Set it to your gateway's URL."
fi

# Credentials used to live in backend/.env. They're no longer read; say so,
# since a secret sitting in a file it doesn't need to be in is worth removing.
stale=""
for v in CUQ_PROXY_API_KEY CUQ_PROXY_SECRET CUQ_PROXY_OPERATOR_ID CUQ_PROXY_OPERATOR_NAME; do
  grep -qE "^${v}=." "$BACKEND/.env" && stale="$stale $v"
done
[ -z "$stale" ] || warn "backend/.env still sets$stale — no longer read (you sign in
  in the browser now). Delete those lines."

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

# --- run both; stop each child's process group on exit ----------------------
# Each child runs in its OWN process group (set -m), so Ctrl-C only reaches this
# script and every child gets exactly one signal, from cleanup(). Previously
# Ctrl-C sent SIGINT to uvicorn's reloader and `kill 0` sent SIGTERM right
# behind it; the second signal re-entered uvicorn's signal handler while it held
# a threading.Event lock and the reloader deadlocked forever, still holding the
# backend port (worker left <defunct>). HUP (terminal closed) is trapped too.
# Children get stdin from /dev/null: a background process group that reads the
# terminal is stopped by SIGTTIN (Vite's keyboard shortcuts would do that).
set -m
backend_pid=""
frontend_pid=""
cleanup() {
  trap - EXIT INT TERM HUP
  local pids="$backend_pid $frontend_pid" pid alive i
  for pid in $pids; do kill -TERM -- "-$pid" 2>/dev/null || true; done
  # Give them up to 10s to shut down cleanly, then force it.
  for i in $(seq 1 20); do
    alive=0
    for pid in $pids; do kill -0 -- "-$pid" 2>/dev/null && alive=1; done
    [ "$alive" = 0 ] && break
    sleep 0.5
  done
  if [ "$alive" = 1 ]; then
    warn "children did not exit within 10s — sending SIGKILL"
    for pid in $pids; do kill -KILL -- "-$pid" 2>/dev/null || true; done
  fi
  log "stopped"
  exit 0
}
trap cleanup EXIT INT TERM HUP

log "backend  -> http://127.0.0.1:$BACKEND_PORT   (routes OKX through $GW)"
# Plain-http dev: the session cookie can't be Secure here.
( cd "$BACKEND" && TERMINAL_COOKIE_SECURE=false \
    exec uv run uvicorn app:app --reload --host 127.0.0.1 --port "$BACKEND_PORT" ) &
backend_pid=$!

log "frontend -> http://localhost:$FRONTEND_PORT   (open this, then sign in)"
# The browser talks to the backend same-origin through Vite's /api proxy, as
# it does through Caddy in production, so the session cookie behaves the same.
( cd "$FRONTEND" && BACKEND_URL="http://127.0.0.1:$BACKEND_PORT" \
    exec npm run dev -- --port "$FRONTEND_PORT" --strictPort ) &
frontend_pid=$!

log "both running (backend $backend_pid, frontend $frontend_pid) — Ctrl-C to stop both"
while kill -0 "$backend_pid" 2>/dev/null && kill -0 "$frontend_pid" 2>/dev/null; do
  sleep 1
done
warn "one process exited — stopping the other"
