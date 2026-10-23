#!/usr/bin/env python3
"""
tools/blz.py - Backward LZ77 (BLZ) Codec for Nintendo 3DS (CTR-SDK)

Implements CTR-SDK backward LZ77 decompression and bit-matching compression.
Features:
- Pure Python fallback for all operations.
- Native C compiler acceleration (cached in tempdir) when GCC is available.
- Enforces strict CTR-SDK constraints:
    * Search window: 4096 bytes (0x1000)
    * Match distance: 3..4096 (12-bit encoding: distance - 3)
    * Match length: 3..18 (4-bit encoding: length - 3)
    * Non-overlapping copy rule: max_length = min(18, distance, remaining)
    * Chain search with closest-match tie-breaking

CLI:
    python tools/blz.py -d <input_file> <output_file>
    python tools/blz.py -c <input_file> <output_file>
"""

import argparse
import ctypes
import hashlib
import os
import struct
import subprocess
import sys
import tempfile

_NATIVE_C_SRC = r"""
#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#ifdef _WIN32
#define EXPORT __declspec(dllexport)
#else
#define EXPORT
#endif

#define MAX_LEN 18
#define MIN_LEN 3
#define MAX_DIST 4096
#define MIN_DIST 3
#define HBITS 16
#define HASH3(q) ((((uint32_t)in[(q)] << 8) ^ ((uint32_t)in[(q)+1] << 4) ^ (uint32_t)in[(q)+2]) * 2654435761u >> (32 - HBITS))

EXPORT int blz_decompress(const uint8_t *in, uint32_t in_size, uint8_t *out, uint32_t out_size)
{
    if (in_size < 8) return -1;
    uint32_t tb, extra;
    memcpy(&tb, in + in_size - 8, 4);
    memcpy(&extra, in + in_size - 4, 4);
    if (extra > 0x08000000) return -2;
    uint32_t top = tb & 0xFFFFFF, bottom = tb >> 24;
    if (bottom < 8 || bottom > 11 || top < bottom || top > in_size) return -2;
    if (out_size != in_size + extra) return -3;
    memcpy(out, in, in_size);
    int64_t dst = out_size;
    int64_t src = in_size - bottom;
    int64_t end = in_size - top;
    while (src > end) {
        uint8_t flag = out[--src];
        for (int i = 0; i < 8; i++) {
            if (!((flag << i) & 0x80)) {
                if (dst - end < 1 || src - end < 1) return -4;
                out[--dst] = out[--src];
            } else {
                if (src - end < 2) return -5;
                uint32_t hi = out[--src];
                uint32_t lo = out[--src];
                uint32_t tok = (hi << 8) | lo;
                uint32_t off = (tok & 0x0FFF) + 3;
                uint32_t len = ((tok >> 12) & 0xF) + 3;
                if (dst - end < (int64_t)len) return -6;
                if (dst + off > out_size) return -7;
                for (uint32_t j = 0; j < len; j++) {
                    out[dst - 1] = out[dst - 1 + off];
                    dst--;
                }
            }
            if (src <= end) break;
        }
    }
    if (dst != end) return -8;
    return 0;
}

/* allow_overlap = 0 reproduces the CTR-SDK compressor exactly (match length is
   capped at the match distance); the retail .code bit-match depends on it.
   allow_overlap = 1 lets runs use long overlapping matches: still valid BLZ for
   the byte-by-byte decoder, and smaller, which repacked PACA files need. */
EXPORT int64_t blz_compress_ex(const uint8_t *in, uint32_t in_size, uint8_t *out, uint32_t out_cap, int allow_overlap)
{
    if (in_size <= 8 || out_cap < in_size) return 0;
    int32_t *head = (int32_t *)malloc(sizeof(int32_t) << HBITS);
    int32_t *prev = (int32_t *)malloc(sizeof(int32_t) * (size_t)in_size);
    size_t max_expansion = (size_t)(in_size >> 3) + 32;
    uint8_t *tmp = (uint8_t *)malloc(in_size + max_expansion);
    if (!head || !prev || !tmp) { free(head); free(prev); free(tmp); return -1; }
    for (int i = 0; i < (1 << HBITS); i++) head[i] = -1;

    int64_t p = in_size;
    int64_t d = in_size;
    int ok = 1;
    int64_t inserted = in_size;

    while (p > 0 && ok) {
        if (d < 1) { ok = 0; break; }
        int64_t flagpos = --d;
        tmp[flagpos] = 0;
        for (int i = 0; i < 8; i++) {
            while (inserted > p) {
                inserted--;
                if (inserted + 3 <= in_size) {
                    uint32_t h = HASH3(inserted);
                    prev[inserted] = head[h];
                    head[h] = (int32_t)inserted;
                }
            }
            int best_len = 0, best_dist = 0;
            if (p >= 3) {
                int64_t t = p - 3;
                uint32_t h = HASH3(t);
                int32_t s = head[h];
                int chain = 4096;
                while (s >= 0 && chain-- > 0) {
                    int64_t dist = s - t;
                    if (dist > MAX_DIST) break;
                    if (dist >= MIN_DIST) {
                        int maxlen = MAX_LEN;
                        if (maxlen > p) maxlen = (int)p;
                        if (!allow_overlap && maxlen > dist) maxlen = (int)dist; // CTR-SDK non-overlapping rule
                        
                        int l = 0;
                        while (l < maxlen && p - 1 - l + dist < in_size && in[p - 1 - l] == in[p - 1 - l + dist]) l++;
                        if (l > best_len) {
                            best_len = l;
                            best_dist = (int)dist;
                            if (l == MAX_LEN) break;
                        }
                    }
                    s = prev[s];
                }
            }
            if (best_len >= 3) {
                if (d < 2) { ok = 0; break; }
                tmp[flagpos] |= (uint8_t)(0x80 >> i);
                uint32_t tok = ((uint32_t)(best_len - 3) << 12) | (uint32_t)(best_dist - 3);
                tmp[--d] = (uint8_t)(tok >> 8);
                tmp[--d] = (uint8_t)(tok & 0xFF);
                p -= best_len;
            } else {
                if (d < 1) { ok = 0; break; }
                tmp[--d] = in[--p];
            }
            if (p <= 0) break;
        }
    }
    free(head); free(prev);
    if (!ok || d < 0 || d >= in_size) { free(tmp); return 0; }

    uint8_t *cbuf = tmp + d;
    int64_t csize = in_size - d;
    int64_t orig = in_size, cpos = csize;
    int64_t orig_safe = 0, comp_safe = 0;
    int over = 0;
    while (orig > 0) {
        if (cpos <= 0) { free(tmp); return 0; }
        uint8_t flag = cbuf[--cpos];
        for (int i = 0; i < 8; i++) {
            if (!((flag << i) & 0x80)) {
                if (cpos < 1 || orig < 1) { free(tmp); return 0; }
                cpos--; orig--;
            } else {
                if (cpos < 2) { free(tmp); return 0; }
                int len = ((cbuf[--cpos] >> 4) & 0xF) + 3;
                cpos--;
                orig -= len;
                if (orig < cpos) { orig_safe = orig; comp_safe = cpos; over = 1; break; }
            }
            if (orig <= 0) break;
        }
        if (over) break;
    }
    int64_t comp_len = csize - comp_safe;
    int64_t pad_off = orig_safe + comp_len;
    int64_t foot_off = (pad_off + 3) & ~3LL;
    int64_t total = foot_off + 8;
    int64_t top = total - orig_safe;
    int64_t bottom = total - pad_off;
    if (total >= in_size || top > 0xFFFFFF) { free(tmp); return 0; }
    memcpy(out, in, (size_t)orig_safe);
    memmove(out + orig_safe, cbuf + comp_safe, (size_t)comp_len);
    memset(out + pad_off, 0xFF, (size_t)(foot_off - pad_off));
    uint32_t tb = (uint32_t)top | ((uint32_t)bottom << 24);
    uint32_t extra = (uint32_t)(in_size - total);
    memcpy(out + foot_off, &tb, 4);
    memcpy(out + foot_off + 4, &extra, 4);
    free(tmp);
    return total;
}

EXPORT int64_t blz_compress(const uint8_t *in, uint32_t in_size, uint8_t *out, uint32_t out_cap)
{
    return blz_compress_ex(in, in_size, out, out_cap, 0);
}
"""

