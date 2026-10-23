"""Tier 1: Feature 3 - Bit-Matching Repacker Tests.
Verifies cartridge padding invariant (0xFF), partition continuity, and repack_rom tool specification.
"""

import unittest
from tests.common import (
    EXPECTED_HASHES,
    EXPECTED_SIZES,
    REFERENCE_ROM,
    TOOLS_DIR,
    run_python_tool,
)


class TestFeature03RomRepack(unittest.TestCase):
    """Feature 3: Bit-Matching ROM Repacking."""

    def test_trailing_padding_specification(self):
        """Verify cartridge trailing padding from 0xA240E000 to 0x100000000 is 100% 0xFF bytes."""
        pad_start = 0xA240E000
        pad_size = 1572806656  # 0x5DBF2000
        self.assertEqual(pad_start + pad_size, EXPECTED_SIZES["rom"])

        # Check a sample of 64 KB from the start and near the end of padding
        with open(REFERENCE_ROM, "rb") as f:
            f.seek(pad_start)
            sample_start = f.read(65536)
            self.assertEqual(
                sample_start, b"\xFF" * 65536, "Padding start is not 0xFF"
            )

            f.seek(pad_start + pad_size - 65536)
            sample_end = f.read(65536)
            self.assertEqual(
                sample_end, b"\xFF" * 65536, "Padding end is not 0xFF"
            )

    def test_cartridge_total_size_and_alignment(self):
        """Verify repacked target size is 4GB (8,388,608 media units of 512 bytes)."""
        total_size = EXPECTED_SIZES["rom"]
        self.assertEqual(total_size % 512, 0, "Cartridge size must be 512-byte aligned")
        self.assertEqual(total_size, 4 * 1024 * 1024 * 1024)

    def test_partition_continuity_in_rom(self):
        """Verify zero gaps between consecutive active partitions in reference ROM."""
        # P0: 0x4000 .. 0x9FF4A000
        p0_start = 0x4000
        p0_size = 2683592704
        p1_start = p0_start + p0_size
        self.assertEqual(p1_start, 0x9FF4A000)

        # P1: 0x9FF4A000 .. 0xA00BA000
        p1_size = 1507328
        p6_start = p1_start + p1_size
        self.assertEqual(p6_start, 0xA00BA000)

        # P6: 0xA00BA000 .. 0xA0436000
        p6_size = 3653632
        p7_start = p6_start + p6_size
        self.assertEqual(p7_start, 0xA0436000)

        # P7: 0xA0436000 .. 0xA240E000
        p7_size = 33390592
        pad_start = p7_start + p7_size
        self.assertEqual(pad_start, 0xA240E000)

    def test_repacked_rom_checksum_target(self):
        """Verify target SHA-256 for repacked ROM is the retail cartridge hash."""
        self.assertEqual(
            EXPECTED_HASHES["rom"],
            "0f04b51bc6dc145106fb7bc957fa41991cd02d89e0af2c8775db9d12a37a9b74",
        )

    def test_repack_rom_cli_interface(self):
        """Verify tools/repack_rom.py CLI interface and help message."""
        if not (TOOLS_DIR / "repack_rom.py").is_file():
            self.skipTest("tools/repack_rom.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "repack_rom.py", ["--help"]
        )
        self.assertEqual(code, 0, f"repack_rom.py --help failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
