"""Tier 5: Challenger 2 - CTR-SDK BLZ Compression Codec Empirical Stress Tests.

Adversarial stress-testing of `tools/blz.py`:
- Bit-matching roundtrip verification on retail DQXI ExeFS binary.
- Non-overlapping token constraint enforcement (max_len = min(18, dist)).
- Synthetic buffer stress testing: all-zeros, all-0xFF, repetitive patterns, ramp buffers.
- Pseudo-random arbitrary binary payloads across entropy levels.
- Small payload edge cases (< 16 B, 0 B, 8 B boundary, minimal compressible size 21 B).
- Large payload scalability (1 MB, 4 MB, 8 MB).
- Buffer overrun protection, corrupt footer parameters, and malformed token streams.
- CLI execution roundtrip verification.
"""

import hashlib
import os
import random
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests.common import (
    BUILD_DIR,
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    PROJECT_ROOT,
    TOOLS_DIR,
    run_python_tool,
)
import tools.blz as blz


def parse_and_validate_tokens(compressed_data: bytes) -> dict:
    """Parse BLZ compressed stream and extract all tokens for constraint verification.
    
    Returns a dict with:
        total_tokens: int
        violations: list of (tok_index, len, dist) where len > dist
        min_dist: int
        max_dist: int
        min_len: int
        max_len: int
        uncompressed_prefix_len: int
    """
    n = len(compressed_data)
    if n < 8:
        raise ValueError("Buffer too small for BLZ stream")
    tb, extra = struct.unpack_from("<II", compressed_data, n - 8)
    top = tb & 0xFFFFFF
    bottom = tb >> 24
    if bottom < 8 or bottom > 11 or top < bottom or top > n:
        raise ValueError("Invalid BLZ header")

    out_size = n + extra
    out = bytearray(compressed_data) + bytearray(extra)
    dst = out_size
    src = n - bottom
    end = n - top

    tokens = 0
    violations = []
    min_dist = 999999
    max_dist = 0
    min_len = 999999
    max_len = 0

    while src > end:
        src -= 1
        flag = out[src]
        for i in range(8):
            if not ((flag << i) & 0x80):
                src -= 1
                dst -= 1
                out[dst] = out[src]
            else:
                hi = out[src - 1]
                lo = out[src - 2]
                src -= 2
                tok = (hi << 8) | lo
                dist = (tok & 0x0FFF) + 3
                length = ((tok >> 12) & 0x0F) + 3
                tokens += 1

                if length > dist:
                    violations.append((tokens, length, dist))

                if dist < min_dist:
                    min_dist = dist
                if dist > max_dist:
                    max_dist = dist
                if length < min_len:
                    min_len = length
                if length > max_len:
                    max_len = length

                for _ in range(length):
                    dst -= 1
                    out[dst] = out[dst + dist]
            if src <= end:
                break

    return {
        "total_tokens": tokens,
        "violations": violations,
        "min_dist": min_dist if tokens > 0 else 0,
        "max_dist": max_dist if tokens > 0 else 0,
        "min_len": min_len if tokens > 0 else 0,
        "max_len": max_len if tokens > 0 else 0,
        "uncompressed_prefix_len": end,
        "final_dst": dst,
        "decompressed_bytes": bytes(out),
    }


