#!/usr/bin/env bash
# receive-deploy.sh — the ONLY thing a terminal deploy key can run.
#
# Installed root-owned at /usr/local/bin/cuq-terminal-receive-deploy (outside
# anything a deploy writes) and named as the forced command on every deploy
# key in ~cuqterm/.ssh/authorized_keys:
#
#   restrict,command="/usr/local/bin/cuq-terminal-receive-deploy" ssh-ed25519 AAAA… github-actions
#
# Changing this file in the repo changes nothing on the box until someone
# re-installs it there by hand (deploy/README.md) — deliberately.
#
# `restrict` turns off PTYs and all forwarding; `command=` means whatever the
# client asks to run, this runs instead, with the request in
# $SSH_ORIGINAL_COMMAND. Only these words are accepted:
#
#   deploy     read a bundle (deploy/build-bundle.sh) on stdin, install it as
#              a new release, switch to it, restart, health-check; on failure
#              switch back to the previous release automatically
#   rollback   switch to the previous release and restart
#   status     print the running release and service state
#
# Runs as `cuqterm`, which owns /srv/cuq-terminal and nothing else — it cannot
# read the gateway's /srv/cuq-proxy. That account boundary, not this script,
# is what contains a leaked key: a deploy runs the code it ships.
#
# Layout:
#   /srv/cuq-terminal/.env                    server settings (600)
#   /srv/cuq-terminal/releases/<utc>-<sha7>/  one per deploy (last KEEP kept)
#   /srv/cuq-terminal/current  -> releases/…  what runs
#   /srv/cuq-terminal/previous -> releases/…  what `rollback` returns to
#   /srv/cuq-terminal/frontend -> current/frontend   (Caddy's root)
#   /srv/cuq-terminal/logs/                   shared across releases

set -euo pipefail
umask 022

# The two overrides exist for testing; an SSH client can't set them (sshd
# passes no client environment to a forced command by default).
BASE="${CUQ_TERMINAL_BASE:-/srv/cuq-terminal}"
RELEASES="$BASE/releases"
KEEP=5
MAX_BUNDLE_BYTES=$((300 * 1024 * 1024))
HEALTH_URL="${CUQ_TERMINAL_HEALTH_URL:-http://127.0.0.1:8100/}"
UNIT=cuq-terminal

export PATH="$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin"
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$(id -u)}"

say()  { printf '[receive-deploy] %s\n' "$*"; }
fail() { printf '[receive-deploy] error: %s\n' "$*" >&2; exit 1; }

# One deploy/rollback at a time. (`status` doesn't take the lock, so it works
# even before /srv/cuq-terminal belongs to cuqterm, and during a deploy.)
take_lock() {
  [ -w "$BASE" ] || fail "$BASE is not writable by $(id -un) — finish the one-time setup (deploy/README.md, step 4)"
  exec 9>"$BASE/.deploy.lock"
  flock -n 9 || fail "another deploy or rollback is in progress"
}

point() {  # point <link> <target>: atomic symlink swap
  ln -sfn "$2" "$1.new"
  mv -T "$1.new" "$1"
}

healthy() {
  for _ in $(seq 1 20); do
    curl -fsS -m 2 "$HEALTH_URL" >/dev/null 2>&1 && return 0
    sleep 1
  done
  return 1
}

restart() {
  # The unit file ships in each release; keep the installed copy in step.
  mkdir -p "$HOME/.config/systemd/user"
  install -m 644 "$BASE/current/deploy/cuq-terminal.service" "$HOME/.config/systemd/user/$UNIT.service"
  systemctl --user daemon-reload
  systemctl --user enable --quiet "$UNIT"
  systemctl --user restart "$UNIT"
}

status() {
  if [ -e "$BASE/current/DEPLOYED" ]; then
    say "current : $(cat "$BASE/current/DEPLOYED")"
  else
    say "current : (none)"
  fi
  if [ -e "$BASE/previous/DEPLOYED" ]; then
    say "previous: $(cat "$BASE/previous/DEPLOYED")"
  fi
  say "service : $(systemctl --user is-active "$UNIT" 2>/dev/null || true)"
}