_lib = None
_lib_failed = False


def _get_native_lib():
    global _lib, _lib_failed
    if _lib is not None:
        return _lib
    if _lib_failed:
        return None

    try:
        temp_dir = tempfile.gettempdir()
        src_hash = hashlib.sha256(_NATIVE_C_SRC.encode("utf-8")).hexdigest()[:8]
        dll_name = f"dq11_blz_accel_{src_hash}.dll" if sys.platform == "win32" else f"libdq11_blz_accel_{src_hash}.so"
        dll_path = os.path.join(temp_dir, dll_name)
        c_path = os.path.join(temp_dir, f"dq11_blz_accel_{src_hash}.c")

        need_rebuild = not os.path.exists(dll_path)
        if not need_rebuild:
            try:
                lib = ctypes.CDLL(dll_path)
                lib.blz_decompress.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
                lib.blz_decompress.restype = ctypes.c_int
                lib.blz_compress.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
                lib.blz_compress.restype = ctypes.c_int64
                lib.blz_compress_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int]
                lib.blz_compress_ex.restype = ctypes.c_int64
                _lib = lib
                return _lib
            except Exception:
                need_rebuild = True

        if need_rebuild:
            with open(c_path, "w", encoding="utf-8") as f:
                f.write(_NATIVE_C_SRC)
            cmd = ["gcc", "-O3", "-shared", "-o", dll_path, c_path]
            res = subprocess.run(cmd, capture_output=True)
            if res.returncode == 0 and os.path.exists(dll_path):
                lib = ctypes.CDLL(dll_path)
                lib.blz_decompress.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
                lib.blz_decompress.restype = ctypes.c_int
                lib.blz_compress.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32]
                lib.blz_compress.restype = ctypes.c_int64
                lib.blz_compress_ex.argtypes = [ctypes.c_char_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int]
                lib.blz_compress_ex.restype = ctypes.c_int64
                _lib = lib
                return _lib
    except Exception:
        pass

    _lib_failed = True
    return None


