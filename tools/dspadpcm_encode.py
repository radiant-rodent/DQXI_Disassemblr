#!/usr/bin/env python3
"""Encode linear PCM to Nintendo DSP-ADPCM (the 3DS/DS 4-bit ADPCM).

The game streams its music as DSP-ADPCM inside BCSTM containers. Replacing a
track with a PCM16 stream (the old ``bcstm_encode`` behaviour) makes a valid
file but roughly doubles its size, which the 3DS has to stream from the SD
card. This module implements the missing encoder so replacements keep the
original codec and bandwidth.

Format, as decoded by :func:`tools.audio_tool.decode_dsp_adpcm_frame`:

* one 8-byte frame carries 14 samples: a header byte (predictor index in the
  high nibble, scale/shift in the low nibble) and seven bytes of two signed
  4-bit deltas (high nibble first);
* ``sample = clamp16(nibble * (1 << scale) + ((c0 * hist1 + c1 * hist2 + 1024) >> 11))``
  where ``(c0, c1)`` is the frame's predictor pair from the channel's 16-entry
  coefficient table (Q11 fixed point).

The encoder chooses a predictor and shift per frame, then writes each nibble
against the *actual* decoder history, so the decoded output tracks the input.
It is a greedy encoder, not a psychoacoustic optimiser; for music it is
accurate to a few hundred LSB and is fully deterministic.
"""

from __future__ import annotations

import numpy as np

# The eight coefficient pairs Nintendo's SDK ships (Q11: 2048 = 1.0). BCSTM
# files carry their own table; these are used when a template has none.
DEFAULT_COEFFS: tuple[tuple[int, int], ...] = (
    (0, 0),
    (3072, 0),
    (0, 3072),
    (3072, 3072),
    (2048, 1024),
    (1024, 2048),
    (2048, 0),
    (0, 2048),
)

SAMPLES_PER_FRAME = 14
FRAME_BYTES = 8


def _clamp16(values: np.ndarray) -> np.ndarray:
    return np.clip(values, -32768, 32767)


def choose_frames(samples: np.ndarray, coeffs=DEFAULT_COEFFS) -> tuple[np.ndarray, np.ndarray]:
    """Chooses (predictor, shift) per 14-sample frame from the input samples.

    Prediction uses the *source* history (open loop) to rank the 104
    predictor/shift combinations cheaply; the final nibble writing uses the
    decoder's reconstructed history so the result is self-consistent.
    """
    flat = np.asarray(samples, dtype=np.int32).reshape(-1)
    n = len(flat)
    frames = (n + SAMPLES_PER_FRAME - 1) // SAMPLES_PER_FRAME
    padded = np.zeros(frames * SAMPLES_PER_FRAME, np.int32)
    padded[:n] = flat
    flat = padded

    prev1 = np.empty_like(flat)
    prev1[0] = 0
    prev1[1:] = flat[:-1]
    prev2 = np.empty_like(flat)
    prev2[:2] = 0
    prev2[2:] = flat[:-2]

    best_err = np.full(frames, np.iinfo(np.int64).max, dtype=np.int64)
    best_pred = np.zeros(frames, np.int8)
    best_shift = np.zeros(frames, np.int8)
    coef = np.asarray(coeffs, dtype=np.int64)

    # Process in chunks so a long track does not allocate 8x the whole stream.
    chunk = SAMPLES_PER_FRAME * 8192
    for start in range(0, len(flat), chunk):
        end = min(len(flat), start + chunk)
        f0, f1 = start // SAMPLES_PER_FRAME, end // SAMPLES_PER_FRAME
        p1, p2 = prev1[start:end], prev2[start:end]
        target = flat[start:end]
        for p in range(min(8, len(coef))):
            pred = (coef[p, 0] * p1 + coef[p, 1] * p2 + 1024) >> 11
            residual = (target - pred).astype(np.int64)
            for shift in range(13):
                step = 1 << shift
                nib = np.clip(np.rint(residual / step), -8, 7).astype(np.int64)
                err = (nib * step - residual) ** 2
                per_frame = err.reshape(f1 - f0, SAMPLES_PER_FRAME).sum(axis=1)
                better = per_frame < best_err[f0:f1]
                if better.any():
                    best_err[f0:f1][better] = per_frame[better]
                    best_pred[f0:f1][better] = p
                    best_shift[f0:f1][better] = shift
    return best_pred, best_shift


def encode_channel(samples: np.ndarray, coeffs=DEFAULT_COEFFS) -> bytes:
    """Encodes one channel of PCM samples into DSP-ADPCM frames (8 bytes each)."""
    flat = np.asarray(samples, dtype=np.int32).reshape(-1)
    pred_idx, shifts = choose_frames(flat, coeffs)
    coef = np.asarray(coeffs, dtype=np.int64)
    frames = len(pred_idx)
    padded = np.zeros(frames * SAMPLES_PER_FRAME, np.int32)
    padded[: len(flat)] = flat[: frames * SAMPLES_PER_FRAME]

    out = bytearray(frames * FRAME_BYTES)
    h1 = h2 = 0
    pos = 0
    for f in range(frames):
        p = int(pred_idx[f])
        scale = int(shifts[f])
        c0, c1 = int(coef[p, 0]), int(coef[p, 1])
        out[pos] = ((p & 7) << 4) | (scale & 0xF)
        pos += 1
        target = padded[f * SAMPLES_PER_FRAME:(f + 1) * SAMPLES_PER_FRAME]
        for i in range(0, SAMPLES_PER_FRAME, 2):
            hi_target, lo_target = int(target[i]), int(target[i + 1])
            pred = (c0 * h1 + c1 * h2 + 1024) >> 11
            hi = int(np.clip(np.rint((hi_target - pred) / (1 << scale)), -8, 7))
            s_hi = max(-32768, min(32767, (hi << scale) + pred))
            h2, h1 = h1, s_hi
            pred = (c0 * h1 + c1 * h2 + 1024) >> 11
            lo = int(np.clip(np.rint((lo_target - pred) / (1 << scale)), -8, 7))
            s_lo = max(-32768, min(32767, (lo << scale) + pred))
            h2, h1 = h1, s_lo
            out[pos] = ((hi & 0xF) << 4) | (lo & 0xF)
            pos += 1
    return bytes(out)


def encode_interleaved(pcm: np.ndarray, channels: int, coeffs=None) -> list[bytes]:
    """Encodes interleaved PCM into one DSP-ADPCM byte stream per channel."""
    pcm = np.asarray(pcm, dtype=np.int32)
    if pcm.ndim == 1:
        pcm = pcm.reshape(-1, 1)
    if pcm.shape[1] != channels:
        raise ValueError(f"PCM has {pcm.shape[1]} channels, expected {channels}")
    out = []
    for ch in range(channels):
        table = (coeffs[ch] if coeffs and ch < len(coeffs) and coeffs[ch] else DEFAULT_COEFFS)
        out.append(encode_channel(pcm[:, ch], table))
    return out


def frames_for(samples: int) -> int:
    return (samples + SAMPLES_PER_FRAME - 1) // SAMPLES_PER_FRAME
