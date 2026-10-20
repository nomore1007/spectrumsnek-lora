# SpectrumSnek LoRa SDR Plugin

Passive LoRa-band activity monitoring plugin for SpectrumSnek. The initial implementation provides an RTL-SDR spectrum survey and event log; RF energy detections are **not** proof of a LoRa packet and do not decode packet contents. LoRa packet decoding requires a compatible LoRa SDR decoder and is intentionally kept separate from energy detection.
