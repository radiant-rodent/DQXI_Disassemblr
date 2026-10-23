"""Build a BCSTM stream from a WAV using an existing BCSTM as the template.

The encoder keeps the template's INFO/tables and replaces the audio payload with
linear 16-bit PCM, setting the codec to PCM16 (1). That makes audio replacement
possible without implementing a DSP-ADPCM encoder while still producing a valid
NintendoWare CSTM container. The DATA section is last in DQXI streams; the tool
refuses templates where it is not.
"""

from __future__ import annotations

import argparse
import struct
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.audio_tool import parse_bcstm_info


def _resample(samples: np.ndarray, src_rate: int, dst_rate: int) -> np.ndarray:
    if src_rate == dst_rate or src_rate <= 0 or len(samples) == 0:
        return samples
    n = max(1, int(round(len(samples) * dst_rate / src_rate)))
    x_old = np.linspace(0.0, 1.0, len(samples), endpoint=False)
    x_new = np.linspace(0.0, 1.0, n, endpoint=False)
    if samples.ndim == 1:
        return np.interp(x_new, x_old, samples).astype(np.int16)
    return np.stack(
        [np.interp(x_new, x_old, samples[:, c]).astype(np.int16) for c in range(samples.shape[1])],
        axis=1,
    )


def wav_to_pcm16(path: Path) -> tuple[np.ndarray, int, int]:
    with wave.open(str(path), "rb") as wf:
        channels = wf.getnchannels()
        width = wf.getsampwidth()
        rate = wf.getframerate()
        raw = wf.readframes(wf.getnframes())
    if width == 2:
        pcm = np.frombuffer(raw, dtype="<i2").astype(np.int16)
    elif width == 1:
        pcm = ((np.frombuffer(raw, dtype=np.uint8).astype(np.int16) - 128) << 8)
    else:
        raise SystemExit(f"unsupported WAV sample width {width * 8} bits")
    if channels > 1:
        pcm = pcm.reshape(-1, channels)
    return pcm, rate, channels


def build_bcstm(template: bytes, pcm: np.ndarray, rate: int, channels: int) -> bytes:
    info, audio_start = parse_bcstm_info(template)
    if channels != info.channels:
        raise SystemExit(
            f"template has {info.channels} channels but WAV has {channels}; "
            "convert the WAV to the matching channel count first"
        )
    pcm = _resample(pcm, rate, info.sample_rate)
    if pcm.ndim == 1:
        pcm = pcm.reshape(-1, 1)
    total = len(pcm)
    payload = pcm.astype("<i2", copy=False).tobytes()

    data_off = struct.unpack_from("<I", template, 0x30)[0]
    if audio_start != data_off + 0x20:
        raise SystemExit("unexpected DATA header layout")
    declared_data_size = struct.unpack_from("<I", template, data_off + 4)[0]
    if data_off + declared_data_size > len(template) or len(template) - (data_off + declared_data_size) > 31:
        raise SystemExit("DATA section is not the final section; cannot replace safely")

    out = bytearray(template[:audio_start])
    out += payload
    # align to 0x20 like the original streams
    while len(out) % 0x20:
        out.append(0)

    info_off = struct.unpack_from("<I", template, 0x18)[0]
    struct.pack_into("<B", out, info_off + 0x20, 1)  # PCM16
    struct.pack_into("<B", out, info_off + 0x21, 1 if info.loop else 0)
    struct.pack_into("<H", out, info_off + 0x22, info.channels)
    struct.pack_into("<I", out, info_off + 0x24, info.sample_rate)
    struct.pack_into("<I", out, info_off + 0x28, min(info.loop_start, total))
    struct.pack_into("<I", out, info_off + 0x2C, total)
    struct.pack_into("<I", out, info_off + 0x30, 1)
    struct.pack_into("<I", out, info_off + 0x34, total * 2)
    struct.pack_into("<I", out, info_off + 0x38, total)
    struct.pack_into("<I", out, info_off + 0x3C, total * 2)
    struct.pack_into("<I", out, info_off + 0x40, total)

    data_size = len(out) - data_off
    struct.pack_into("<I", out, data_off + 4, data_size)
    struct.pack_into("<I", out, 0x0C, len(out))
    return bytes(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--template", type=Path, required=True, help="existing BCSTM to reuse")
    ap.add_argument("--wav", type=Path, required=True, help="replacement PCM WAV")
    ap.add_argument("--out", type=Path, required=True, help="output BCSTM")
    args = ap.parse_args()
    pcm, rate, channels = wav_to_pcm16(args.wav)
    out = build_bcstm(args.template.read_bytes(), pcm, rate, channels)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_bytes(out)
    print(f"wrote {args.out} ({len(out)} bytes, {len(pcm)} samples, {rate} Hz, {channels} ch)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
