#!/usr/bin/env bash
# Install systemd path watcher for resume auto-sync.
# Run from HOST (not container).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"
cp "$SCRIPT_DIR/systemd/resume-sync.path" "$UNIT_DIR/"
cp "$SCRIPT_DIR/systemd/resume-sync.service" "$UNIT_DIR/"

# Create env file if missing
ENV_FILE="$HOME/.config/paulharvey-deploy.env"
if [ ! -f "$ENV_FILE" ]; then
  cat > "$ENV_FILE" <<'ENVEOF'
CLOUDFLARE_API_TOKEN=<REPLACE_ME>
CLOUDFLARE_ACCOUNT_ID=23f1dc885a85e77e0b3969b247bbf65f
WRANGLER_HOME=/home/jason/.cache/wrangler-home
ENVEOF
  chmod 600 "$ENV_FILE"
  echo "Created $ENV_FILE — set CLOUDFLARE_API_TOKEN before enabling."
fi

systemctl --user daemon-reload
systemctl --user enable --now resume-sync.path

echo "Watcher installed. Drop .docx in ~/SyncThing/Resume/ → auto deploys."
systemctl --user status resume-sync.path
