# SpectrumSnek LoRa Activity Monitor

A standalone plugin for [SpectrumSnek](https://github.com/nomore1007/spectrumsnek) that uses an RTL-SDR to survey a LoRa frequency band and log RF energy peaks.

## Capability and limitation

This initial version is a **spectrum activity detector**, not a LoRa packet demodulator. It runs `rtl_power` sweeps, estimates median power, reports bins above a configurable threshold, and appends candidate peaks to CSV. Peaks may be other emitters, interference, or noise; they are not proof of LoRa traffic. No packet headers or payloads are decoded.

## Install

From the SpectrumSnek checkout:

```bash
git clone https://github.com/nomore1007/spectrumsnek-lora.git plugins/lora_monitor
bash plugins/lora_monitor/setup.sh
```

The setup script installs Debian/Ubuntu's `rtl-sdr` package and checks Python syntax. It does not open the SDR.

The plugin uses SpectrumSnek's shared `sdr_manager.py` lock. It cannot lock out unrelated applications that ignore that lock, so stop other SDR programs before starting a survey.

## Run

From the SpectrumSnek root:

```bash
python3 plugin_menu.py --run lora_monitor
```

Press Ctrl+C to stop. Defaults survey the US 902–928 MHz ISM band. Configure the appropriate local band before use.

| Environment variable | Default | Purpose |
| --- | --- | --- |
| `SPECTRUMSNEK_LORA_START` | `902M` | Start frequency |
| `SPECTRUMSNEK_LORA_STOP` | `928M` | Stop frequency |
| `SPECTRUMSNEK_LORA_STEP` | `25k` | Spectrum bin width |
| `SPECTRUMSNEK_LORA_INTERVAL` | `5` | Seconds between sweeps (minimum 2) |
| `SPECTRUMSNEK_LORA_THRESHOLD_DB` | `8` | Candidate threshold above median power |
| `SPECTRUMSNEK_LORA_LOG` | `$SPECTRUMSNEK_ROOT/lora-events.csv` | Event CSV path |
| `RTL_POWER_BIN` | `rtl_power` | Executable path/name |

Events include timestamp, frequency, power, median power, and threshold. Errors are logged to SpectrumSnek's `error.log`.

## Requirements

- Linux / Debian-based Raspberry Pi OS
- RTL-SDR-compatible receiver and working USB permissions
- `rtl_power` from the `rtl-sdr` package
- Python 3 and SpectrumSnek's shared `sdr_manager.py`

No third-party Python packages are required.

## SpectrumSnek integration

The plugin implements root `__init__.py`, `MODULE_INFO`, `get_module_info()`, and no-argument `run()`. To list it in the core's **Installed Plugins** installer, `plugin_manager.sh` needs a `lora_monitor` repository mapping and label. That core change must be submitted separately; this repository does not modify the core project.

## License

MIT. See [LICENSE.txt](LICENSE.txt).
