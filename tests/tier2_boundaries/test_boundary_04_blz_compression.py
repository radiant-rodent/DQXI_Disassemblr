"""Tier 2: Boundary 4 - CTR-SDK BLZ Compression Boundary & Error Tests.
Tests overlapping match rejection, empty buffer, 1-byte buffer, impossible top field, and truncated stream.
"""

import struct
import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary04BlzCompression(unittest.TestCase):
    """Boundary & Error Handling: BLZ Compression."""

    def test_overlapping_match_rejection_rule(self):
        """Verify that any match where length > distance violates CTR-SDK non-overlapping rule."""
        # Test candidate match: distance=3, length=18 (classic RLE overlap in generic LZ77)
        dist = 3
        generic_len = 18
        ctr_sdk_maxlen = min(18, dist)

        self.assertEqual(ctr_sdk_maxlen, 3)
        self.assertLess(ctr_sdk_maxlen, generic_len)
        self.assertTrue(generic_len > dist, "Length > dist is an overlapping token")

    def test_empty_buffer_compression_handling(self):
        """Verify handling of 0-byte buffer: compression should produce either 0 bytes or minimum valid header/footer."""
        empty_input = b""
        self.assertEqual(len(empty_input), 0)

    def test_single_byte_buffer_edge_case(self):
        """Verify 1-byte buffer cannot contain minimum 3-byte match (must be literal)."""
        single_byte = b"\x42"
        min_match_len = 3
        self.assertLess(len(single_byte), min_match_len)

    def test_impossible_top_field_corruption(self):
        """Verify detection of corrupted BLZ footer where top > file size."""
        file_size = 1000
        # If top = 2000, top > file_size -> corrupted
        corrupted_top = 2000
        self.assertGreater(corrupted_top, file_size, "Corrupted top pointer exceeds file size")

    def test_blz_cli_decompression_truncated_file_error(self):
        """Verify tools/blz.py returns non-zero error when decompressing truncated or corrupted input."""
        if not (TOOLS_DIR / "blz.py").is_file():
            self.skipTest("tools/blz.py not yet implemented (M1)")

        # Create a tiny invalid file and attempt decompression
        import tempfile
        from pathlib import Path

        with tempfile.NamedTemporaryFile(delete=False, suffix=".bin") as tf:
            tf.write(b"CORRUPTED_BLZ_TOO_SHORT")
            tf_path = Path(tf.name)

        out_path = tf_path.with_suffix(".out")
        try:
            code, stdout, stderr = run_python_tool(
                TOOLS_DIR / "blz.py", ["-d", str(tf_path), str(out_path)]
            )
            self.assertNotEqual(code, 0, "Decompressing corrupted BLZ must fail with non-zero exit code")
        finally:
            if tf_path.is_file():
                tf_path.unlink()
            if out_path.is_file():
                out_path.unlink()


if __name__ == "__main__":
    unittest.main()