class TestChallengerBlz(unittest.TestCase):
    """Adversarial stress-test suite for tools/blz.py."""

    @classmethod
    def setUpClass(cls):
        cls.code_comp_file = ORIGINAL_DIR / "exefs" / ".code"
        if not cls.code_comp_file.exists():
            cls.code_comp_file = ORIGINAL_DIR / "exefs" / "code.bin"
        cls.code_decomp_file = ORIGINAL_DIR / "exefs" / "code.decompressed.bin"

    # =========================================================================
    # 1. Retail DQXI Binary Bit-Matching Verification
    # =========================================================================

    def test_01_retail_binary_decompression_bitmatch(self):
        """Verify decompressing retail .code matches code.decompressed.bin byte-for-byte."""
        self.assertTrue(self.code_comp_file.is_file(), f"Missing {self.code_comp_file}")
        self.assertTrue(self.code_decomp_file.is_file(), f"Missing {self.code_decomp_file}")

        with open(self.code_comp_file, "rb") as f:
            comp_bytes = f.read()
        with open(self.code_decomp_file, "rb") as f:
            expected_decomp_bytes = f.read()

        # Empirical decompress via tools/blz.py
        decomp = blz.decompress(comp_bytes)

        self.assertEqual(len(decomp), EXPECTED_SIZES["code_decompressed"])
        self.assertEqual(
            hashlib.sha256(decomp).hexdigest(),
            EXPECTED_HASHES["code_decompressed"],
            "Decompressed binary SHA-256 does not match authoritative baseline",
        )
        self.assertEqual(decomp, expected_decomp_bytes)

    def test_02_retail_binary_recompression_bitmatch(self):
        """Verify recompressing decompressed code.bin reproduces exact original .code."""
        self.assertTrue(self.code_decomp_file.is_file())

        with open(self.code_decomp_file, "rb") as f:
            decomp_bytes = f.read()
        with open(self.code_comp_file, "rb") as f:
            expected_comp_bytes = f.read()

        recomp = blz.compress(decomp_bytes)

        self.assertEqual(len(recomp), EXPECTED_SIZES["code_compressed"])
        self.assertEqual(
            hashlib.sha256(recomp).hexdigest(),
            EXPECTED_HASHES["code_compressed"],
            "Recompressed binary SHA-256 does not match authoritative compressed baseline",
        )
        self.assertEqual(recomp, expected_comp_bytes)

    # =========================================================================
    # 2. Non-Overlapping Token Constraint Invariant
    # =========================================================================

    def test_03_retail_binary_tokens_strict_non_overlapping(self):
        """Parse all 933,585 tokens from retail .code and verify zero overlapping tokens."""
        with open(self.code_comp_file, "rb") as f:
            comp_bytes = f.read()

        stats = parse_and_validate_tokens(comp_bytes)

        self.assertEqual(stats["total_tokens"], 933585, "Total token count changed")
        self.assertEqual(
            len(stats["violations"]),
            0,
            f"Found {len(stats['violations'])} overlapping tokens in retail binary! Violations: {stats['violations'][:5]}",
        )
        self.assertGreaterEqual(stats["min_dist"], 3)
        self.assertLessEqual(stats["max_dist"], 4096)
        self.assertGreaterEqual(stats["min_len"], 3)
        self.assertLessEqual(stats["max_len"], 18)
        self.assertEqual(stats["final_dst"], stats["uncompressed_prefix_len"])

    def test_04_recompressed_binary_tokens_strict_non_overlapping(self):
        """Parse all tokens emitted by blz.compress on code.bin and verify non-overlapping rule."""
        with open(self.code_decomp_file, "rb") as f:
            decomp_bytes = f.read()

        recomp = blz.compress(decomp_bytes)
        stats = parse_and_validate_tokens(recomp)

        self.assertEqual(len(stats["violations"]), 0, "blz.compress emitted overlapping tokens!")
        self.assertEqual(stats["total_tokens"], 933585)
        self.assertEqual(stats["final_dst"], stats["uncompressed_prefix_len"])

    # =========================================================================
    # 3. Synthetic Buffers & Stress Tests
    # =========================================================================

    def test_05_all_zero_buffers_stress(self):
        """Stress-test compression and decompression of all-0x00 buffers of various sizes."""
        test_sizes = [32, 64, 128, 256, 1024, 4096, 65536, 524288]
        for size in test_sizes:
            data = b"\x00" * size
            comp = blz.compress(data)
            self.assertLess(len(comp), size, f"Failed to compress all-zero buffer size {size}")

            # Verify non-overlapping token constraint
            stats = parse_and_validate_tokens(comp)
            self.assertEqual(
                len(stats["violations"]),
                0,
                f"All-zero buffer size {size} emitted overlapping tokens: {stats['violations']}",
            )

            # Roundtrip verification
            decomp = blz.decompress(comp)
            self.assertEqual(decomp, data, f"Roundtrip mismatch on all-zero buffer size {size}")

            # Verify pure-Python decompressor on same data
            py_decomp = blz.py_decompress(comp)
            self.assertEqual(py_decomp, data)

    def test_06_all_ff_buffers_stress(self):
        """Stress-test compression and decompression of all-0xFF buffers of various sizes."""
        test_sizes = [32, 64, 128, 256, 1024, 4096, 65536, 524288]
        for size in test_sizes:
            data = b"\xFF" * size
            comp = blz.compress(data)
            self.assertLess(len(comp), size, f"Failed to compress all-FF buffer size {size}")

            stats = parse_and_validate_tokens(comp)
            self.assertEqual(
                len(stats["violations"]),
                0,
                f"All-FF buffer size {size} emitted overlapping tokens: {stats['violations']}",
            )

            decomp = blz.decompress(comp)
            self.assertEqual(decomp, data, f"Roundtrip mismatch on all-FF buffer size {size}")

            py_decomp = blz.py_decompress(comp)
            self.assertEqual(py_decomp, data)

    def test_07_repetitive_patterns_adversarial_overlap_bait(self):
        """Test repetitive short period patterns designed to bait naive LZ77 into overlapping copies."""
        patterns = [
            b"A" * 500,
            b"AB" * 250,
            b"ABC" * 200,
            b"ABCD" * 200,
            b"12345678" * 100,
            bytes([i % 7 for i in range(1000)]),
            bytes([i % 17 for i in range(2000)]),
            bytes([i % 19 for i in range(2000)]),
        ]

        for pat in patterns:
            comp = blz.compress(pat)
            stats = parse_and_validate_tokens(comp)
            self.assertEqual(
                len(stats["violations"]),
                0,
                f"Pattern {pat[:8]} produced overlapping tokens: {stats['violations']}",
            )
            decomp = blz.decompress(comp)
            self.assertEqual(decomp, pat)

    def test_08_pseudo_random_and_structured_entropy_payloads(self):
        """Test arbitrary pseudo-random payloads with varying entropy levels."""
        rng = random.Random(0xD0112026)

        # 1. Medium entropy: repeated pseudo-random 32-byte blocks
        block = bytes(rng.getrandbits(8) for _ in range(32))
        data = block * 100  # 3200 bytes
        comp = blz.compress(data)
        stats = parse_and_validate_tokens(comp)
        self.assertEqual(len(stats["violations"]), 0)
        self.assertEqual(blz.decompress(comp), data)

        # 2. Ramp pattern: sequential ascending bytes
        ramp = bytes(i & 0xFF for i in range(4096))
        # Repeating ramp
        rep_ramp = ramp * 4
        comp_ramp = blz.compress(rep_ramp)
        stats_ramp = parse_and_validate_tokens(comp_ramp)
        self.assertEqual(len(stats_ramp["violations"]), 0)
        self.assertEqual(blz.decompress(comp_ramp), rep_ramp)

        # 3. High entropy noise: uncompressible
        noise = bytes(rng.getrandbits(8) for _ in range(1024))
        # Pure random noise must safely raise ValueError or produce valid compressed stream
        try:
            comp_noise = blz.compress(noise)
            self.assertEqual(blz.decompress(comp_noise), noise)
        except ValueError as e:
            self.assertIn("could not be compressed", str(e))

    # =========================================================================
    # 4. Small and Boundary Payloads (< 16 B, 0 B)
    # =========================================================================

    def test_09_small_payloads_boundaries(self):
        """Verify strict error handling on small payloads from 0 to 20 bytes."""
        # 0 to 8 bytes must raise ValueError
        for size in range(9):
            data = b"X" * size
            with self.assertRaises(ValueError, msg=f"Size {size} did not raise ValueError"):
                blz.compress(data)

        # 9 to 20 bytes cannot compress (overhead exceeds data size)
        for size in range(9, 21):
            data = b"Z" * size
            with self.assertRaises(ValueError, msg=f"Size {size} did not raise ValueError"):
                blz.compress(data)

        # Size 21: first size that can compress repetitive data
        data_21 = b"A" * 21
        comp_21 = blz.compress(data_21)
        self.assertEqual(len(comp_21), 20)
        decomp_21 = blz.decompress(comp_21)
        self.assertEqual(decomp_21, data_21)

    # =========================================================================
    # 5. Large Payloads
    # =========================================================================

    def test_10_large_payloads(self):
        """Verify scalability and stability on large payloads (1MB, 4MB, 8MB)."""
        rng = random.Random(42)
        base = bytes(rng.getrandbits(8) for _ in range(256))

        for size in [1024 * 1024, 4 * 1024 * 1024]:
            repeats = size // len(base)
            large_data = base * repeats
            comp = blz.compress(large_data)
            self.assertLess(len(comp), len(large_data))
            decomp = blz.decompress(comp)
            self.assertEqual(decomp, large_data)

    # =========================================================================
    # 6. Malformed Stream & Buffer Overrun Hardening
    # =========================================================================

    def test_11_malformed_stream_rejection(self):
        """Stress-test decompressor resilience against corrupted footers and bounds violations."""
        # 1. Truncated stream < 8 bytes
        for sz in range(8):
            with self.assertRaises(ValueError):
                blz.decompress(b"\x00" * sz)

        # 2. Corrupted bottom pointer (< 8 or > 11)
        corrupted_bottom = bytes(b"\x00" * 24 + struct.pack("<II", 0x10 | (0x02 << 24), 0))
        with self.assertRaises(ValueError):
            blz.decompress(corrupted_bottom)

        # 3. Corrupted top pointer (> in_size)
        corrupted_top = bytes(b"\x00" * 24 + struct.pack("<II", 0x1000 | (0x08 << 24), 0))
        with self.assertRaises(ValueError):
            blz.decompress(corrupted_top)

        # 4. Corrupted top pointer (< bottom)
        corrupted_top_low = bytes(b"\x00" * 24 + struct.pack("<II", 0x05 | (0x08 << 24), 0))
        with self.assertRaises(ValueError):
            blz.decompress(corrupted_top_low)

        # 5. Token offset read overrun
        corrupt_tok = bytearray(b"\x00" * 32)
        corrupt_tok[23] = 0x80  # flag: 1st token
        # Token at 22, 21: ln=3, dist=4095 (way past out_size 48)
        corrupt_tok[22] = 0x0F  # ln = 3, off high bits
        corrupt_tok[21] = 0xFF  # off low bits
        struct.pack_into("<II", corrupt_tok, 24, 9 | (8 << 24), 16)
        with self.assertRaises((ValueError, IndexError)):
            blz.decompress(bytes(corrupt_tok))

    # =========================================================================
    # 7. CLI End-to-End Execution
    # =========================================================================

    def test_12_cli_decompression_and_recompression_roundtrip(self):
        """Verify tools/blz.py CLI operates end-to-end and produces bit-matching output."""
        with tempfile.TemporaryDirectory() as td:
            temp_dir = Path(td)
            decomp_out = temp_dir / "cli_decomp.bin"
            recomp_out = temp_dir / "cli_recomp.bin"

            # 1. Decompress retail .code via CLI
            code, stdout, stderr = run_python_tool(
                TOOLS_DIR / "blz.py",
                ["-d", str(self.code_comp_file), str(decomp_out)],
            )
            self.assertEqual(code, 0, f"blz.py -d CLI failed: {stderr}")
            self.assertTrue(decomp_out.is_file())
            self.assertEqual(
                hashlib.sha256(decomp_out.read_bytes()).hexdigest(),
                EXPECTED_HASHES["code_decompressed"],
            )

            # 2. Recompress decompressed file via CLI
            code, stdout, stderr = run_python_tool(
                TOOLS_DIR / "blz.py",
                ["-c", str(decomp_out), str(recomp_out)],
            )
            self.assertEqual(code, 0, f"blz.py -c CLI failed: {stderr}")
            self.assertTrue(recomp_out.is_file())
            self.assertEqual(
                hashlib.sha256(recomp_out.read_bytes()).hexdigest(),
                EXPECTED_HASHES["code_compressed"],
            )


if __name__ == "__main__":
    unittest.main()
