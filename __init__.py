"""SpectrumSnek LoRa receiver: packet decoding plus optional energy monitoring."""
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
from datetime import datetime, timezone
from pathlib import Path

try:
    from sdr_manager import SDRManager
except ImportError:
    SDRManager = None

MODULE_INFO = {
    "name": "📡 LoRa Receiver",
    "description": "Passive RTL-SDR LoRa packet decoder and RF energy monitor",
    "version": "0.2.0",
    "author": "SpectrumSnek",
    "category": "radio",
    "capabilities": [
        "LoRa PHY packet decoding",
        "SF/BW auto-scan",
        "CRC-verified packet logging",
        "Optional RF energy survey",
    ],
}


def get_module_info():
    return MODULE_INFO.copy()


def _log_error(message, exc_info=False):
    root = os.environ.get("SPECTRUMSNEK_ROOT", os.getcwd())
    try:
        with open(os.path.join(root, "error.log"), "a", encoding="utf-8") as f:
            f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] [lora_monitor] {message}\n")
            if exc_info:
                f.write(traceback.format_exc() + "\n")
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
            powers = [
                float(v) for v in row[6:]
                if v.strip() and v.strip().lower() not in ("nan", "inf", "-inf")
            ]
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


def _frequency_hz(value):
    """Convert a frequency setting like 915M, 125k, or 915000000 to Hz."""
    text = str(value).strip().lower()
    multiplier = 1
    if text.endswith("g"):
        multiplier, text = 1_000_000_000, text[:-1]
    elif text.endswith("m"):
        multiplier, text = 1_000_000, text[:-1]
    elif text.endswith("k"):
        multiplier, text = 1_000, text[:-1]
    return int(float(text) * multiplier)


def _decoder_binary():
    configured = os.environ.get("LORA_RX_BIN")
    if configured:
        candidate = shutil.which(configured) or (configured if os.path.isfile(configured) else None)
        if candidate and os.access(candidate, os.X_OK):
            return candidate
        raise RuntimeError(f"LORA_RX_BIN is set but not executable: {configured}")
    candidate = Path(__file__).resolve().parent / "vendor" / "LoraReceiverStandalone" / "lora_rx"
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    raise RuntimeError(
        "The LoRa decoder is not built. Run plugins/lora_monitor/setup.sh, "
        "or set LORA_RX_BIN to an executable lora_rx path."
    )


def _packet_log_path():
    root = os.environ.get("SPECTRUMSNEK_ROOT", os.getcwd())
    return os.environ.get("SPECTRUMSNEK_LORA_PACKET_LOG", os.path.join(root, "lora-packets.log"))


