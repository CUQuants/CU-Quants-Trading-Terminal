#!/usr/bin/env bash
# deploy.sh — build the terminal locally and ship it to 178.105.55.5.
#
# Run from a Mac with `ssh cuq-proxy` working (the ~/.ssh/config alias for
# admin@178.105.55.5). Does NOT touch Caddy or the gateway: first-time setup
# (uv, the systemd unit, the Caddy block, /srv/cuq-terminal/.env) is a manual,
# one-off step — see deploy/README.md.
#
#   deploy/deploy.sh              # build, rsync, uv sync, restart, health check
#   DRY_RUN=1 deploy/deploy.sh    # build, then show what rsync would change
#   SSH_HOST=admin@178.105.55.5 deploy/deploy.sh
#
# NOTE: restarting the backend signs every trader out (their secrets are held
# in memory only). Deploy outside trading hours, or warn people first.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SSH_HOST="${SSH_HOST:-cuq-proxy}"
REMOTE="/srv/cuq-terminal"
PUBLIC_URL="${PUBLIC_URL:-https://terminal.178-105-55-5.sslip.io}"
DRY_RUN="${DRY_RUN:-0}"

log()  { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
die()  { printf '\033[1;31m[deploy] error:\033[0m %s\n' "$*" >&2; exit 1; }

command -v rsync >/dev/null || die "rsync not found"
command -v npm >/dev/null || die "npm not found (Node 22: see frontend/.nvmrc)"

# --- 1. build the SPA locally (the box needs no Node) -----------------------
log "building frontend"
( cd "$ROOT/frontend" && npm ci --no-audit --no-fund --silent && npm run build )
[ -f "$ROOT/frontend/dist/index.html" ] || die "frontend build produced no dist/index.html"

# Record what is being deployed, like the gateway's DEPLOYED file.
COMMIT="$(git -C "$ROOT" rev-parse --short HEAD 2>/dev/null || echo unknown)"
BRANCH="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
DIRTY=""; git -C "$ROOT" diff --quiet 2>/dev/null || DIRTY=" (+uncommitted changes)"
STAMP="$COMMIT on $BRANCH$DIRTY, deployed $(date -u +%Y-%m-%dT%H:%M:%SZ) by $(whoami)"

RSYNC=(rsync -az --delete)
[ "$DRY_RUN" = "1" ] && RSYNC+=(--dry-run --itemize-changes)

# --- 2. ship the backend ------------------------------------------------------
# .env never leaves your machine; the box has its own at $REMOTE/.env.
log "syncing backend -> $SSH_HOST:$REMOTE/app"
"${RSYNC[@]}" \
  --exclude .git --exclude .venv --exclude __pycache__ --exclude .pytest_cache \
  --exclude .mypy_cache --exclude '.env' --exclude 'logs/' --exclude tests \
  --exclude DEPLOYED \
  "$ROOT/backend" "$ROOT/deploy" "$SSH_HOST:$REMOTE/app/"

# --- 3. ship the built SPA ----------------------------------------------------
log "syncing frontend/dist -> $SSH_HOST:$REMOTE/frontend"
"${RSYNC[@]}" "$ROOT/frontend/dist/" "$SSH_HOST:$REMOTE/frontend/"

if [ "$DRY_RUN" = "1" ]; then
  log "dry run: nothing changed on the box"
  exit 0
fi

# --- 4. install deps and restart --------------------------------------------
log "uv sync + restart cuq-terminal on $SSH_HOST"
ssh "$SSH_HOST" bash -s -- "$REMOTE" "$STAMP" <<'EOF'
set -euo pipefail
REMOTE="$1"; STAMP="$2"
export PATH="$HOME/.local/bin:$PATH"
command -v uv >/dev/null || { echo "uv missing on the box: see deploy/README.md (first-time setup)"; exit 1; }
[ -f "$REMOTE/.env" ] || { echo "$REMOTE/.env missing: see deploy/README.md"; exit 1; }
cd "$REMOTE/app/backend"
uv sync --frozen --no-dev --quiet
echo "$STAMP" > "$REMOTE/app/DEPLOYED"
systemctl --user restart cuq-terminal
sleep 2
systemctl --user is-active --quiet cuq-terminal || { journalctl --user -u cuq-terminal -n 40 --no-pager; exit 1; }
curl -fsS -m 5 http://127.0.0.1:8100/ >/dev/null && echo "backend healthy on loopback"
EOF

# --- 5. check it from outside ------------------------------------------------
log "checking $PUBLIC_URL"
if curl -fsS -m 10 "$PUBLIC_URL/api/" >/dev/null 2>&1; then
  log "public health check OK"
else
  # Staging certificates aren't trusted, so retry without verification
  # before calling it broken.
  if curl -kfsS -m 10 "$PUBLIC_URL/api/" >/dev/null 2>&1; then
    log "public health check OK (certificate not trusted: still on the staging CA?)"
  else
    die "public health check failed: $PUBLIC_URL/api/"
  fi
fi
log "deployed $STAMP"
