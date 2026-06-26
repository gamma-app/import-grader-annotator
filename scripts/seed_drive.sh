#!/usr/bin/env bash
# Seed (or top up) a shared Google Drive data folder for the Slide-Pair Grader.
#
# Copies deck PDFs from the local ./data into the shared Drive folder so every
# teammate sees the same decks. It NEVER overwrites files that already exist in
# the destination (safe to re-run; won't clobber anyone's grades) and never
# copies rendered PNGs or exports.
#
# Usage:
#   ./scripts/seed_drive.sh "/path/to/Drive/slide-grader-data" [--with-annotations] [--dry-run]
#
#   --with-annotations  also copy local data/annotations/*.json (still won't overwrite)
#   --dry-run           show what would be copied without writing anything
#
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SRC="$ROOT/data"

DEST="${1:-}"
if [ -z "$DEST" ]; then
  echo "Usage: $0 <shared-drive-data-folder> [--with-annotations] [--dry-run]" >&2
  exit 1
fi
shift || true

WITH_ANNOTATIONS=0
DRY=()
for arg in "$@"; do
  case "$arg" in
    --with-annotations) WITH_ANNOTATIONS=1 ;;
    --dry-run) DRY=(-n) ;;
    *) echo "Unknown option: $arg" >&2; exit 1 ;;
  esac
done

command -v rsync >/dev/null 2>&1 || { echo "rsync is required but not found." >&2; exit 1; }
[ -d "$SRC/decks" ] || { echo "No local decks found at $SRC/decks" >&2; exit 1; }

mkdir -p "$DEST/decks" "$DEST/annotations" "$DEST/exports"

echo "==> Copying deck PDFs  ->  $DEST/decks  (existing files preserved)"
# -m prunes empty dirs so the legacy input/ideal/current render folders aren't recreated.
rsync -avm "${DRY[@]}" --ignore-existing \
  --include='*/' \
  --include='input.pdf' --include='ideal_output.pdf' --include='current_output.pdf' \
  --include='*_output.original.pdf' \
  --exclude='*' \
  "$SRC/decks/" "$DEST/decks/"

if [ "$WITH_ANNOTATIONS" -eq 1 ] && [ -d "$SRC/annotations" ]; then
  echo "==> Copying annotations  ->  $DEST/annotations  (existing files preserved)"
  rsync -av "${DRY[@]}" --ignore-existing "$SRC/annotations/" "$DEST/annotations/"
else
  echo "==> Skipping annotations (pass --with-annotations to seed them)"
fi

echo "Done. Set SLIDE_GRADER_DATA in your .env to: $DEST"
