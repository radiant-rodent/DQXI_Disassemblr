"""Tier 1: Feature 2 - Baseline Hash Validation Tests.
Verifies SHA-256 cryptographic hashes for executable code, containers, and hash format parsing.
"""

import re
import unittest
from tests.common import (
    EXPECTED_HASHES,
    ORIGINAL_DIR,
    REFERENCE_CODE_BIN,
    REFERENCE_CODE_DECOMPRESSED,
    TOOLS_DIR,
    run_python_tool,
    sha256_file,
)


class TestFeature02HashValidation(unittest.TestCase):
    """Feature 2: Baseline SHA-256 Hash Generation and Validation."""

    def test_authoritative_hashes_registry(self):
        """Verify baseline hash registry contains all required keys and valid 64-char hex strings."""
        required_keys = [
            "rom",
            "code_decompressed",
            "code_compressed",
            "romfs",
            "exheader",
            "logo",
            "plain",
            "banner",
            "icon",
        ]
        hex_pattern = re.compile(r"^[0-9a-f]{64}$")
        for key in required_keys:
            self.assertIn(key, EXPECTED_HASHES)
            h = EXPECTED_HASHES[key]
            self.assertTrue(
                hex_pattern.match(h), f"Hash for {key} is invalid hex: {h}"
            )

    def test_reference_code_decompressed_hash(self):
        """Verify uncompressed code.bin matches exact retail baseline SHA-256."""
        self.assertTrue(REFERENCE_CODE_DECOMPRESSED.is_file())
        actual_hash = sha256_file(REFERENCE_CODE_DECOMPRESSED)
        self.assertEqual(
            actual_hash,
            EXPECTED_HASHES["code_decompressed"],
            "Uncompressed code.bin SHA-256 mismatch",
        )

    def test_reference_code_compressed_hash(self):
        """Verify compressed code.bin (.code) matches exact retail baseline SHA-256."""
        self.assertTrue(REFERENCE_CODE_BIN.is_file())
        actual_hash = sha256_file(REFERENCE_CODE_BIN)
        self.assertEqual(
            actual_hash,
            EXPECTED_HASHES["code_compressed"],
            "Compressed code.bin (.code) SHA-256 mismatch",
        )

    def test_hashes_file_format_parser(self):
        """Verify parsing parser for standard sha256 checksum file format."""
        sample_manifest = (
            "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8  code.bin\n"
            "ea3d2c02780e7d7406137cc5099e2ccdf9da4a90f48f35f97d59f0a08c298a2f *.code\n"
        )
        parsed = {}
        for line in sample_manifest.strip().splitlines():
            parts = line.strip().split(maxsplit=1)
            self.assertEqual(len(parts), 2)
            h, name = parts[0], parts[1].lstrip("*").strip()
            parsed[name] = h

        self.assertEqual(
            parsed["code.bin"], EXPECTED_HASHES["code_decompressed"]
        )
        self.assertEqual(parsed[".code"], EXPECTED_HASHES["code_compressed"])

    def test_verify_tool_or_manifest(self):
        """Verify tools/verify.py if implemented, or original/hashes.sha256 if present."""
        if (TOOLS_DIR / "verify.py").is_file():
            code, stdout, stderr = run_python_tool(
                TOOLS_DIR / "verify.py", ["--help"]
            )
            self.assertEqual(code, 0, f"verify.py --help failed: {stderr}")
        elif (ORIGINAL_DIR / "hashes.sha256").is_file():
            # Verify that hashes.sha256 has entries
            content = (ORIGINAL_DIR / "hashes.sha256").read_text()
            self.assertIn(EXPECTED_HASHES["code_decompressed"], content)
        else:
            self.skipTest(
                "Neither tools/verify.py nor original/hashes.sha256 is present yet (M1)"
            )


if __name__ == "__main__":
    unittest.main()
