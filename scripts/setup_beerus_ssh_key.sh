#!/usr/bin/env bash
set -euo pipefail

KEY_PATH="$HOME/.ssh/free_court_watcher_beerus"
HOST_ALIAS="beerus-local"
HOST_NAME="192.168.64.1"
HOST_USER="beerus"

mkdir -p "$HOME/.ssh"
chmod 700 "$HOME/.ssh"

if [ ! -f "$KEY_PATH" ]; then
  echo "Creating SSH key at $KEY_PATH"
  ssh-keygen -t ed25519 -f "$KEY_PATH" -C "free-court-watcher-vm-to-beerus"
else
  echo "Key already exists at $KEY_PATH"
fi

cat > "$HOME/.ssh/config.d_free_court_watcher_beerus" <<EOF
Host $HOST_ALIAS
  HostName $HOST_NAME
  User $HOST_USER
  IdentityFile $KEY_PATH
  IdentitiesOnly yes
  AddKeysToAgent yes
EOF

if [ -f "$HOME/.ssh/config" ]; then
  if ! grep -q "config.d_free_court_watcher_beerus" "$HOME/.ssh/config"; then
    printf '\nInclude ~/.ssh/config.d_free_court_watcher_beerus\n' >> "$HOME/.ssh/config"
  fi
else
  printf 'Include ~/.ssh/config.d_free_court_watcher_beerus\n' > "$HOME/.ssh/config"
fi
chmod 600 "$HOME/.ssh/config" "$HOME/.ssh/config.d_free_court_watcher_beerus"

if ssh-add --apple-use-keychain "$KEY_PATH" 2>/dev/null; then
  echo "Added key to ssh-agent and Apple keychain."
elif ssh-add "$KEY_PATH" 2>/dev/null; then
  echo "Added key to ssh-agent."
else
  echo "Run this next to add the key to your agent:"
  echo "  ssh-add --apple-use-keychain $KEY_PATH"
fi

echo
echo "Public key:"
cat "$KEY_PATH.pub"
echo
echo "Next step: install the public key on the host with:"
echo "  ssh-copy-id -i $KEY_PATH.pub $HOST_USER@$HOST_NAME"
echo "Then test with:"
echo "  ssh $HOST_ALIAS"