def _run_decoder():
    """Run the standalone decoder's passive band sweep and log packet output."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("The SpectrumSnek LoRa receiver currently requires Linux.")
    if SDRManager is None:
        raise RuntimeError("SpectrumSnek sdr_manager.py was not found. Launch through SpectrumSnek's plugin menu.")

    binary = _decoder_binary()
    start = _frequency_hz(os.environ.get("SPECTRUMSNEK_LORA_START", "902M"))
    stop = _frequency_hz(os.environ.get("SPECTRUMSNEK_LORA_STOP", "928M"))
    dwell = max(3, int(os.environ.get("SPECTRUMSNEK_LORA_DWELL", "10")))
    if start <= 0 or stop <= start:
        raise ValueError("LoRa sweep start/stop must be positive frequencies with stop greater than start.")

    command = [binary, "-W", f"{start},{stop},{dwell}", "-A", "-w", "0"]
    print("SpectrumSnek LoRa Packet Receiver")
    print(f"Decoder: {binary}")
    print(f"Passive sweep: {start / 1e6:g}–{stop / 1e6:g} MHz; dwell {dwell}s per tuner position")
    print("Auto-scanning spreading factors and bandwidths; accepting any sync word.")
    print(f"CRC-valid/decoded packet log: {_packet_log_path()}")
    print("Press Ctrl+C to stop. The receiver exclusively owns the shared RTL-SDR.\n")

    manager = SDRManager()
    process = None
    try:
        manager.acquire_device("lora_monitor")
        process = subprocess.Popen(
            command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, encoding="utf-8",
            errors="replace", bufsize=1,
        )
        with open(_packet_log_path(), "a", encoding="utf-8") as log:
            for raw_line in process.stdout:
                line = raw_line.rstrip("\r\n")
                if not line:
                    continue
                print(line, flush=True)
                if line.startswith(("rx msg:", "rx str:", "rx ok:")) or "CRC valid" in line:
                    stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
                    log.write(f"{stamp} {line}\n")
                    log.flush()
        code = process.wait()
        if code:
            raise RuntimeError(f"lora_rx exited with status {code}. Check the decoder output above.")
    except KeyboardInterrupt:
        print("\nStopping LoRa receiver...")
    except Exception as exc:
        _log_error(f"Decoder failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)
        manager.release_device()


def _run_activity_monitor():
    """Run the original rtl_power RF energy survey; detections are not decoded packets."""
    if not sys.platform.startswith("linux"):
        raise RuntimeError("LoRa Activity Monitor requires Linux and rtl_power.")
    rtl_power = shutil.which(os.environ.get("RTL_POWER_BIN", "rtl_power"))
    if not rtl_power:
        raise RuntimeError("rtl_power not found. Install rtl-sdr (Debian: sudo apt install rtl-sdr).")
    if SDRManager is None:
        raise RuntimeError("SpectrumSnek sdr_manager.py was not found. Launch through SpectrumSnek's plugin menu.")

    start = os.environ.get("SPECTRUMSNEK_LORA_START", "902M")
    stop = os.environ.get("SPECTRUMSNEK_LORA_STOP", "928M")
    step = os.environ.get("SPECTRUMSNEK_LORA_STEP", "25k")
    interval = max(2, int(os.environ.get("SPECTRUMSNEK_LORA_INTERVAL", "5")))
    threshold = float(os.environ.get("SPECTRUMSNEK_LORA_THRESHOLD_DB", "8"))
    print("SpectrumSnek LoRa RF Energy Monitor")
    print(f"Survey: {start}–{stop}, bin {step}; candidate threshold +{threshold:g} dB above median")
    print("Energy peaks are candidates only—not verified LoRa packets or decoded payloads.")
    print(f"Event log: {_event_log_path()}")
    print("Press Ctrl+C to stop. This survey temporarily owns the shared RTL-SDR.\n")

    manager = SDRManager()
    try:
        manager.acquire_device("lora_monitor")
        while True:
            fd, output_path = tempfile.mkstemp(prefix="spectrumsnek-lora-", suffix=".csv")
            os.close(fd)
            try:
                cmd = [rtl_power, "-f", f"{start}:{stop}:{step}", "-i", "1", "-1", output_path]
                try:
                    proc = subprocess.run(cmd, capture_output=True, text=True,
                                          timeout=max(30, interval * 4), check=False)
                except subprocess.TimeoutExpired:
                    print("\nrtl_power timed out; check SDR and frequency settings.", file=sys.stderr)
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
            stamp = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
            rows = [(stamp, int(freq), round(power, 2), round(noise, 2), threshold)
                    for freq, power in events]
            _append_events(rows)
            print(f"\r{stamp} | bins {len(samples):4d} | candidate peaks {len(events):3d} | median {noise:6.1f} dBFS",
                  end="", flush=True)
            if events:
                top = sorted(events, key=lambda item: item[1], reverse=True)[:5]
                print("\n  " + " | ".join(f"{freq/1e6:.4f} MHz {power:.1f} dBFS"
                                             for freq, power in top), flush=True)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nLoRa activity survey stopped.")
    except Exception as exc:
        _log_error(f"Survey failed: {type(exc).__name__}: {exc}", exc_info=True)
        raise
    finally:
        manager.release_device()


def run():
    """Run the LoRa packet decoder by default; select mode=activity for RF-only surveys."""
    mode = os.environ.get("SPECTRUMSNEK_LORA_MODE", "decode").strip().lower()
    if mode in ("decode", "decoder", "packet"):
        _run_decoder()
    elif mode in ("activity", "energy"):
        _run_activity_monitor()
    else:
        raise ValueError("SPECTRUMSNEK_LORA_MODE must be 'decode' or 'activity'.")


if __name__ == "__main__":
    run()
