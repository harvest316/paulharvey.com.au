#!/usr/bin/env bash
# Syncs resume .docx files from SyncThing folder to site, updates CV page, deploys.
# Usage: ./scripts/sync-resumes.sh [source_dir]
# Default source: ~/SyncThing/Resume/

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
SOURCE_DIR="${1:-$HOME/SyncThing/Resume}"
DOCS_DIR="$REPO_DIR/cv/docs"
CV_PAGE="$REPO_DIR/cv/index.html"

if [ ! -d "$SOURCE_DIR" ]; then
  echo "Error: Source dir not found: $SOURCE_DIR"
  exit 1
fi

# Find .docx files (top-level only, ignore Old/ subfolder)
shopt -s nullglob
docx_files=("$SOURCE_DIR"/*.docx)

if [ ${#docx_files[@]} -eq 0 ]; then
  echo "No .docx files found in $SOURCE_DIR"
  exit 0
fi

# Copy files
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

# Regenerate CV page doc entries
echo "Regenerating CV page..."
entries=""
for f in "$DOCS_DIR"/*.docx; do
  fname="$(basename "$f")"
  size_kb=$(( $(stat -c%s "$f") / 1024 ))
  mod_date=$(date -r "$f" '+%-d %b %Y')

  # Derive display title from filename (strip date suffix and extension)
  title=$(echo "$fname" | sed -E 's/ - [0-9]{8}\.docx$//' | sed -E 's/ - Paul Harvey//')

  # Choose icon: FAQ gets question mark, others get document
  if echo "$fname" | grep -qi "FAQ"; then
    icon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3"/><line x1="12" y1="17" x2="12.01" y2="17"/></svg>'
  else
    icon='<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/></svg>'
  fi

  encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$fname'))")

  entries="$entries
      <li class=\"doc\">
        <a href=\"docs/$encoded\" download>
          <div class=\"doc-icon\">$icon</div>
          <div class=\"doc-info\">
            <div class=\"doc-title\">$title</div>
            <div class=\"doc-meta\">Updated $mod_date · DOCX · $size_kb KB</div>
          </div>
          <div class=\"doc-arrow\">
            <svg width=\"16\" height=\"16\" viewBox=\"0 0 24 24\" fill=\"none\" stroke=\"currentColor\" stroke-width=\"2\" stroke-linecap=\"round\" stroke-linejoin=\"round\"><path d=\"M5 12h14\"/><path d=\"m12 5 7 7-7 7\"/></svg>
          </div>
        </a>
      </li>"
done

# Replace doc entries in CV page using python for reliability
python3 - "$CV_PAGE" "$entries" <<'PYEOF'
import sys, re
page_path, entries = sys.argv[1], sys.argv[2]
with open(page_path, 'r') as f:
    html = f.read()
new_list = f'<ul class="docs">{entries}\n    </ul>'
html = re.sub(r'<ul class="docs">.*?</ul>', new_list, html, flags=re.DOTALL)
with open(page_path, 'w') as f:
    f.write(html)
PYEOF

echo "CV page updated."

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
# Load env from repo .env
ENV_FILE="$REPO_DIR/.env"
if [ -f "$ENV_FILE" ]; then
  set -a; source "$ENV_FILE"; set +a
fi

if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "Error: CLOUDFLARE_API_TOKEN not set. Configure .env (copy from .env.example)"
  exit 1
fi

export HOME="${WRANGLER_HOME:-/home/jason/.cache/wrangler-home}"
npx wrangler pages deploy "$REPO_DIR" --project-name=paulharvey-com-au --branch=main --commit-dirty=true

echo "Done. Resumes synced and deployed."
