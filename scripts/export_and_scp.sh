#!/usr/bin/env bash
set -euo pipefail

# Free Court Watcher dataset export + SCP upload
# Usage:
#   bash scripts/export_and_scp.sh
#
# Edit these first:
DEST_USER="youruser"
DEST_HOST="your.server.com"
DEST_PATH="/remote/path/free-court-watcher"

WORKDIR="/Users/varysoc/.openclaw/workspace/court-watch"
STAMP="$(date +%Y%m%d-%H%M%S)"
EXPORT_ROOT="$WORKDIR/exports"
BUNDLE_DIR="$EXPORT_ROOT/free-court-watcher-$STAMP"
ARCHIVE_PATH="$EXPORT_ROOT/free-court-watcher-$STAMP.tar.gz"

mkdir -p "$BUNDLE_DIR"

# Core dataset
cp "$WORKDIR/court_watch.db" "$BUNDLE_DIR/"

# Helpful source artifacts if present
if [ -d "$WORKDIR/data/raw" ]; then
  mkdir -p "$BUNDLE_DIR/data"
  cp -R "$WORKDIR/data/raw" "$BUNDLE_DIR/data/"
fi

if [ -f "$WORKDIR/logs/nightly.stdout.log" ]; then
  mkdir -p "$BUNDLE_DIR/logs"
  cp "$WORKDIR/logs/nightly.stdout.log" "$BUNDLE_DIR/logs/"
fi

if [ -f "$WORKDIR/logs/nightly.stderr.log" ]; then
  mkdir -p "$BUNDLE_DIR/logs"
  cp "$WORKDIR/logs/nightly.stderr.log" "$BUNDLE_DIR/logs/"
fi

cat > "$BUNDLE_DIR/README.txt" <<EOF
Free Court Watcher export
Created: $(date)
Contents:
- court_watch.db
- data/raw/ (if present)
- logs/ (if present)
EOF

cd "$EXPORT_ROOT"
tar -czf "$ARCHIVE_PATH" "$(basename "$BUNDLE_DIR")"

echo
echo "Archive ready: $ARCHIVE_PATH"
echo "Uploading to: ${DEST_USER}@${DEST_HOST}:${DEST_PATH}/"
echo "scp will prompt you for your SSH password if needed."
echo

scp "$ARCHIVE_PATH" "${DEST_USER}@${DEST_HOST}:${DEST_PATH}/"

echo
echo "Done. Uploaded: $ARCHIVE_PATH"
