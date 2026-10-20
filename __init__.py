""""SpectrumSnek passive LoRa-band RF activity monitor."""
from __future__ import annotations

import csv
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from datetime import datetime

try:
    from sdr_manager import SDRManager
except ImportError:
    SDRManager = None

MODULE_INFO = {
    "name": "📡 LoRa Activity Monitor",
    "description": "Passive RTL-SDR survey of LoRa bands with RF energy event logging",
    "version": "0.1.0",
    "author": "SpectrumSnek",
    "category": "radio",
    "capabilities": ["RTL-SDR spectrum survey", "energy threshold events", "CSV event log"],
}


def get_module_info():
    return MODULE_INFO.copy()


def _log_error(message, exc_info=False):
    root = os.environ.get("SPECTRUMSNEK_ROOT", os.getcwd())
    try:
        with open(os.path.join(root, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [lora_monitor] {message}\\n")
            if exc_info:
                f.write(traceback.format_exc() + "\\n")
    except OSError:
        print(message, file=sys.stderr)


def _parse_rtl_power(output):
    """Parse rtl_power CSV rows into (center_hz, power_dbfs) samples."""
    samples = []
    for row in csv.reader(io.StringIO(output)):
        if len(row) < 7:
            continue
        try:
            low_hz, high_hz, step_hz = map(float, row[2:5])
            powers = [float(v) for v in row[6:] if v.strip() and v.strip().lower() not in ("nan", "inf", "-inf")]
        except (ValueError, IndexError):
            continue
        for index, power in enumerate(powers):
            samples.append((low_hz + (index + 0.5) * step_hz, power))
    return samples


def _event_log_path():
    root = os.environ.get("SPECTRUMSNEK_ROOT", os.getcwd())
    return os.environ.get("SPECTRUMSNEK_LORA_LOG", os.path.join(root, "lora-events.csv"))


def _append_events(events):
    if not events:
        return
    path = _event_log_path()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    new_file = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["timestamp_utc", "frequency_hz", "power_dbfs", "noise_floor_dbfs", "threshold_db"])
        writer.writerows(events)


def run():
    """Run a passive RTL-SDR energy survey; it does not demodulate LoRa packets."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("LoRa Activity Monitor requires Linux and rtl_power.")
    rtl_power = shutil.which(os.environ.get("RTL_POWER_BIN", "rtl_power"))
    if not rtl_power:
        raise RuntimeError("rtl_power not found. Install rtl-sdr (Debian: sudo apt install rtl-sdr).")
    if SDRManager is None:
        raise RuntimeError("SpectrumSnek sdr_manager.py was not found. Launch through SpectrumSnek's plugin menu.")

    # US 902–928 MHz ISM defaults. Set start/stop for your local region.
    start = os.environ.get("SPECTRUMSNEK_LORA_START", "902M")
    stop = os.environ.get("SPECTRUMSNEK_LORA_STOP", "928M")
    step = os.environ.get("SPECTRUMSNEK_LORA_STEP", "25k")
    interval = max(2, int(os.environ.get("SPECTRUMSNEK_LORA_INTERVAL", "5")))
    threshold = float(os.environ.get("SPECTRUMSNEK_LORA_THRESHOLD_DB", "8"))
    print("SpectrumSnek LoRa Activity Monitor")
    print(f"Survey: {start}–{stop}, bin {step}; candidate threshold +{threshold:g} dB above median")
    print("Energy peaks are candidates only—not verified LoRa packets or decoded payloads.")
    print(f"Event log: {_event_log_path()}")
    print("Press Ctrl+C to stop. This survey temporarily owns the shared RTL-SDR.\\n")

    manager = SDRManager()
    try:
        manager.acquire_device("lora_monitor")
        while True:
            # rtl_power writes CSV to a named output file; -1 requests one sweep.
            fd, output_path = tempfile.mkstemp(prefix="spectrumsnek-lora-", suffix=".csv")
            os.close(fd)
            try:
                cmd = [rtl_power, "-f", f"{start}:{stop}:{step}", "-i", "1", "-1", output_path]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True,
                                          timeout=max(30, interval * 4), check=False)
                except subprocess.TimeoutExpired:
                    print("\\nrtl_power timed out; check SDR and frequency settings.", file=sys.stderr)
                    time.sleep(interval)
                    continue
                if proc.returncode != 0:
                    detail = (proc.stderr or proc.stdout or "no diagnostic output").strip()
                    raise RuntimeError(f"rtl_power failed (exit {proc.returncode}): {detail}")
                with open(output_path, "r", encoding="utf-8", errors="replace") as f:
                    samples = _parse_rtl_power(f.read())
            finally:
                try:
                    os.unlink(output_path)
                except FileNotFoundError:
                    pass

            if len(samples) < 8:
                detail = proc.stderr.strip() if proc.stderr else ""
                raise RuntimeError("rtl_power returned too few parseable samples. " + detail)
            powers = sorted(power for _, power in samples)
            noise = powers[len(powers) // 2]
            events = [(freq, power) for freq, power in samples if power >= noise + threshold]
            stamp = datetime.now().astimezone().isoformat(timespec="seconds")
            rows = [(stamp, int(freq), round(power, 2), round(noise, 2), threshold)
                    for freq, power in events]
            _append_events(rows)
            print(f"\\r{stamp} | bins {len(samples):4d} | candidate peaks {len(events):3d} | median {noise:6.1f} dBFS",
                  end="", flush=True)
            if events:
                top = sorted(events, key=lambda item: item[1], reverse=True)[:5]
                print("\\n  " + " | ".join(f"{freq/1e6:.4f} MHz {power:.1f} dBFS"
                                             for freq, power in top), flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\\nLoRa activity survey stopped.")
    except Exception as exc:
        _log_error(f"Survey failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise
    finally:
        manager.release_device()


if __name__ == "__main__":
    run()
