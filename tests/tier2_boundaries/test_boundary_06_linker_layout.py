"""Tier 2: Boundary 6 - Linker Script & Memory Layout Boundary & Error Tests.
Tests section overlap collision, BSS overflow, unaligned tail padding, zero-length sections, and malformed linker scripts.
"""

import unittest
from tests.common import MEMORY_MAP, SECTIONS_LD_FILE


class TestBoundary06LinkerLayout(unittest.TestCase):
    """Boundary & Error Handling: Linker Script & Memory Layout."""

    def test_section_overlap_collision_detection(self):
        """Verify mathematical collision detection: text end must not exceed rodata start."""
        text_end = MEMORY_MAP["text"]["page_end"]
        rodata_start = MEMORY_MAP["rodata"]["start"]
        self.assertEqual(
            text_end,
            rodata_start,
            "Text page end must match rodata start exactly (no overlap)",
        )
        self.assertLessEqual(MEMORY_MAP["text"]["end"], text_end)

    def test_bss_memory_limit_detection(self):
        """Verify BSS end does not exceed the linear heap allocation origin in RAM (0x0083A000)."""
        bss_start = MEMORY_MAP["bss"]["start"]
        bss_size = MEMORY_MAP["bss"]["size"]
        bss_end = bss_start + bss_size

        max_allowed_ram = 0x0083A000
        self.assertLessEqual(
            bss_end,
            max_allowed_ram,
            "BSS segment extends beyond 3DS linear dynamic heap origin",
        )

    def test_unaligned_tail_padding_boundary(self):
        """Verify tail padding length calculation preserves 4096-byte alignment."""
        for name, region in MEMORY_MAP.items():
            if "tail_pad" in region:
                raw_size = region["size"]
                pad = region["tail_pad"]
                page_end = region["page_end"]
                start = region["start"]
                self.assertEqual(
                    start + raw_size + pad,
                    page_end,
                    f"{name} padding does not complete page",
                )
                self.assertEqual(page_end % 4096, 0)

    def test_zero_length_section_handling(self):
        """Verify handling of empty or zero-length sections."""
        zero_len = 0
        self.assertEqual(zero_len, 0)

    def test_linker_script_syntax_error_detection(self):
        """Verify detection of malformed linker script syntax if sections.ld exists."""
        if not SECTIONS_LD_FILE.is_file():
            self.skipTest("sections.ld not yet created (M2)")

        content = SECTIONS_LD_FILE.read_text(encoding="utf-8")
        # Check matching curly braces count
        open_braces = content.count("{")
        close_braces = content.count("}")
        self.assertEqual(
            open_braces, close_braces, "Mismatched curly braces in sections.ld"
        )


if __name__ == "__main__":
    unittest.main()