def py_decompress(data: bytes) -> bytes:
    """Pure-Python CTR-SDK Backward LZ77 decompression."""
    n = len(data)
    if n < 8:
        raise ValueError("Data too short for BLZ header")
    tb, extra = struct.unpack_from("<II", data, n - 8)
    if extra > 0x08000000:
        raise ValueError("BLZ extra size exceeds maximum CTR limit")
    top, bottom = tb & 0xFFFFFF, tb >> 24
    if bottom < 8 or bottom > 11 or top < bottom or top > n:
        raise ValueError("Invalid BLZ header parameters")
    out = bytearray(data) + bytearray(extra)
    dst = len(out)
    src = n - bottom
    end = n - top
    while src > end:
        src -= 1
        flag = out[src]
        for i in range(8):
            if not ((flag << i) & 0x80):
                if dst <= end or src <= end:
                    raise ValueError("BLZ decompression stream corrupted")
                src -= 1
                dst -= 1
                out[dst] = out[src]
            else:
                if src - end < 2:
                    raise ValueError("BLZ decompression stream truncated token")
                hi = out[src - 1]
                lo = out[src - 2]
                src -= 2
                tok = (hi << 8) | lo
                off = (tok & 0xFFF) + 3
                ln = (tok >> 12) + 3
                if dst - end < ln:
                    raise ValueError("BLZ decompression destination underflow")
                if dst + off > len(out):
                    raise ValueError("BLZ decompression copy offset out of bounds")
                for _ in range(ln):
                    dst -= 1
                    out[dst] = out[dst + off]
            if src <= end:
                break
    if dst != end:
        raise ValueError("BLZ decompression stream truncated or unaligned")
    return bytes(out)


