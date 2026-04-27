#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="$HOME/.ssh/free_court_watcher_beerus"
HOST_NAME="192.168.64.1"
HOST_USER="beerus"

if [ ! -f "$KEY_PATH.pub" ]; then
  echo "Missing public key: $KEY_PATH.pub"
  echo "Run setup_beerus_ssh_key.sh first."
  exit 1
fi

ssh-copy-id -i "$KEY_PATH.pub" "$HOST_USER@$HOST_NAME"

echo
echo "Done. Test with:"
echo "  ssh beerus-local"
