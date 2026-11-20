#!/usr/bin/env bash
# deploy.sh — break-glass deploy from a laptop.
#
# The normal way to deploy is the "Deploy" workflow in GitHub Actions (a
# button; it deploys main). This script ships exactly the same kind of bundle
# to exactly the same receiver, for when GitHub is unavailable.
#
# It needs an SSH alias for the cuqterm account with a deploy key of your own
# (locked to the same forced command — see deploy/README.md):
#
#   Host cuq-terminal
#       HostName <server ip>
#       User cuqterm
#       IdentityFile ~/.ssh/cuq_terminal_deploy
#       IdentitiesOnly yes
#       ClearAllForwardings yes
#
#   deploy/deploy.sh                  # build, ship, switch, health-check
#   DRY_RUN=1 deploy/deploy.sh        # build the bundle and list it; ship nothing
#   deploy/deploy.sh status           # what's running
#   deploy/deploy.sh rollback         # back to the previous release
#   DEPLOY_SSH=other-alias deploy/deploy.sh
#
# Deploying anything but a clean, pushed main needs FORCE=1, so the box only
# ever runs what is in GitHub unless you say otherwise.
#
# NOTE: every deploy and rollback restarts the backend, which signs every
# trader out (their secrets are held in memory only).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEPLOY_SSH="${DEPLOY_SSH:-cuq-terminal}"
TERMINAL_URL="${TERMINAL_URL:-https://terminal.178-105-55-5.sslip.io}"
ACTION="${1:-deploy}"

log() { printf '\033[1;34m[deploy]\033[0m %s\n' "$*"; }
die() { printf '\033[1;31m[deploy] error:\033[0m %s\n' "$*" >&2; exit 1; }

SSH=(ssh -o ClearAllForwardings=yes "$DEPLOY_SSH")

case "$ACTION" in
  status|rollback) exec "${SSH[@]}" "$ACTION" ;;
  deploy) ;;
  *) die "unknown action '$ACTION' (deploy, status or rollback)" ;;
esac

if [ "${FORCE:-0}" != "1" ]; then
  branch="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)"
  [ "$branch" = "main" ] || die "on '$branch', not main (FORCE=1 to deploy it anyway)"
  git -C "$ROOT" diff --quiet HEAD -- || die "uncommitted changes (FORCE=1 to deploy them anyway)"
  git -C "$ROOT" fetch -q origin main
  [ "$(git -C "$ROOT" rev-parse HEAD)" = "$(git -C "$ROOT" rev-parse origin/main)" ] \
    || die "local main is not origin/main — pull or push first (FORCE=1 to skip)"
fi

TMPD="$(mktemp -d)"
trap 'rm -rf "$TMPD"' EXIT
BUNDLE="$TMPD/bundle.tar.gz"
"$ROOT/deploy/build-bundle.sh" "$BUNDLE"

if [ "${DRY_RUN:-0}" = "1" ]; then
  tar -tzf "$BUNDLE" | sed 's|^\./||' | grep -v '/$' | sort
  log "dry run: nothing shipped"
  exit 0
fi

log "shipping to $DEPLOY_SSH"
"${SSH[@]}" deploy < "$BUNDLE"

log "checking $TERMINAL_URL"
curl -fsS -m 10 "$TERMINAL_URL/api/" >/dev/null || die "public health check failed: $TERMINAL_URL/api/"
log "done"
