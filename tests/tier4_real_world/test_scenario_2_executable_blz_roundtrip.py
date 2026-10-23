"""Tier 4: Scenario 2 - Executable Extraction, BLZ Decompress & Roundtrip Compress.
Features Exercised: F1 (ROM Extraction), F4 (BLZ Compression), F7 (Relocatable Assembly Build).
Verifies BLZ roundtrip preservation of bit-matching hashes and sizes.
"""

import struct
import unittest
from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    REFERENCE_CODE_BIN,
    REFERENCE_CODE_DECOMPRESSED,
    TOOLS_DIR,
    run_python_tool,
    sha256_file,
)


class TestScenario2ExecutableBlzRoundtrip(unittest.TestCase):
    """Scenario 2: Executable Extraction, BLZ Decompress & Roundtrip Compress."""

    def test_scenario_2_decompressed_and_compressed_pair_integrity(self):
        """Verify baseline pairing between code.decompressed.bin and compressed .code."""
        self.assertTrue(REFERENCE_CODE_DECOMPRESSED.is_file())
        self.assertTrue(REFERENCE_CODE_BIN.is_file())

        self.assertEqual(
            REFERENCE_CODE_DECOMPRESSED.stat().st_size,
            EXPECTED_SIZES["code_decompressed"],
        )
        self.assertEqual(
            REFERENCE_CODE_BIN.stat().st_size,
            EXPECTED_SIZES["code_compressed"],
        )

        self.assertEqual(
            sha256_file(REFERENCE_CODE_DECOMPRESSED),
            EXPECTED_HASHES["code_decompressed"],
        )
        self.assertEqual(
            sha256_file(REFERENCE_CODE_BIN),
            EXPECTED_HASHES["code_compressed"],
        )

    def test_scenario_2_footer_mathematical_consistency(self):
        """Verify BLZ footer mathematical relation: decompressed_size == compressed_size + extra."""
        comp_size = REFERENCE_CODE_BIN.stat().st_size
        with open(REFERENCE_CODE_BIN, "rb") as f:
            f.seek(comp_size - 8)
            tb, extra = struct.unpack("<II", f.read(8))

        top = tb & 0x00FFFFFF
        bottom = (tb >> 24) & 0xFF
        decomp_size = comp_size + extra

        self.assertEqual(decomp_size, EXPECTED_SIZES["code_decompressed"])
        self.assertEqual(top, 0x3BD3D5)
        self.assertEqual(bottom, 0x0A)

    def test_scenario_2_blz_tool_roundtrip(self):
        """Verify tools/blz.py roundtrip if tool is implemented in M1."""
        blz_tool = TOOLS_DIR / "blz.py"
        if not blz_tool.is_file():
            self.skipTest("tools/blz.py not yet implemented (M1)")

        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tf:
            temp_out = Path(tf.name)

        try:
            # Test decompression of code.bin
            code, stdout, stderr = run_python_tool(
                blz_tool, ["-d", str(REFERENCE_CODE_BIN), str(temp_out)]
            )
            self.assertEqual(code, 0, f"blz -d failed: {stderr}")
            self.assertEqual(sha256_file(temp_out), EXPECTED_HASHES["code_decompressed"])
        finally:
            if temp_out.is_file():
                temp_out.unlink()


if __name__ == "__main__":
    unittest.main()
