# SpectrumSnek LoRa Receiver

A passive LoRa receiver plugin for [SpectrumSnek](https://github.com/nomore1007/spectrumsnek). It uses an RTL-SDR and the standalone C/C++ [LoraReceiverStandalone](https://github.com/mmmaly/LoraReceiverStandalone) decoder to scan a configured band, identify LoRa PHY settings, and report packets that pass the decoder's CRC checks.

## What it does

- Builds a pinned upstream lora_rx decoder during setup.
- Uses the decoder's sweep mode to scan the configured frequency range and auto-scan spreading factors and bandwidths.
- Accepts any LoRa sync word by default (-w 0), so unknown sync words can be observed.
- Prints receiver diagnostics and decoded packet output in the SpectrumSnek terminal.
- Logs decoded rx msg, rx str, rx ok, and CRC-valid output to lora-packets.log.
- Retains the original rtl_power energy monitor as an optional mode. Energy detections are candidates only, not verified LoRa packets.

This is a LoRa PHY decoder, not a universal application-layer decoder. Payloads may be binary or protocol-specific; MeshCore or other application protocols require their own parser.

## Install

From the SpectrumSnek checkout:

    git clone https://github.com/nomore1007/spectrumsnek-lora.git plugins/lora_monitor
    bash plugins/lora_monitor/setup.sh

On Debian/Ubuntu and Raspberry Pi OS, setup installs git, build-essential, librtlsdr-dev, and rtl-sdr. It checks out the receiver source into vendor/LoraReceiverStandalone/ at a pinned revision and builds only lora_rx. It does not build or run the upstream transmit utilities. The build itself does not open an SDR or transmit anything.

Setup requires network access to GitHub for the pinned upstream source.

## Run

From the SpectrumSnek root:

    python3 plugin_menu.py --run lora_monitor

The default mode is **packet decoding**. Press Ctrl+C to stop. The plugin uses SpectrumSnek's shared sdr_manager.py lock while the decoder owns the RTL-SDR. It does not terminate unrelated SDR processes that ignore that lock; stop other programs using the dongle before running.

## Configuration

Environment variables are read when the plugin starts.

| Variable | Default | Purpose |
| --- | --- | --- |
| SPECTRUMSNEK_LORA_MODE | decode | decode (packet decoder) or activity (energy-only survey) |
| SPECTRUMSNEK_LORA_START | 902M | Sweep start frequency; decoder mode accepts Hz or suffixes such as 902M |
| SPECTRUMSNEK_LORA_STOP | 928M | Sweep stop frequency |
| SPECTRUMSNEK_LORA_DWELL | 10 | Seconds per tuner position in decoder sweep mode (minimum 3) |
| LORA_RX_BIN | bundled checkout's lora_rx | Optional path to an already-built decoder |
| SPECTRUMSNEK_LORA_PACKET_LOG | $SPECTRUMSNEK_ROOT/lora-packets.log | Decoded packet log path |
| SPECTRUMSNEK_LORA_INTERVAL | 5 | Energy-mode delay between sweeps (minimum 2) |
| SPECTRUMSNEK_LORA_STEP | 25k | Energy-mode bin width |
| SPECTRUMSNEK_LORA_THRESHOLD_DB | 8 | Energy-mode threshold above median power |
| SPECTRUMSNEK_LORA_LOG | $SPECTRUMSNEK_ROOT/lora-events.csv | Energy-mode CSV event path |
| RTL_POWER_BIN | rtl_power | Energy-mode executable path/name |

The default 902–928 MHz range is appropriate for US 902–928 MHz LoRa use; configure a legal local band for your location. The receiver's default sweep is broad and CPU intensive because it auto-scans multiple spreading factors and bandwidths. A narrower band and longer dwell can improve observation time per channel.

To run the original RF energy monitor instead:

    SPECTRUMSNEK_LORA_MODE=activity python3 plugin_menu.py --run lora_monitor

## Output and limitations

- rx msg: is the decoded payload bytes; rx str: is a text rendering when available; rx ok: is the machine-readable CRC-valid payload in hex.
- A CRC-valid PHY packet does not identify the application protocol or guarantee that its payload is text.
- This plugin is receive-only. It does not call or run the upstream transmit utilities.
- SDR performance and packet reception depend on antenna, RF noise, gain, frequency correction, spreading factor, bandwidth, and signal strength. The standalone RTL-SDR decoder is not as sensitive as a dedicated LoRa transceiver chip in all conditions.
- The shared SpectrumSnek lock coordinates SpectrumSnek plugins only; it cannot prevent other applications from accessing the device.

## Tests

Python parser/configuration tests:

    python3 -m unittest discover -s plugins/lora_monitor/tests -v

The upstream decoder has an offline synthetic-frame test suite (make check) that exercises multiple spreading factors, bandwidths, sync words, CFO/noise, and end-to-end CRC verification. GitHub Actions runs those tests against the pinned revision. No physical SDR is needed for those software tests; hardware validation still requires an RTL-SDR.

## Third-party code and licensing notes

The plugin wrapper and its own tests are MIT-licensed; see LICENSE.txt. The decoder is checked out separately at install time rather than copied into the plugin's Git history. See THIRD_PARTY_NOTICES.md for upstream attribution and the licensing caveat for the decoder and its DSP lineage.

## SpectrumSnek integration

The plugin implements root __init__.py, MODULE_INFO, get_module_info(), and no-argument run(). The core plugin manager already maps the lora_monitor plugin ID to this repository.
