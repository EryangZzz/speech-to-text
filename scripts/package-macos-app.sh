#!/usr/bin/env bash
set -euo pipefail

TARGET_TRIPLE="${1:-}"
BASE_DIR="src-tauri/target"
if [[ -n "$TARGET_TRIPLE" ]]; then
  BASE_DIR="src-tauri/target/${TARGET_TRIPLE}"
fi

APP_PATH="${BASE_DIR}/release/bundle/macos/WhisperDesktop.app"
OUT_PATH="${BASE_DIR}/release/bundle/macos/WhisperDesktop.app.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found: $APP_PATH"
  if [[ -n "$TARGET_TRIPLE" ]]; then
    echo "Run a build for target: $TARGET_TRIPLE"
  else
    echo "Run: npm run build:mac"
  fi
  exit 1
fi

rm -f "$OUT_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$OUT_PATH"

echo "Created: $OUT_PATH"
