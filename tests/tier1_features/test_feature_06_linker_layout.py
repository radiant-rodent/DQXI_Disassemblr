"""Tier 1: Feature 6 - Linker Script & Memory Layout Tests.
Verifies CTR process memory regions, page boundaries, tail padding invariants (100% 0x00),
and sections.ld linker script specifications.
"""

import unittest
from tests.common import (
    MEMORY_MAP,
    REFERENCE_CODE_DECOMPRESSED,
    SECTIONS_LD_FILE,
)


class TestFeature06LinkerLayout(unittest.TestCase):
    """Feature 6: Linker Script and Memory Layout Configuration."""

    def test_memory_map_origins_and_sizes(self):
        """Verify memory map segment origins, sizes, and page endpoints match ExHeader specs."""
        text = MEMORY_MAP["text"]
        rodata = MEMORY_MAP["rodata"]
        data = MEMORY_MAP["data"]
        bss = MEMORY_MAP["bss"]

        # Check origins and sizes
        self.assertEqual(text["start"], 0x00100000)
        self.assertEqual(text["size"], 0x0062403C)
        self.assertEqual(rodata["start"], 0x00725000)
        self.assertEqual(rodata["size"], 0x00075A18)
        self.assertEqual(data["start"], 0x0079B000)
        self.assertEqual(data["size"], 0x00027D24)
        self.assertEqual(bss["start"], 0x007C3000)
        self.assertEqual(bss["size"], 0x00076BC0)

    def test_tail_padding_zero_invariants(self):
        """Verify text, rodata, and data tail paddings in reference binary are 100% 0x00 bytes."""
        with open(REFERENCE_CODE_DECOMPRESSED, "rb") as f:
            # Text tail padding: 4036 bytes (file offset 0x62403C to 0x625000)
            f.seek(0x62403C)
            text_pad = f.read(4036)
            self.assertEqual(
                text_pad, b"\x00" * 4036, "Text tail padding must be all 0x00"
            )

            # Rodata tail padding: 1512 bytes (file offset 0x69AA18 to 0x69B000)
            f.seek(0x69AA18)
            rodata_pad = f.read(1512)
            self.assertEqual(
                rodata_pad,
                b"\x00" * 1512,
                "Rodata tail padding must be all 0x00",
            )

            # Data tail padding: 732 bytes (file offset 0x6C2D24 to 0x6C3000)
            f.seek(0x6C2D24)
            data_pad = f.read(732)
            self.assertEqual(
                data_pad, b"\x00" * 732, "Data tail padding must be all 0x00"
            )

    def test_page_alignment_boundaries(self):
        """Verify all segment boundary endpoints align to 4096-byte (4 KB) page boundaries."""
        page_size = 4096
        self.assertEqual(MEMORY_MAP["text"]["page_end"] % page_size, 0)
        self.assertEqual(MEMORY_MAP["rodata"]["page_end"] % page_size, 0)
        self.assertEqual(MEMORY_MAP["data"]["page_end"] % page_size, 0)
        # Total decompressed file size is sum of page lengths
        total_decomp = (
            MEMORY_MAP["text"]["page_end"] - MEMORY_MAP["text"]["start"]
            + (MEMORY_MAP["rodata"]["page_end"] - MEMORY_MAP["rodata"]["start"])
            + (MEMORY_MAP["data"]["page_end"] - MEMORY_MAP["data"]["start"])
        )
        self.assertEqual(total_decomp, 7090176)

    def test_bss_in_ram_allocation(self):
        """Verify BSS segment in RAM spans from 0x007C3000 to 0x00839BC0."""
        bss = MEMORY_MAP["bss"]
        bss_end = bss["start"] + bss["size"]
        self.assertEqual(bss_end, 0x00839BC0)
        # Page aligned to 0x0083A000
        bss_page_end = (bss_end + 4095) & ~4095
        self.assertEqual(bss_page_end, 0x0083A000)

    def test_linker_script_syntax_and_sections(self):
        """Verify sections.ld linker script structure if present."""
        if not SECTIONS_LD_FILE.is_file():
            self.skipTest("sections.ld not yet created (M2)")

        content = SECTIONS_LD_FILE.read_text(encoding="utf-8")
        self.assertIn("elf32-littlearm", content)
        self.assertIn("0x00100000", content)
        self.assertIn(".text", content)
        self.assertIn(".rodata", content)
        self.assertIn(".data", content)
        self.assertIn(".bss", content)


if __name__ == "__main__":
    unittest.main()
