#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENDOR="$ROOT/vendor/LoraReceiverStandalone"
UPSTREAM_URL="https://github.com/mmmaly/LoraReceiverStandalone.git"
UPSTREAM_REV="beb7bad8554dc78133c90e83d594c2b49d00d1ea"

if [[ "${EUID}" -eq 0 ]]; then
  SUDO=()
elif command -v sudo >/dev/null 2>&1; then
  SUDO=(sudo)
else
  echo "Install git, build-essential, librtlsdr-dev, and rtl-sdr with your package manager, then rerun." >&2
  exit 1
fi

if command -v apt-get >/dev/null 2>&1; then
  "${SUDO[@]}" apt-get update
  "${SUDO[@]}" apt-get install -y git build-essential librtlsdr-dev rtl-sdr
else
  echo "Automatic dependency installation currently supports Debian/Ubuntu (apt-get)." >&2
  echo "Install git, a C++17 compiler, librtlsdr development files, and rtl-sdr manually." >&2
  exit 1
fi

mkdir -p "$ROOT/vendor"
if [[ ! -d "$VENDOR/.git" ]]; then
  if [[ -e "$VENDOR" ]]; then
    echo "Refusing to replace non-Git directory: $VENDOR" >&2
    exit 1
  fi
  git clone --no-checkout "$UPSTREAM_URL" "$VENDOR"
fi

git -C "$VENDOR" fetch --depth 1 origin "$UPSTREAM_REV"
git -C "$VENDOR" checkout --detach "$UPSTREAM_REV"
make -C "$VENDOR" clean
make -C "$VENDOR" lora_rx

command -v rtl_power >/dev/null || {
  echo "rtl_power was not found after installing rtl-sdr." >&2
  exit 1
}
python3 -m py_compile "$ROOT/__init__.py"

echo
echo "SpectrumSnek LoRa Receiver setup complete."
echo "Decoder: $VENDOR/lora_rx"
echo "Pinned upstream revision: $UPSTREAM_REV"
echo "The decoder was built only; no SDR was opened and no transmission was performed."
