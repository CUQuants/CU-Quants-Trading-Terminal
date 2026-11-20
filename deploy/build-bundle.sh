#!/usr/bin/env bash
# build-bundle.sh — build the frontend and package one release as a .tar.gz.
#
# The same bundle is produced by the GitHub "Deploy" workflow and by
# deploy/deploy.sh on a laptop, and is unpacked on the server by
# deploy/receive-deploy.sh. Layout:
#
#   backend/    the FastAPI app (no tests, venv, caches, .env or logs)
#   deploy/     these deploy files (the server installs its unit from here)
#   frontend/   the built SPA (frontend/dist)
#   DEPLOYED    one line: <full commit sha> <ref><dirty?> built <utc> by <who>
#
#   deploy/build-bundle.sh /tmp/terminal.tar.gz
#   SKIP_BUILD=1 deploy/build-bundle.sh out.tar.gz   # reuse an existing frontend/dist

set -euo pipefail

OUT="${1:?usage: build-bundle.sh OUT.tar.gz}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

if [ "${SKIP_BUILD:-0}" != "1" ]; then
  ( cd "$ROOT/frontend" && npm ci --no-audit --no-fund && npm run build )
fi
[ -f "$ROOT/frontend/dist/index.html" ] || { echo "no frontend/dist/index.html — build failed?" >&2; exit 1; }

STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT

# macOS tar would otherwise add AppleDouble ._* files to the archive.
export COPYFILE_DISABLE=1

mkdir -p "$STAGE/backend" "$STAGE/deploy" "$STAGE/frontend"
tar -C "$ROOT/backend" \
    --exclude ./.venv --exclude ./tests --exclude ./logs --exclude ./.env \
    --exclude '__pycache__' --exclude .pytest_cache --exclude .mypy_cache \
    -cf - . | tar -C "$STAGE/backend" -xf -
tar -C "$ROOT/deploy" -cf - . | tar -C "$STAGE/deploy" -xf -
tar -C "$ROOT/frontend/dist" -cf - . | tar -C "$STAGE/frontend" -xf -

SHA="$(git -C "$ROOT" rev-parse HEAD)"
REF="${GITHUB_REF_NAME:-$(git -C "$ROOT" rev-parse --abbrev-ref HEAD)}"
DIRTY=""
git -C "$ROOT" diff --quiet HEAD -- 2>/dev/null || DIRTY="+uncommitted"
WHO="${GITHUB_ACTOR:+github:$GITHUB_ACTOR}"
WHO="${WHO:-$(whoami)@$(hostname -s)}"
printf '%s %s%s built %s by %s\n' "$SHA" "$REF" "$DIRTY" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$WHO" \
  > "$STAGE/DEPLOYED"

tar -C "$STAGE" -czf "$OUT" .
echo "bundle: $OUT ($(du -h "$OUT" | cut -f1)) — $(cat "$STAGE/DEPLOYED")"
