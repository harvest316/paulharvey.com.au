#!/usr/bin/env bash
# Build the resume artifacts from resume.json and deploy the static site.
#
# Layout: every served file lives under public/ (the wrangler deploy root). Source,
# tooling and secrets live OUTSIDE public/ — so `wrangler pages deploy public/` can
# never publish .env, scripts, CLAUDE.md, or the real-contact "(full)" variants. That
# subfolder scope replaces the old staging-dir copy + allowlist + safety-grep.
#
# Two ways to ship:
#   - Push to main  -> GitHub Actions (.github/workflows/deploy.yml) deploys with the
#     repo's CLOUDFLARE_* secrets. This is the normal path.
#   - Run this script -> builds artifacts, commits them, and deploys directly from your
#     machine using CLOUDFLARE_* from the gitignored repo-root .env (handy for an
#     immediate deploy without waiting on CI).
#
# Usage: ./scripts/deploy.sh

set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PUBLIC_DIR="$REPO_DIR/public"
PY="${PYTHON:-$REPO_DIR/.venv/bin/python}"

if [ ! -x "$PY" ]; then
  echo "Error: Python venv not found at $PY"
  echo "Create it: python3 -m venv .venv && .venv/bin/pip install python-docx weasyprint pypdf"
  exit 1
fi

# 1. Build the public PDF + DOCX from resume.json (obfuscated contact, deterministic).
#    The builders write into public/cv/docs (see PUBLIC in the scripts).
echo "==> Building resume artifacts from resume.json"
"$PY" "$REPO_DIR/scripts/build-resume-pdf.py"
"$PY" "$REPO_DIR/scripts/build-resume-docx.py"

# 2. Stamp the resume.json version into public/index.html so the site fetches
#    resume.json?v=<version> (cacheable) rather than forcing a revalidation each visit.
RESUME_VER="$("$PY" -c "import json; print(json.load(open('$PUBLIC_DIR/resume.json'))['meta']['version'])")"
sed -i "s/data-version=\"[^\"]*\"/data-version=\"$RESUME_VER\"/" "$PUBLIC_DIR/index.html"

# 3. Commit regenerated artifacts + version stamp only if they actually changed.
cd "$REPO_DIR"
git add "public/cv/docs/Paul Harvey - Resume.pdf" "public/cv/docs/Paul Harvey - Resume.docx" public/index.html
if git diff --cached --quiet; then
  echo "==> Artifacts unchanged"
else
  git commit -m "build: regenerate resume artifacts from resume.json

Co-Authored-By: deploy.sh <noreply@paulharvey.com.au>"
fi

# 4. Load deploy creds from the gitignored repo-root .env. Safe now that .env sits
#    OUTSIDE public/ and can never enter the wrangler deploy scope.
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ] && [ -f "$REPO_DIR/.env" ]; then
  set -a; source "$REPO_DIR/.env"; set +a
fi
if [ -z "${CLOUDFLARE_API_TOKEN:-}" ]; then
  echo "No CLOUDFLARE_API_TOKEN in env or .env — skipping direct deploy."
  echo "Push to main to deploy via GitHub Actions, or add CLOUDFLARE_API_TOKEN to .env"
  echo "(plus CLOUDFLARE_ACCOUNT_ID) for an immediate local deploy."
  exit 0
fi

export HOME="${WRANGLER_HOME:-/home/jason/.cache/wrangler-home}"

# 5. Deploy the public/ tree. No staging copy needed — public/ IS the publish root.
echo "==> Deploying public/ to Cloudflare Pages"
npx wrangler pages deploy "$PUBLIC_DIR" --project-name=paulharvey-com-au --branch=main --commit-dirty=true

echo "Done. Built from resume.json and deployed public/."