switch_to() {  # switch_to <release dir>; health-checks, returns 1 if unhealthy
  point "$BASE/current" "$1"
  [ -L "$BASE/frontend" ] || point "$BASE/frontend" "$BASE/current/frontend"
  restart
  healthy
}

INCOMING=""
cleanup_incoming() { [ -n "$INCOMING" ] && rm -rf "$INCOMING"; }

deploy() {
  mkdir -p "$RELEASES" "$BASE/logs"
  INCOMING="$(mktemp -d "$RELEASES/.incoming.XXXXXX")"
  trap cleanup_incoming EXIT
  local incoming="$INCOMING"

  # The bundle arrives on stdin. Cap its size; GNU tar refuses absolute and
  # ../ member paths by default.
  head -c "$MAX_BUNDLE_BYTES" | tar -xzf - -C "$incoming" --no-same-owner --warning=no-unknown-keyword \
    || fail "could not unpack the bundle"

  for f in DEPLOYED backend/app.py backend/uv.lock deploy/cuq-terminal.service frontend/index.html; do
    [ -e "$incoming/$f" ] || fail "bundle is missing $f"
  done
  local sha
  sha="$(cut -d' ' -f1 "$incoming/DEPLOYED")"
  [[ "$sha" =~ ^[0-9a-f]{40}$ ]] || fail "DEPLOYED does not start with a commit sha"
  say "received $(cat "$incoming/DEPLOYED")"

  # Shared log directory, so order-event logs survive deploys.
  rm -rf "$incoming/backend/logs"
  ln -s "$BASE/logs" "$incoming/backend/logs"

  say "installing Python dependencies"
  ( cd "$incoming/backend" && uv sync --frozen --no-dev --quiet ) || fail "uv sync failed"

  # Catch an app that can't even import before it replaces a working one.
  # (load_dotenv finds $BASE/.env by walking up from the release.)
  ( cd "$incoming/backend" && .venv/bin/python -c "import app" ) \
    || fail "the new release fails to import; nothing was switched"

  local release
  release="$RELEASES/$(date -u +%Y%m%dT%H%M%SZ)-${sha:0:7}"
  mv "$incoming" "$release"
  INCOMING=""
  trap - EXIT

  local old=""
  [ -L "$BASE/current" ] && old="$(readlink -f "$BASE/current")"

  say "switching to $(basename "$release") and restarting (signs every trader out)"
  if switch_to "$release"; then
    [ -n "$old" ] && point "$BASE/previous" "$old"
    say "healthy"
  else
    journalctl --user -u "$UNIT" -n 30 --no-pager >&2 || true
    if [ -n "$old" ]; then
      say "UNHEALTHY — rolling back to $(basename "$old")"
      switch_to "$old" || fail "rollback is unhealthy too — investigate on the box"
      fail "new release was unhealthy; rolled back to $(basename "$old")"
    fi
    fail "new release is unhealthy and there is nothing to roll back to"
  fi

  # Keep the newest KEEP releases, and never the ones current/previous use.
  local keep_cur keep_prev
  keep_cur="$(readlink -f "$BASE/current")"
  keep_prev="$(readlink -f "$BASE/previous" 2>/dev/null || true)"
  ls -1d "$RELEASES"/2* 2>/dev/null | sort -r | tail -n +$((KEEP + 1)) | while read -r dir; do
    [ "$dir" = "$keep_cur" ] || [ "$dir" = "$keep_prev" ] || rm -rf "$dir"
  done
  status
}

rollback() {
  [ -L "$BASE/previous" ] || fail "no previous release to roll back to"
  local cur prev
  cur="$(readlink -f "$BASE/current")"
  prev="$(readlink -f "$BASE/previous")"
  say "rolling back to $(basename "$prev") (signs every trader out)"
  if switch_to "$prev"; then
    point "$BASE/previous" "$cur"
    say "healthy"
    status
  else
    say "previous release unhealthy — switching back to $(basename "$cur")"
    switch_to "$cur" || true
    fail "rollback failed"
  fi
}

case "${SSH_ORIGINAL_COMMAND:-status}" in
  deploy)   take_lock; deploy ;;
  rollback) take_lock; rollback ;;
  status)   status ;;
  *)        fail "refused: only 'deploy', 'rollback' or 'status'" ;;
esac
