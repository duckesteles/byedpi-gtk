#!/usr/bin/env bash
set -euo pipefail

TAG="$1"
DEST="$2"
WORKTMP="$(mktemp -d)"
trap 'rm -rf "$WORKTMP"' EXIT

curl -fsSL "https://api.github.com/repos/hufrea/byedpi/releases/tags/${TAG}" \
  | python3 -c "
import json, sys
for asset in json.load(sys.stdin)['assets']:
    if asset['name'].endswith('.tar.gz'):
        print(asset['browser_download_url'])
" > "$WORKTMP/urls.txt"

while read -r url; do
  archive="$WORKTMP/$(basename "$url")"
  curl -fsSL -o "$archive" "$url"
  tar -xzf "$archive" -C "$WORKTMP"
done < "$WORKTMP/urls.txt"

install -d "$DEST"
for bin in "$WORKTMP"/ciadpi-*; do
  install -Dm755 "$bin" "$DEST/$(basename "$bin")"
done
ls -1 "$DEST"
