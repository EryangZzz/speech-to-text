#!/usr/bin/env bash
set -euo pipefail

# Clean stale mounted volumes created by failed DMG packaging runs.
# This prevents create-dmg/bundle_dmg.sh from failing on repeated builds.
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "Skip cleanup: not macOS"
  exit 0
fi

devices=()
while IFS= read -r line; do
  [[ -n "$line" ]] && devices+=("$line")
done < <(
  hdiutil info 2>/dev/null \
    | awk '/\/Volumes\/WhisperDesktop([[:space:]]|$)/ {print $1}' \
    | sort -u
)

if [[ ${#devices[@]} -eq 0 ]]; then
  echo "No stale WhisperDesktop volumes found."
  exit 0
fi

echo "Found stale volumes: ${devices[*]}"
failed=0
for dev in "${devices[@]}"; do
  echo "Detaching ${dev} ..."
  if ! hdiutil detach -force "${dev}"; then
    failed=1
  fi
done

# Best-effort cleanup for stale temporary rw images.
find src-tauri/target -type f -name 'rw.*.WhisperDesktop_*.dmg' -delete 2>/dev/null || true

if [[ $failed -ne 0 ]]; then
  echo "Failed to detach some stale volumes. Close Finder windows opened on WhisperDesktop DMGs and retry."
  exit 1
fi

echo "Cleanup finished."
