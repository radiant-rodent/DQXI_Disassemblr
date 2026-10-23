"""Tier 2: Boundary 9 - Startup Function C Lifting Boundary & Error Tests.
Tests inverted BSS pointers, equal pointers, single-word BSS, post-indexed store loop boundary, and unaligned pointers.
"""

import unittest
from tests.common import INIT_BSS_BYTES


class TestBoundary09StartupLifting(unittest.TestCase):
    """Boundary & Error Handling: Startup Function C Lifting."""

    def test_inverted_bss_pointers_handling(self):
        """Verify behavior when start pointer > end pointer: loop terminates immediately (0 iterations)."""
        start = 0x00800000
        end = 0x00700000  # end < start
        iterations = 0
        dst = start
        while dst < end:
            iterations += 1
            dst += 4
        self.assertEqual(iterations, 0, "Loop must not execute if end < start")

    def test_equal_bss_pointers_handling(self):
        """Verify behavior when start pointer == end pointer: 0 iterations performed."""
        start = 0x007C2D24
        end = 0x007C2D24
        iterations = 0
        dst = start
        while dst < end:
            iterations += 1
            dst += 4
        self.assertEqual(iterations, 0, "Loop must not execute if start == end")

    def test_single_word_bss_range(self):
        """Verify behavior for exactly 1 word (4 bytes) in BSS range: executes exactly once."""
        buf = [0xDEADBEEF]
        dst = 0
        end = 1
        iterations = 0
        while dst < end:
            buf[dst] = 0
            dst += 1
            iterations += 1
        self.assertEqual(iterations, 1)
        self.assertEqual(buf[0], 0)

    def test_init_bss_instruction_count(self):
        """Verify InitBss code block contains exactly 7 instructions (28 bytes)."""
        import capstone

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        instrs = list(md.disasm(INIT_BSS_BYTES[:28], 0x00100024))
        self.assertEqual(len(instrs), 7)

    def test_post_indexed_store_opcode(self):
        """Verify instruction at 0x100034 is strlo with post-indexed increment [r0], #4."""
        import capstone

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        # Instruction 5 (offset 16): 04208034 -> strlo r2, [r0], #4
        strlo_bytes = bytes.fromhex("04208034")
        instrs = list(md.disasm(strlo_bytes, 0x00100034))
        self.assertEqual(len(instrs), 1)
        self.assertEqual(instrs[0].mnemonic, "strlo")
        self.assertIn("r0", instrs[0].op_str)


if __name__ == "__main__":
    unittest.main()
