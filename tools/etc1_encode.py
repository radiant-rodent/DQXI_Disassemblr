"""Minimal ETC1 / ETC1A4 encoder for DQXI BCH texture replacement.

The 3DS stores ETC1 blocks in 8x8 tiles (four 4x4 blocks in the order
top-left, top-right, bottom-left, bottom-right). Colour words are little-endian
and use the same field layout as ``tools.texture_tool._etc1_block``.

This is a compact encoder, not a rate-distortion optimiser: each half-block uses
the quantised average colour and picks the best of the eight ETC1 modifier
tables. That is enough to replace diffuse textures without changing file size or
the BCH header.
"""

from __future__ import annotations

import numpy as np

_ETC_MOD = (
    (2, 8, -2, -8),
    (5, 17, -5, -17),
    (9, 29, -9, -29),
    (13, 42, -13, -42),
    (18, 60, -18, -60),
    (24, 80, -24, -80),
    (33, 106, -33, -106),
    (47, 183, -47, -183),
)


def _quant(v: float) -> int:
    return max(0, min(15, int(round(v / 17.0))))


def _half_pixels(px: np.ndarray, flip: int, second: int) -> list[tuple[int, int]]:
    out = []
    for x in range(4):
        for y in range(4):
            is_second = (y >= 2) if flip else (x >= 2)
            if is_second == bool(second):
                out.append((x, y))
    return out


def _encode_block(px: np.ndarray, alpha: bool) -> bytes:
    """Encodes one 4x4 RGBA block into 8 bytes (ETC1) or 16 bytes (ETC1A4)."""
    best: tuple[float, int, int, list[int], list[int], list[int], list[int]] | None = None
    for flip in (0, 1):
        table_idx: list[int] = []
        bases: list[list[int]] = []
        indices: list[list[int]] = []
        total_err = 0.0
        for second in (0, 1):
            coords = _half_pixels(px, flip, second)
            avg = [float(np.mean([px[y, x, c] for x, y in coords])) for c in range(3)]
            base = [_quant(v) for v in avg]
            best_half: tuple[float, int, list[int]] | None = None
            for ti, table in enumerate(_ETC_MOD):
                err = 0.0
                idxs: list[int] = []
                for x, y in coords:
                    p = px[y, x]
                    best_k = 0
                    best_d = 1e30
                    for k in range(4):
                        d = sum(
                            (float(p[c]) - (base[c] * 17 + table[k])) ** 2
                            for c in range(3)
                        )
                        if d < best_d:
                            best_d = d
                            best_k = k
                    err += best_d
                    idxs.append(best_k)
                if best_half is None or err < best_half[0]:
                    best_half = (err, ti, idxs)
            assert best_half is not None
            total_err += best_half[0]
            table_idx.append(best_half[1])
            bases.append(base)
            indices.append(best_half[2])
        if best is None or total_err < best[0]:
            best = (total_err, flip, table_idx[0], table_idx[1], bases[0], bases[1], indices[0], indices[1])

    assert best is not None
    _, flip, t1, t2, b1, b2, i1, i2 = best

    word = 0
    word |= (flip & 1) << 32
    # diff = 0: two independent 4-bit RGB colours
    word |= (t1 & 7) << 37
    word |= (t2 & 7) << 34
    word |= (b1[0] & 15) << 60
    word |= (b2[0] & 15) << 56
    word |= (b1[1] & 15) << 52
    word |= (b2[1] & 15) << 48
    word |= (b1[2] & 15) << 44
    word |= (b2[2] & 15) << 40

    for second, idxs in ((0, i1), (1, i2)):
        coords = _half_pixels(px, flip, second)
        for (x, y), idx in zip(coords, idxs):
            k = x * 4 + y
            word |= (idx & 1) << k
            word |= ((idx >> 1) & 1) << (16 + k)

    colour = int(word).to_bytes(8, "little")
    if not alpha:
        return colour

    alpha_word = 0
    for x in range(4):
        for y in range(4):
            a = _quant(float(px[y, x, 3]))
            alpha_word |= (a & 15) << ((x * 4 + y) * 4)
    return int(alpha_word).to_bytes(8, "little") + colour


def _pad_to_8(rgba: np.ndarray) -> np.ndarray:
    h, w = rgba.shape[:2]
    ph = (h + 7) // 8 * 8
    pw = (w + 7) // 8 * 8
    if ph == h and pw == w:
        return rgba
    out = np.empty((ph, pw, 4), np.uint8)
    out[:h, :w] = rgba
    out[h:, :] = rgba[h - 1:h, :]
    out[:, w:] = out[:, w - 1:w]
    return out


def encode_etc1(rgba: np.ndarray, alpha: bool = False) -> bytes:
    """Encodes an HxWx4 uint8 RGBA image to ETC1/ETC1A4 in the 3DS tile order."""
    rgba = _pad_to_8(np.asarray(rgba, dtype=np.uint8))
    h, w = rgba.shape[:2]
    out = bytearray()
    for ty in range(0, h, 8):
        for tx in range(0, w, 8):
            for bx, by in ((0, 0), (4, 0), (0, 4), (4, 4)):
                block = rgba[ty + by:ty + by + 4, tx + bx:tx + bx + 4]
                out += _encode_block(block, alpha)
    return bytes(out)
