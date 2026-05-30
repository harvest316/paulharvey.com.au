#!/usr/bin/env bash
# Syncs resume .docx files from SyncThing folder to site, commits, deploys.
# Usage: ./scripts/sync-resumes.sh [source_dir]
# Default source: ~/SyncThing/Resume/

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="${1:-$HOME/SyncThing/Resume}"
DOCS_DIR="$REPO_DIR/cv/docs"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source dir not found: $SOURCE_DIR"
  exit 1
fi

shopt -s nullglob
docx_files=("$SOURCE_DIR"/*.docx)

if [ ${#docx_files[@]} -eq 0 ]; then
  echo "No .docx files found in $SOURCE_DIR"
  exit 0
fi

mkdir -p "$DOCS_DIR"
changed=false

for f in "${docx_files[@]}"; do
  fname="$(basename "$f")"
  dest="$DOCS_DIR/$fname"
  if [ ! -f "$dest" ] || ! cmp -s "$f" "$dest"; then
    cp "$f" "$dest"
    echo "Updated: $fname"
    changed=true
  fi
done

# Remove docs that no longer exist in source
for f in "$DOCS_DIR"/*.docx; do
  fname="$(basename "$f")"
  if [ ! -f "$SOURCE_DIR/$fname" ]; then
    rm "$f"
    echo "Removed: $fname"
    changed=true
  fi
done

if [ "$changed" = false ]; then
  echo "No changes detected."
  exit 0
fi

# Commit and deploy
cd "$REPO_DIR"
git add cv/
if git diff --cached --quiet; then
  echo "No git changes to commit."
else
  git commit -m "docs: update resumes from SyncThing

Co-Authored-By: sync-resumes.sh <noreply@paulharvey.com.au>"
  git push
fi

# Deploy
ENV_FILE="$REPO_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "Error: CLOUDFLARE_API_TOKEN not set. Configure .env (copy from .env.example)"
  exit 1
fi

export HOME="${WRANGLER_HOME:-/home/jason/.cache/wrangler-home}"

# Deploy from a clean staging dir — NEVER deploy the repo root directly.
# wrangler pages deploy ignores .gitignore, so deploying $REPO_DIR would
# publish .env (secrets), scripts/, CLAUDE.md, .vscode, etc. as static assets.
# Explicit allowlist of publishable paths only.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$REPO_DIR"/index.html "$REPO_DIR"/resume.json "$REPO_DIR"/_worker.js \
   "$REPO_DIR"/_headers "$REPO_DIR"/_redirects "$STAGE"/
cp -r "$REPO_DIR"/images "$STAGE"/images
mkdir -p "$STAGE/cv/docs"
cp "$REPO_DIR"/cv/docs/*.docx "$STAGE/cv/docs/"

# Safety net: refuse to deploy if any secret/dotfile slipped into staging.
if command find "$STAGE" \( -name '.env' -o -name '.env.*' -o -name '*.py' \
     -o -name 'CLAUDE.md' \) -print | grep -q .; then
  echo "Error: secret/non-public file present in staging dir — aborting deploy."
  command find "$STAGE" \( -name '.env' -o -name '.env.*' -o -name '*.py' -o -name 'CLAUDE.md' \) -print
  exit 1
fi

npx wrangler pages deploy "$STAGE" --project-name=paulharvey-com-au --branch=main --commit-dirty=true

echo "Done. Resumes synced and deployed."
