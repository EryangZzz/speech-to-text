#!/usr/bin/env bash
set -euo pipefail

APP_PATH="src-tauri/target/release/bundle/macos/WhisperDesktop.app"
OUT_PATH="src-tauri/target/release/bundle/macos/WhisperDesktop.app.zip"

if [[ ! -d "$APP_PATH" ]]; then
  echo "App not found: $APP_PATH"
  echo "Run: npm run build:mac"
  exit 1
fi

rm -f "$OUT_PATH"
ditto -c -k --sequesterRsrc --keepParent "$APP_PATH" "$OUT_PATH"

echo "Created: $OUT_PATH"
