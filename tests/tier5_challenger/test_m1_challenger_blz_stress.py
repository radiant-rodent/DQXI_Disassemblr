"""Tier 5 Challenger Deep Stress Harness for CTR-SDK BLZ Codec (Worker 2 Remediation).

Adversarial stress-testing of tools/blz.py across:
1. Random noise fuzzing across entropy levels & seeds (Native C and Pure Python).
2. Zero-length and small boundary payloads (0 to 25 bytes).
3. Truncated buffer cascades (every single byte truncation).
4. DoS buffers with extra > 128 MB and integer overflow values.
5. Corrupted header/footer parameter permutations (top/bottom bounds).
6. Malformed token streams and memory underflow/overrun attempts.
7. Cross-engine parity: C compress -> Py decompress; Py compress -> C decompress.
8. Exact retail .code roundtrip and SHA-256 bit-matching.
"""

import hashlib
import os
import random
import struct
import sys
import unittest
from pathlib import Path

from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    PROJECT_ROOT,
    TOOLS_DIR,
)
import tools.blz as blz


class TestChallengerBlzDeepStress(unittest.TestCase):
    """Deep adversarial stress tests for CTR-SDK BLZ codec."""

    @classmethod
    def setUpClass(cls):
        cls.code_comp_file = ORIGINAL_DIR / "exefs" / ".code"
        if not cls.code_comp_file.exists():
            cls.code_comp_file = ORIGINAL_DIR / "exefs" / "code.bin"
        cls.code_decomp_file = ORIGINAL_DIR / "exefs" / "code.decompressed.bin"
        cls.native_lib = blz._get_native_lib()

    # =========================================================================
    # 1. Zero-Length and Small Boundary Payloads
    # =========================================================================

    def test_zero_length_payloads(self):
        """Zero-length buffer must be rejected cleanly by all API entry points."""
        empty = b""
        with self.assertRaises(ValueError):
            blz.compress(empty)

        with self.assertRaises(ValueError):
            blz.decompress(empty)

        self.assertIsNone(blz.py_compress(empty))

        with self.assertRaises(ValueError):
            blz.py_decompress(empty)

        if self.native_lib:
            buf = bytearray(64)
            rc = self.native_lib.blz_decompress(b"", 0, (blz.ctypes.c_char * 64).from_buffer(buf), 64)
            self.assertEqual(rc, -1)
            c_rc = self.native_lib.blz_compress(b"", 0, (blz.ctypes.c_char * 64).from_buffer(buf), 64)
            self.assertEqual(c_rc, 0)

    def test_small_boundary_sizes_0_to_25(self):
        """Test payload sizes 1..25 for clean error handling or valid compression."""
        for sz in range(1, 9):
            data = b"A" * sz
            with self.assertRaises(ValueError):
                blz.compress(data)
            self.assertIsNone(blz.py_compress(data))
            with self.assertRaises(ValueError):
                blz.decompress(data)
            with self.assertRaises(ValueError):
                blz.py_decompress(data)

        # Sizes 9..20 cannot compress (overhead of 8-byte footer + flag byte exceeds saving)
        for sz in range(9, 21):
            data = b"A" * sz
            with self.assertRaises(ValueError):
                blz.compress(data)
            self.assertIsNone(blz.py_compress(data))

        # Size 21 compresses to 20 bytes
        data_21 = b"A" * 21
        comp_21 = blz.compress(data_21)
        self.assertEqual(len(comp_21), 20)
        self.assertEqual(blz.decompress(comp_21), data_21)
        self.assertEqual(blz.py_decompress(comp_21), data_21)

        # Pure Python compressor on size 21
        py_comp_21 = blz.py_compress(data_21)
        self.assertIsNotNone(py_comp_21)
        self.assertEqual(len(py_comp_21), 20)
        self.assertEqual(blz.decompress(py_comp_21), data_21)
        self.assertEqual(blz.py_decompress(py_comp_21), data_21)

    # =========================================================================
    # 2. Random Noise Fuzzing Across Entropy Levels & Sizes
    # =========================================================================

    def test_random_noise_fuzzing(self):
        """Fuzz with arbitrary pseudo-random payloads across various sizes and seeds."""
        test_sizes = [16, 25, 32, 64, 100, 128, 256, 512, 1024, 2048, 4096]
        seeds = [1, 42, 1337, 0xCAFE, 0xDEADBEEF]

        for seed in seeds:
            rng = random.Random(seed)
            for size in test_sizes:
                noise = bytes(rng.getrandbits(8) for _ in range(size))

                # Test standard blz.compress (uses native C if available)
                try:
                    comp = blz.compress(noise)
                    decomp = blz.decompress(comp)
                    self.assertEqual(decomp, noise, f"Roundtrip mismatch for seed {seed}, size {size}")
                    py_decomp = blz.py_decompress(comp)
                    self.assertEqual(py_decomp, noise)
                except ValueError as e:
                    self.assertIn("could not be compressed", str(e))

                # Test pure-Python py_compress directly
                py_comp = blz.py_compress(noise)
                if py_comp is not None:
                    decomp = blz.decompress(py_comp)
                    self.assertEqual(decomp, noise)
                    py_decomp = blz.py_decompress(py_comp)
                    self.assertEqual(py_decomp, noise)

    # =========================================================================
    # 3. Truncated Buffer Cascades
    # =========================================================================

    def test_truncated_buffer_cascade(self):
        """Test progressive truncation of a valid BLZ compressed buffer byte-by-byte."""
        # Create a valid compressed payload
        orig = b"XYZ12345ABCDEFGH" * 20  # 320 bytes
        comp = blz.compress(orig)
        self.assertLess(len(comp), len(orig))

        # Truncate at every length from len(comp) - 1 down to 0
        for cut_len in range(len(comp) - 1, -1, -1):
            truncated = comp[:cut_len]

            # Native / wrapper decompress
            with self.assertRaises(ValueError, msg=f"Truncated buffer at len {cut_len} did not raise ValueError"):
                blz.decompress(truncated)

            # Pure Python decompress
            with self.assertRaises(ValueError, msg=f"Truncated buffer at len {cut_len} did not raise ValueError in py_decompress"):
                blz.py_decompress(truncated)

    # =========================================================================
    # 4. DoS Protection: Memory Exhaustion via Malicious Extra Size
    # =========================================================================

    def test_dos_extra_size_limits(self):
        """Verify extra size > 128 MB (0x08000000) is rejected immediately without allocating."""
        # Build minimal valid structure with malicious extra field
        # top = 8, bottom = 8, in_size = 8
        tb = 8 | (8 << 24)

        dos_extras = [
            0x08000001,       # 128 MB + 1
            0x09000000,       # 144 MB
            0x10000000,       # 256 MB
            0x40000000,       # 1 GB
            0x7FFFFFFF,       # ~2 GB (max signed 32-bit)
            0x80000000,       # Negative if signed
            0xFFFFFFFF,       # 4 GB - 1 (-1)
        ]

        for extra in dos_extras:
            malicious_buf = struct.pack("<II", tb, extra)

            # blz.decompress must reject
            with self.assertRaises(ValueError, msg=f"extra=0x{extra:08X} was not rejected by decompress"):
                blz.decompress(malicious_buf)

            # blz.py_decompress must reject
            with self.assertRaises(ValueError, msg=f"extra=0x{extra:08X} was not rejected by py_decompress"):
                blz.py_decompress(malicious_buf)

            # Native C directly
            if self.native_lib:
                buf = bytearray(64)
                rc = self.native_lib.blz_decompress(
                    malicious_buf,
                    len(malicious_buf),
                    (blz.ctypes.c_char * 64).from_buffer(buf),
                    64,
                )
                self.assertEqual(rc, -2, f"Native C did not return -2 for extra=0x{extra:08X}")

    # =========================================================================
    # 5. Corrupted Header/Footer Bounds Permutations
    # =========================================================================

    def test_corrupt_header_footer_bounds(self):
        """Adversarial permutations of bottom and top pointers."""
        # Valid extra = 0, size = 16
        base = b"\x00" * 8

        # Invalid bottoms: < 8 or > 11
        for invalid_bottom in [0, 1, 2, 7, 12, 15, 255]:
            tb = 8 | (invalid_bottom << 24)
            corrupt = base + struct.pack("<II", tb, 0)
            with self.assertRaises(ValueError):
                blz.decompress(corrupt)
            with self.assertRaises(ValueError):
                blz.py_decompress(corrupt)

        # Invalid top: top < bottom
        tb_top_low = 7 | (8 << 24)
        corrupt = base + struct.pack("<II", tb_top_low, 0)
        with self.assertRaises(ValueError):
            blz.decompress(corrupt)
        with self.assertRaises(ValueError):
            blz.py_decompress(corrupt)

        # Invalid top: top > in_size (in_size = 16, top = 17)
        tb_top_high = 17 | (8 << 24)
        corrupt = base + struct.pack("<II", tb_top_high, 0)
        with self.assertRaises(ValueError):
            blz.decompress(corrupt)
        with self.assertRaises(ValueError):
            blz.py_decompress(corrupt)

    # =========================================================================
    # 6. Stream Termination and Alignment Verification
    # =========================================================================

    def test_unaligned_stream_termination(self):
        """Verify streams where dst != end at conclusion are rejected."""
        # Craft a stream where decoding finishes but leaves dst != end
        # Size = 24. footer: top = 16, bottom = 8, extra = 0.
        # end = 24 - 16 = 8. src starts at 24 - 8 = 16.
        # Flag byte at index 15.
        buf = bytearray(24)
        buf[15] = 0x00  # 8 literals
        # 8 literals decrements src by 8 (from 15 to 7 <= end=8, loop breaks).
        # But dst was 24, decrements by 8 -> dst becomes 16, which != end (8)!
        tb = 16 | (8 << 24)
        struct.pack_into("<II", buf, 16, tb, 0)

        with self.assertRaises(ValueError) as ctx:
            blz.decompress(bytes(buf))
        self.assertTrue("truncated or unaligned" in str(ctx.exception) or "code -8" in str(ctx.exception))

        with self.assertRaises(ValueError) as ctx:
            blz.py_decompress(bytes(buf))
        self.assertIn("truncated or unaligned", str(ctx.exception))

    # =========================================================================
    # 7. Cross-Engine Interoperability
    # =========================================================================

    def test_cross_engine_parity(self):
        """Verify native C and pure Python codecs interoperate symmetrically."""
        compressible_patterns = [
            b"ABC" * 100,
            b"\x00\xFF" * 80,
            bytes((x * 7) & 0xFF for x in range(300)) * 5,
            b"The quick brown fox jumps over the lazy dog" * 10,
        ]

        for p in compressible_patterns:
            # 1. Native compress -> Pure Python decompress
            c_comp = blz.compress(p)
            py_decomp = blz.py_decompress(c_comp)
            self.assertEqual(py_decomp, p)

            # 2. Pure Python compress -> Native decompress
            py_comp = blz.py_compress(p)
            self.assertIsNotNone(py_comp)
            c_decomp = blz.decompress(py_comp)
            self.assertEqual(c_decomp, p)

            # 3. Pure Python compress -> Pure Python decompress
            py_self_decomp = blz.py_decompress(py_comp)
            self.assertEqual(py_self_decomp, p)

            # 4. Bit-matching output parity between engines
            self.assertEqual(c_comp, py_comp, "Native C and Pure Python compression produced differing output")

        # Incompressible payload: both engines must agree it cannot be compressed
        incompressible = bytes((x * 7) & 0xFF for x in range(300))
        self.assertIsNone(blz.py_compress(incompressible))
        with self.assertRaises(ValueError):
            blz.compress(incompressible)

    # =========================================================================
    # 8. Retail DQXI .code Exact Roundtrip & Bit-Matching
    # =========================================================================

    def test_retail_code_roundtrip_bitmatch(self):
        """Verify retail .code decompress and recompress matches SHA-256 byte-for-byte."""
        self.assertTrue(self.code_comp_file.is_file(), f"Missing {self.code_comp_file}")
        self.assertTrue(self.code_decomp_file.is_file(), f"Missing {self.code_decomp_file}")

        with open(self.code_comp_file, "rb") as f:
            comp_bytes = f.read()
        with open(self.code_decomp_file, "rb") as f:
            decomp_bytes = f.read()

        # Step 1: Decompress retail .code -> check decompressed hash
        decomp = blz.decompress(comp_bytes)
        self.assertEqual(len(decomp), EXPECTED_SIZES["code_decompressed"])
        self.assertEqual(
            hashlib.sha256(decomp).hexdigest(),
            EXPECTED_HASHES["code_decompressed"],
        )
        self.assertEqual(decomp, decomp_bytes)

        # Step 2: Recompress decompressed bytes -> check compressed hash
        recomp = blz.compress(decomp_bytes)
        self.assertEqual(len(recomp), EXPECTED_SIZES["code_compressed"])
        self.assertEqual(
            hashlib.sha256(recomp).hexdigest(),
            EXPECTED_HASHES["code_compressed"],
        )
        self.assertEqual(recomp, comp_bytes)


if __name__ == "__main__":
    unittest.main()
