#!/usr/bin/env bash
# Install systemd path watcher for resume auto-sync.
# Run from HOST (not container).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_DIR="$HOME/.config/systemd/user"

mkdir -p "$UNIT_DIR"
cp "$SCRIPT_DIR/systemd/resume-sync.path" "$UNIT_DIR/"
cp "$SCRIPT_DIR/systemd/resume-sync.service" "$UNIT_DIR/"

# Check repo .env exists
ENV_FILE="$SCRIPT_DIR/../.env"
if [ ! -f "$ENV_FILE" ]; then
  cp "$SCRIPT_DIR/../.env.example" "$ENV_FILE"
  chmod 600 "$ENV_FILE"
  echo "Created .env from .env.example — set CLOUDFLARE_API_TOKEN before enabling."
fi

systemctl --user daemon-reload
systemctl --user enable --now resume-sync.path

echo "Watcher installed. Drop .docx in ~/SyncThing/Resume/ → auto deploys."
systemctl --user status resume-sync.path
