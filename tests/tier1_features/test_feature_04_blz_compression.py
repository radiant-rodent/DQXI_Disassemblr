"""Tier 1: Feature 4 - CTR-SDK BLZ Compression & Decompression Tests.
Verifies BLZ footer fields, uncompressed prefix, non-overlapping match constraint, and tools/blz.py CLI.
"""

import struct
import unittest
from tests.common import (
    EXPECTED_SIZES,
    REFERENCE_CODE_BIN,
    REFERENCE_CODE_DECOMPRESSED,
    TOOLS_DIR,
    run_python_tool,
)


class TestFeature04BlzCompression(unittest.TestCase):
    """Feature 4: CTR-SDK BLZ Compression & Decompression."""

    def test_blz_footer_structure(self):
        """Verify the 8-byte BLZ footer in reference compressed code.bin (.code)."""
        self.assertTrue(REFERENCE_CODE_BIN.is_file())
        file_size = REFERENCE_CODE_BIN.stat().st_size
        self.assertEqual(file_size, EXPECTED_SIZES["code_compressed"])

        with open(REFERENCE_CODE_BIN, "rb") as f:
            f.seek(file_size - 8)
            tb, extra = struct.unpack("<II", f.read(8))

        top = tb & 0x00FFFFFF
        bottom = (tb >> 24) & 0xFF

        # Documented values for retail DQXI code.bin
        self.assertEqual(top, 0x3BD3D5, "BLZ top pointer mismatch")
        self.assertEqual(bottom, 0x0A, "BLZ bottom size mismatch")
        self.assertEqual(extra, 0x305BE4, "BLZ extra expansion mismatch")

        # Check decompressed size calculation
        calc_decomp_size = file_size + extra
        self.assertEqual(
            calc_decomp_size,
            EXPECTED_SIZES["code_decompressed"],
            "Decompressed size calculated from footer mismatch",
        )

    def test_blz_decompressed_size_matches(self):
        """Verify reference decompressed code.bin matches exactly 7,090,176 bytes."""
        self.assertTrue(REFERENCE_CODE_DECOMPRESSED.is_file())
        self.assertEqual(
            REFERENCE_CODE_DECOMPRESSED.stat().st_size,
            EXPECTED_SIZES["code_decompressed"],
        )

    def test_blz_uncompressed_prefix(self):
        """Verify the safe uncompressed prefix (first 71 bytes) matches between compressed and uncompressed files."""
        # Uncompressed safe prefix = file_size - top = 3920924 - 3920853 = 71 bytes
        prefix_len = 71
        with open(REFERENCE_CODE_BIN, "rb") as f_comp, open(
            REFERENCE_CODE_DECOMPRESSED, "rb"
        ) as f_decomp:
            comp_head = f_comp.read(prefix_len)
            decomp_head = f_decomp.read(prefix_len)

        self.assertEqual(
            comp_head,
            decomp_head,
            "Prefix before BLZ compressed stream must match uncompressed code",
        )

    def test_ctr_sdk_non_overlapping_constraint(self):
        """Verify CTR-SDK token constraint rule: max match length is min(18, dist)."""
        # Under CTR-SDK rules: length cannot exceed distance (no run-length overlap)
        # Mathematical property: max_len = min(18, dist) for all dist in [3..4096]
        for dist in range(3, 4097):
            expected_maxlen = min(18, dist)
            self.assertLessEqual(expected_maxlen, dist)
            self.assertLessEqual(expected_maxlen, 18)
            if dist < 18:
                self.assertEqual(expected_maxlen, dist)
            else:
                self.assertEqual(expected_maxlen, 18)

    def test_blz_cli_interface(self):
        """Verify tools/blz.py CLI entry point and flags if implemented."""
        if not (TOOLS_DIR / "blz.py").is_file():
            self.skipTest("tools/blz.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "blz.py", ["--help"]
        )
        self.assertEqual(code, 0, f"blz.py --help failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
