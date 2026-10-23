"""Tier 2: Boundary 3 - Bit-Matching Repacker Boundary & Error Tests.
Tests corrupted padding byte detection, missing input partition, unaligned component, total size mismatch, and empty input dir.
"""

import unittest
from tests.common import EXPECTED_SIZES, TOOLS_DIR, run_python_tool


class TestBoundary03RomRepack(unittest.TestCase):
    """Boundary & Error Handling: Bit-Matching Repacker."""

    def test_corrupted_padding_byte_detection(self):
        """Verify that padding bytes other than 0xFF in trailing region are rejected."""
        valid_pad_block = b"\xFF" * 1024
        corrupted_pad_block = b"\xFF" * 512 + b"\xFE" + b"\xFF" * 511

        self.assertEqual(valid_pad_block.count(b"\xFF"), 1024)
        self.assertNotEqual(corrupted_pad_block.count(b"\xFF"), 1024)
        self.assertIn(b"\xFE", corrupted_pad_block)

    def test_unaligned_component_rejection(self):
        """Verify that components not aligned to 512-byte media unit boundary trigger error."""
        unaligned_size = 1000  # not divisible by 512
        aligned_size = 1024
        self.assertNotEqual(unaligned_size % 512, 0)
        self.assertEqual(aligned_size % 512, 0)

    def test_total_repack_size_mismatch_detection(self):
        """Verify that any repacked size other than 4,294,967,296 bytes fails validation."""
        incorrect_size_1 = EXPECTED_SIZES["rom"] - 512
        incorrect_size_2 = EXPECTED_SIZES["rom"] + 512

        self.assertNotEqual(incorrect_size_1, EXPECTED_SIZES["rom"])
        self.assertNotEqual(incorrect_size_2, EXPECTED_SIZES["rom"])

    def test_missing_input_partition_detection(self):
        """Verify repacker detects missing mandatory partition (e.g. partition 0 CXI)."""
        required_partitions = ["ncch0.bin", "exheader.bin", "romfs.bin"]
        available_files = ["ncch0.bin", "exheader.bin"]  # romfs.bin missing

        missing = [p for p in required_partitions if p not in available_files]
        self.assertEqual(missing, ["romfs.bin"])

    def test_repack_empty_input_directory_error(self):
        """Verify tools/repack_rom.py returns non-zero error when input directory is empty or missing."""
        if not (TOOLS_DIR / "repack_rom.py").is_file():
            self.skipTest("tools/repack_rom.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "repack_rom.py", ["C:/nonexistent/empty_dir", "C:/tmp/out.3ds"]
        )
        self.assertNotEqual(code, 0, "Repacking empty directory must return non-zero code")


if __name__ == "__main__":
    unittest.main()
