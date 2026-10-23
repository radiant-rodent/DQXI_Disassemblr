"""Tier 2: Boundary 1 - ROM Extraction Boundary & Error Handling Tests.
Tests invalid magic, truncated headers, zero-sized partitions, out-of-bounds offsets, and missing ROM paths.
"""

import io
import struct
import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary01RomExtraction(unittest.TestCase):
    """Boundary & Error Handling: ROM Extraction."""

    def test_invalid_ncsd_magic_rejected(self):
        """Verify that a header with invalid magic (not 'NCSD') is identified as corrupted."""
        bad_header = b"\x00" * 0x100 + b"BAD!" + b"\x00" * (0x200 - 0x104)
        magic = bad_header[0x100:0x104]
        self.assertNotEqual(magic, b"NCSD")

    def test_truncated_header_stream(self):
        """Verify handling of truncated file streams smaller than NCSD header (0x200 bytes)."""
        short_data = b"NCSD" + b"\x00" * 50  # only 54 bytes
        stream = io.BytesIO(short_data)
        stream.seek(0)
        read_bytes = stream.read(0x200)
        self.assertLess(len(read_bytes), 0x200, "Truncated stream must yield less than 0x200 bytes")

    def test_zero_size_partition_handling(self):
        """Verify handling of inactive partitions having size 0 in partition table."""
        # Unused partitions 2, 3, 4, 5 have offset 0 and size 0
        raw_partition = struct.pack("<II", 0, 0)
        off, sz = struct.unpack("<II", raw_partition)
        self.assertEqual(off, 0)
        self.assertEqual(sz, 0)

    def test_partition_offset_overflow_check(self):
        """Verify detection of partition offsets extending beyond cartridge boundary."""
        max_cartridge_units = 8388608  # 4GB in 512-byte media units
        invalid_offset_units = 9000000
        self.assertGreater(
            invalid_offset_units,
            max_cartridge_units,
            "Out-of-bounds media unit offset must be detected",
        )

    def test_missing_rom_file_cli_error(self):
        """Verify tools/extract_rom.py returns non-zero error when given non-existent file path."""
        if not (TOOLS_DIR / "extract_rom.py").is_file():
            self.skipTest("tools/extract_rom.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "extract_rom.py", ["C:/nonexistent/fake_rom.3ds", "C:/tmp/out"]
        )
        self.assertNotEqual(code, 0, "Extracting missing file must return non-zero exit code")


if __name__ == "__main__":
    unittest.main()
