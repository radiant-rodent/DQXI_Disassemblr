"""Tier 1: Feature 1 - ROM Extraction Tests.
Verifies ROM container architecture, partition layout, NCSD/NCCH headers, and extract_rom tool contract.
"""

import struct
import unittest
from tests.common import (
    EXPECTED_SIZES,
    ORIGINAL_DIR,
    REFERENCE_ROM,
    TOOLS_DIR,
    require_tool,
    run_python_tool,
)


class TestFeature01RomExtraction(unittest.TestCase):
    """Feature 1: ROM Extraction and Container Analysis."""

    def test_reference_rom_exists_and_size(self):
        """Verify the reference ROM exists and matches exact 4GB cartridge size."""
        self.assertTrue(
            REFERENCE_ROM.is_file(), f"Reference ROM not found at {REFERENCE_ROM}"
        )
        self.assertEqual(
            REFERENCE_ROM.stat().st_size,
            EXPECTED_SIZES["rom"],
            f"ROM size mismatch: expected {EXPECTED_SIZES['rom']} bytes",
        )

    def test_ncsd_header_magic_and_media_id(self):
        """Verify NCSD magic 'NCSD' at offset 0x100 and Cartridge Media ID."""
        with open(REFERENCE_ROM, "rb") as f:
            f.seek(0x100)
            magic = f.read(4)
            self.assertEqual(magic, b"NCSD", "NCSD magic header mismatch")

            media_units = struct.unpack("<I", f.read(4))[0]
            self.assertEqual(
                media_units * 512,
                EXPECTED_SIZES["rom"],
                "Cartridge media unit size mismatch",
            )

            media_id = struct.unpack("<Q", f.read(8))[0]
            self.assertEqual(
                media_id, 0x0004000000199200, "Cartridge media ID mismatch"
            )

    def test_ncsd_partition_table_layout(self):
        """Verify Partition Table offsets and sizes in media units (512 bytes)."""
        with open(REFERENCE_ROM, "rb") as f:
            f.seek(0x120)  # Partition Table offset
            # 8 partition records: (offset, size) in media units (u32 LE)
            partitions = []
            for i in range(8):
                off, sz = struct.unpack("<II", f.read(8))
                partitions.append((off, sz))

            # Partition 0: Main Game CXI at media unit 0x20, size 0x4FFA30 (0x9FF46000 bytes)
            self.assertEqual(partitions[0][0], 0x000020)
            self.assertEqual(partitions[0][1] * 512, 2683592704)

            # Partition 1: Electronic Manual CFA at media unit 0x4FFA50
            self.assertEqual(partitions[1][0], 0x4FFA50)
            self.assertEqual(partitions[1][1] * 512, 1507328)

            # Partition 6: New 3DS Update CFA at media unit 0x5005D0
            self.assertEqual(partitions[6][0], 0x5005D0)
            self.assertEqual(partitions[6][1] * 512, 3653632)

            # Partition 7: Old 3DS Update CFA at media unit 0x5021B0
            self.assertEqual(partitions[7][0], 0x5021B0)
            self.assertEqual(partitions[7][1] * 512, 33390592)

    def test_ncch0_header_and_flags(self):
        """Verify Partition 0 NCCH header at offset 0x4000: magic, product code, NoCrypto flag."""
        with open(REFERENCE_ROM, "rb") as f:
            f.seek(0x4000 + 0x100)  # NCCH magic offset
            magic = f.read(4)
            self.assertEqual(magic, b"NCCH", "NCCH magic mismatch")

            f.seek(0x4000 + 0x150)
            product_code = f.read(16).rstrip(b"\x00").decode("ascii", errors="replace")
            self.assertEqual(product_code, "CTR-P-BTZJ", "Product code mismatch")

            f.seek(0x4000 + 0x188)
            flags = f.read(8)
            # Byte 7 is bitmask: 0x04 indicates NoCrypto (decrypted)
            self.assertEqual(
                flags[7] & 0x04,
                0x04,
                "NoCrypto bit not set; decrypted ROM required",
            )

    def test_extract_rom_cli_interface(self):
        """Verify tools/extract_rom.py CLI entry point and argument parsing."""
        if not (TOOLS_DIR / "extract_rom.py").is_file():
            self.skipTest("tools/extract_rom.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "extract_rom.py", ["--help"]
        )
        self.assertEqual(code, 0, f"extract_rom.py --help failed: {stderr}")
        self.assertIn("rom", stdout.lower() + stderr.lower())


if __name__ == "__main__":
    unittest.main()
