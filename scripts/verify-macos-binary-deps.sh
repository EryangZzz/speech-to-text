#!/usr/bin/env bash
set -euo pipefail

if [[ "$#" -eq 0 ]]; then
  echo "Usage: $0 <binary1> [binary2 ...]"
  exit 1
fi

bad=0
for bin in "$@"; do
  if [[ ! -f "$bin" ]]; then
    echo "[ERROR] Missing file: $bin"
    bad=1
    continue
  fi
  if [[ ! -x "$bin" ]]; then
    echo "[ERROR] Not executable: $bin"
    bad=1
    continue
  fi

  if otool -L "$bin" | rg -q '/opt/homebrew|/usr/local/Cellar|Cellar'; then
    echo "[ERROR] Local/Homebrew dependency found in: $bin"
    otool -L "$bin" | rg '/opt/homebrew|/usr/local/Cellar|Cellar' || true
    bad=1
  else
    echo "[OK] $bin has no local brew dylib dependency"
  fi
done

if [[ "$bad" -ne 0 ]]; then
  exit 2
fi
