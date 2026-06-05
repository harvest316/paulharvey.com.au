#!/usr/bin/env bash
# Build the resume artifacts from resume.json (the single source of truth) and deploy
# the static site to Cloudflare Pages.
#
# No SyncThing: resume.json is canonical. The public PDF + DOCX are derived by the two
# builder scripts and deployed from a clean staging dir.
#
# Two hard safety rules (a real-contact "(full)" DOCX leaked publicly on 2026-06-01 by a
# `cp *.docx` glob that caught the gitignored file):
#   1. Stage ONLY git-TRACKED files under cv/docs — gitignored "(full)" variants can't slip in.
#   2. Abort if anything matching *(full)* / .env / *.py / CLAUDE.md reaches the staging dir.
# Never deploy the repo root: wrangler ignores .gitignore and would publish .env.
#
# Usage: ./scripts/deploy.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-$REPO_DIR/.venv/bin/python}"

if [ ! -x "$PY" ]; then
  echo "Error: Python venv not found at $PY"
  echo "Create it: python3 -m venv .venv && .venv/bin/pip install python-docx weasyprint pypdf"
  exit 1
fi

# 1. Build the public PDF + DOCX from resume.json (obfuscated contact, deterministic output).
echo "==> Building resume artifacts from resume.json"
"$PY" "$REPO_DIR/scripts/build-resume-pdf.py"
"$PY" "$REPO_DIR/scripts/build-resume-docx.py"

# 2. Commit regenerated artifacts only if they actually changed. Builds are deterministic
#    (footer uses meta.lastModified, not the wall clock), so this fires only on real edits.
cd "$REPO_DIR"
git add "cv/docs/Paul Harvey - Resume.pdf" "cv/docs/Paul Harvey - Resume.docx"
if git diff --cached --quiet; then
  echo "==> Artifacts unchanged"
else
  git commit -m "build: regenerate resume artifacts from resume.json

Co-Authored-By: deploy.sh <noreply@paulharvey.com.au>"
  # Push the artifact commit, but don't blanket-swallow the result: a benign
  # "no upstream / already up-to-date" must not look the same as a real auth /
  # non-fast-forward / network failure (which would leave the local commit
  # silently diverged from origin). Cloudflare Pages is not git-connected, so a
  # push failure does not block the deploy — but it must be surfaced, not hidden.
  if push_out="$(git push 2>&1)"; then
    echo "  Pushed artifact commit to origin"
  elif printf '%s' "$push_out" | grep -qiE 'no upstream|everything up-to-date|no configured push destination|does not appear to be a git repo'; then
    echo "  (nothing to push / no upstream configured — continuing)"
  else
    echo "  WARNING: git push failed — artifact commit is NOT on origin:" >&2
    printf '  %s\n' "$push_out" >&2
    echo "  Deploy continues (Pages is not git-connected), but resolve the push." >&2
  fi
fi

# 3. Load deploy creds from the OUT-OF-REPO secrets file. NEVER source $REPO_DIR/.env —
#    it lives in the deploy dir and wrangler can publish it (token leaked this way 2026-05-30).
SECRETS_FILE="${PAULHARVEY_DEPLOY_ENV:-$HOME/.secrets/paulharvey-deploy.env}"
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$SECRETS_FILE" ]; then
  set -a; source "$SECRETS_FILE"; set +a
fi
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "Error: CLOUDFLARE_API_TOKEN not set."
  echo "Set it in the environment, or create $SECRETS_FILE (chmod 600) with:"
  echo "  CLOUDFLARE_API_TOKEN=... / CLOUDFLARE_ACCOUNT_ID=..."
  exit 1
fi

export HOME="${WRANGLER_HOME:-/home/jason/.cache/wrangler-home}"

# 4. Build a clean staging dir from the explicit root allowlist + git-tracked cv/docs only.
echo "==> Deploying to Cloudflare Pages"
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
cp "$REPO_DIR"/index.html "$REPO_DIR"/resume.json "$REPO_DIR"/_worker.js \
   "$REPO_DIR"/_headers "$REPO_DIR"/_redirects "$STAGE"/

# Stamp the resume.json version into the staged index.html data-version attribute
# so the fetch uses a versioned URL (resume.json?v=...) instead of no-cache.
RESUME_VER="$(python3 -c "import json,sys; print(json.load(open('$REPO_DIR/resume.json'))['meta']['version'])")"
sed -i "s/data-version=\"[^\"]*\"/data-version=\"$RESUME_VER\"/" "$STAGE/index.html"
cp -r "$REPO_DIR"/images "$STAGE"/images
# Only git-TRACKED files under cv/docs (public). Gitignored "(full)" variants are excluded.
git ls-files -z cv/docs | while IFS= read -r -d '' f; do
  mkdir -p "$STAGE/$(dirname "$f")"
  cp "$REPO_DIR/$f" "$STAGE/$f"
done

# 5. Safety net: refuse to deploy if any secret / private / non-public file slipped in.
if find "$STAGE" \( -name '.env' -o -name '.env.*' -o -name '*.py' \
     -o -name 'CLAUDE.md' -o -name '*(full)*' \) -print | grep -q .; then
  echo "Error: secret/private file present in staging dir — aborting deploy."
  find "$STAGE" \( -name '.env' -o -name '.env.*' -o -name '*.py' -o -name 'CLAUDE.md' -o -name '*(full)*' \) -print
  exit 1
fi

npx wrangler pages deploy "$STAGE" --project-name=paulharvey-com-au --branch=main --commit-dirty=true

echo "Done. Built from resume.json and deployed."