def py_compress(data: bytes) -> bytes | None:
    """Pure-Python CTR-SDK Backward LZ77 compression with non-overlapping matches."""
    in_size = len(data)
    if in_size <= 8:
        return None

    max_expansion = (in_size >> 3) + 32
    tmp = bytearray(in_size + max_expansion)
    p = in_size
    d = in_size
    inserted = in_size
    head = {}

    while p > 0:
        if d < 1:
            return None
        d -= 1
        flagpos = d
        tmp[flagpos] = 0
        for i in range(8):
            while inserted > p:
                inserted -= 1
                if inserted + 3 <= in_size:
                    k = bytes(data[inserted:inserted+3])
                    if k not in head:
                        head[k] = []
                    head[k].append(inserted)

            best_len = 0
            best_dist = 0
            if p >= 3:
                t = p - 3
                k = bytes(data[t:t+3])
                if k in head:
                    for s in reversed(head[k]):
                        dist = s - t
                        if dist > 4096:
                            break
                        if dist >= 3:
                            maxlen = min(18, dist, p)
                            l = 0
                            while l < maxlen and p - 1 - l + dist < in_size and data[p - 1 - l] == data[p - 1 - l + dist]:
                                l += 1
                            if l > best_len:
                                best_len = l
                                best_dist = dist
                                if l == 18:
                                    break

            if best_len >= 3:
                if d < 2:
                    return None
                tmp[flagpos] |= (0x80 >> i)
                tok = ((best_len - 3) << 12) | (best_dist - 3)
                d -= 1
                tmp[d] = tok >> 8
                d -= 1
                tmp[d] = tok & 0xFF
                p -= best_len
            else:
                if d < 1:
                    return None
                d -= 1
                p -= 1
                tmp[d] = data[p]
            if p <= 0:
                break

    if d < 0 or d >= in_size:
        return None

    cbuf = tmp[d:in_size]
    csize = len(cbuf)
    orig = in_size
    cpos = csize
    orig_safe = 0
    comp_safe = 0
    over = False

    while orig > 0:
        if cpos <= 0:
            return None
        cpos -= 1
        flag = cbuf[cpos]
        for i in range(8):
            if not ((flag << i) & 0x80):
                if cpos < 1 or orig < 1:
                    return None
                cpos -= 1
                orig -= 1
            else:
                if cpos < 2:
                    return None
                ln = ((cbuf[cpos - 1] >> 4) & 0xF) + 3
                cpos -= 2
                orig -= ln
                if orig < cpos:
                    orig_safe = orig
                    comp_safe = cpos
                    over = True
                    break
            if orig <= 0:
                break
        if over:
            break

    comp_len = csize - comp_safe
    pad_off = orig_safe + comp_len
    foot_off = (pad_off + 3) & ~3
    total = foot_off + 8
    top = total - orig_safe
    bottom = total - pad_off
    if total >= in_size or top > 0xFFFFFF:
        return None

    out = bytearray(total)
    out[:orig_safe] = data[:orig_safe]
    out[orig_safe:orig_safe + comp_len] = cbuf[comp_safe:]
    out[pad_off:foot_off] = b"\xFF" * (foot_off - pad_off)
    struct.pack_into("<II", out, foot_off, top | (bottom << 24), in_size - total)
    return bytes(out)


def decompress(data: bytes) -> bytes:
    """Decompress BLZ compressed data."""
    if len(data) < 8:
        raise ValueError("Input data too small for BLZ stream")
    tb, extra = struct.unpack_from("<II", data, len(data) - 8)
    if extra > 0x08000000:
        raise ValueError("BLZ extra size exceeds maximum CTR limit")
    top, bottom = tb & 0xFFFFFF, tb >> 24
    if bottom < 8 or bottom > 11 or top < bottom or top > len(data):
        raise ValueError("Invalid BLZ header parameters")

    lib = _get_native_lib()
    if lib:
        out_size = len(data) + extra
        buf = ctypes.create_string_buffer(out_size)
        rc = lib.blz_decompress(data, len(data), buf, out_size)
        if rc == 0:
            return buf.raw
        else:
            raise ValueError(f"BLZ decompression failed with code {rc}")
    return py_decompress(data)


def compress(data: bytes, allow_overlap: bool = False) -> bytes:
    """Compress data using CTR-SDK BLZ algorithm.

    The default reproduces Nintendo's compressor byte for byte (needed for the
    retail .code bit-match). `allow_overlap=True` produces smaller, equally valid
    output; use it when repacking data files that only need to fit their slot.
    """
    if len(data) <= 8:
        raise ValueError("Input data too small to compress")
    lib = _get_native_lib()
    if lib:
        buf = ctypes.create_string_buffer(len(data) + 16)
        n = lib.blz_compress_ex(data, len(data), buf, len(data) + 16, 1 if allow_overlap else 0)
        if n > 0:
            return buf.raw[:n]
        elif n == 0:
            raise ValueError("Data could not be compressed")
    res = py_compress(data)
    if res is None:
        raise ValueError("Data could not be compressed")
    return res


def main():
    parser = argparse.ArgumentParser(description="CTR-SDK BLZ compression / decompression tool")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-d", "--decompress", action="store_true", help="Decompress input file")
    group.add_argument("-c", "--compress", action="store_true", help="Compress input file")
    parser.add_argument("input", help="Input file path")
    parser.add_argument("output", help="Output file path")
    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: input file '{args.input}' not found", file=sys.stderr)
        sys.exit(1)

    try:
        with open(args.input, "rb") as f:
            in_data = f.read()

        if args.decompress:
            out_data = decompress(in_data)
        else:
            out_data = compress(in_data)

        os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
        with open(args.output, "wb") as f:
            f.write(out_data)

        print(f"Successfully processed {args.input} -> {args.output} ({len(in_data)} -> {len(out_data)} bytes)")
        sys.exit(0)
    except Exception as e:
        print(f"Error processing BLZ: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
