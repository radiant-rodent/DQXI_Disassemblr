"""WAV peak extraction for waveform drawing."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

_CACHE: dict[tuple, tuple] = {}


def _to_float(raw: bytes, width: int) -> np.ndarray:
    if width == 1:
        arr = np.frombuffer(raw, dtype=np.uint8).astype(np.float32)
        return (arr - 128.0) / 128.0
    if width == 2:
        return np.frombuffer(raw, dtype="<i2").astype(np.float32) / 32768.0
    if width == 3:
        arr = np.frombuffer(raw, dtype=np.uint8).reshape(-1, 3).astype(np.int32)
        val = (arr[:, 0] | (arr[:, 1] << 8) | (arr[:, 2] << 16))
        val = np.where(val & 0x800000, val - 0x1000000, val)
        return val.astype(np.float32) / 8388608.0
    if width == 4:
        return np.frombuffer(raw, dtype="<i4").astype(np.float32) / 2147483648.0
    raise ValueError(f"unsupported sample width {width}")


def peaks(path: str | Path, buckets: int = 900) -> tuple[np.ndarray, np.ndarray, dict]:
    """Return (mins, maxs, info) with *buckets* peak pairs for a WAV file."""
    key = (str(path), buckets)
    cached = _CACHE.get(key)
    if cached is not None:
        return cached
    info: dict = {"channels": 0, "rate": 0, "frames": 0, "duration": 0.0, "width": 0}
    mins = np.zeros(buckets, dtype=np.float32)
    maxs = np.zeros(buckets, dtype=np.float32)
    try:
        with wave.open(str(path), "rb") as w:
            info["channels"] = w.getnchannels()
            info["rate"] = w.getframerate()
            info["frames"] = w.getnframes()
            info["width"] = w.getsampwidth()
            nch = max(1, info["channels"])
            width = info["width"]
            if info["rate"]:
                info["duration"] = info["frames"] / float(info["rate"])
            raw = w.readframes(info["frames"])
        data = _to_float(raw, width)
        if nch > 1:
            usable = (len(data) // nch) * nch
            data = data[:usable].reshape(-1, nch).mean(axis=1)
        n = len(data)
        if n == 0:
            return mins, maxs, info
        chunk = max(1, n // buckets)
        usable = (n // chunk) * chunk
        reshaped = data[:usable].reshape(-1, chunk)
        mn = reshaped.min(axis=1)
        mx = reshaped.max(axis=1)
        count = min(buckets, len(mn))
        mins[:count] = mn[:count]
        maxs[:count] = mx[:count]
        if count < buckets:
            mins[count:] = 0.0
            maxs[count:] = 0.0
        info["peak"] = float(max(abs(mn).max() if count else 0.0, abs(mx).max() if count else 0.0))
    except Exception as exc:
        info["error"] = str(exc)
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[key] = (mins, maxs, info)
    return mins, maxs, info
