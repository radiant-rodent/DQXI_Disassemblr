"""Tier 2: Boundary 2 - Baseline Hash Validation Boundary & Error Tests.
Tests invalid hex string lengths, non-hex characters, 1-byte mismatch detection, empty input hash, and missing hash files.
"""

import hashlib
import re
import unittest
from tests.common import EXPECTED_HASHES, TOOLS_DIR, run_python_tool


class TestBoundary02HashValidation(unittest.TestCase):
    """Boundary & Error Handling: Hash Validation."""

    def test_corrupted_hash_length_rejected(self):
        """Verify that hashes with lengths other than 64 characters are detected as invalid."""
        too_short = "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24"  # 62 chars
        too_long = (
            "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d800"  # 66 chars
        )
        pattern = re.compile(r"^[0-9a-f]{64}$")
        self.assertIsNone(pattern.match(too_short))
        self.assertIsNone(pattern.match(too_long))

    def test_non_hex_characters_in_hash_rejected(self):
        """Verify that hashes containing non-hexadecimal characters are detected as invalid."""
        invalid_hex = (
            "zfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8"
        )
        pattern = re.compile(r"^[0-9a-f]{64}$")
        self.assertIsNone(pattern.match(invalid_hex))

    def test_single_byte_mutation_detection(self):
        """Verify that a single-byte flip anywhere in a block causes an entirely distinct SHA-256."""
        block = bytearray(b"\x00" * 1024)
        hash_original = hashlib.sha256(block).hexdigest()

        # Flip 1 bit in byte 512
        block[512] ^= 0x01
        hash_mutated = hashlib.sha256(block).hexdigest()

        self.assertNotEqual(hash_original, hash_mutated)

    def test_empty_input_hash_constant(self):
        """Verify SHA-256 digest of 0 bytes matches standard cryptographic constant."""
        empty_hash = hashlib.sha256(b"").hexdigest()
        expected_empty_hash = (
            "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
        )
        self.assertEqual(empty_hash, expected_empty_hash)

    def test_verify_tool_nonexistent_manifest_error(self):
        """Verify tools/verify.py handles nonexistent manifest or files gracefully with non-zero exit."""
        if not (TOOLS_DIR / "verify.py").is_file():
            self.skipTest("tools/verify.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "verify.py", ["--manifest", "C:/nonexistent/hashes.sha256"]
        )
        self.assertNotEqual(code, 0, "Verification of missing manifest must return non-zero code")


if __name__ == "__main__":
    unittest.main()
