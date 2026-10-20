#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
elif command -v sudo >/dev/null 2>&1; then
  SUDO=(sudo)
else
  echo "Install rtl-sdr and build tools with your system package manager, then rerun." >&2
  exit 1
fi
if command -v apt-get >/dev/null 2>&1; then
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y rtl-sdr
else
  echo "Automatic dependency installation currently supports Debian/Ubuntu (apt-get). Install rtl-sdr manually." >&2
  exit 1
fi
command -v rtl_power >/dev/null || { echo "rtl_power was not found after installing rtl-sdr." >&2; exit 1; }
python3 -m py_compile "$ROOT/__init__.py"
echo "LoRa Activity Monitor setup complete. No SDR was opened during installation."
