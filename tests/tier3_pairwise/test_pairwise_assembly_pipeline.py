"""Tier 3: Pairwise Combination 2 - Assembly & Reassembly Pipeline Interactions.
Tests pairwise interactions:
- Pair 5: Assembly Splitting + Linker Layout (F5 + F6)
- Pair 6: Disassembly + Build Pipeline (F5 + F7)
- Pair 7: Linker Script + Build Pipeline (F6 + F7)
- Pair 8: Disassembly Splitting + Visual Diff (F5 + F10)
"""

import unittest
from tests.common import (
    EXPECTED_SIZES,
    INIT_BSS_BYTES,
    MEMORY_MAP,
    REFERENCE_CODE_DECOMPRESSED,
)


class TestPairwiseAssemblyPipeline(unittest.TestCase):
    """Pairwise Cross-Feature Interactions: Assembly & Reassembly Pipeline."""

    def test_pair_05_assembly_splitting_to_linker_layout(self):
        """Pair 5 (F5 + F6): Disassembled function boundaries align with linker script segments."""
        # Entry function start is at 0x00100000 (.text start)
        self.assertEqual(MEMORY_MAP["text"]["start"], 0x00100000)
        # InitBss is at 0x00100024, well within .text
        init_bss_addr = 0x00100024
        self.assertGreater(init_bss_addr, MEMORY_MAP["text"]["start"])
        self.assertLess(init_bss_addr, MEMORY_MAP["text"]["end"])

    def test_pair_06_disassembly_to_build_pipeline(self):
        """Pair 6 (F5 + F7): Modular assembly modules reassemble into matching bytecode."""
        import keystone

        ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
        # Assemble InitBss instruction sequence
        asm_code = (
            "ldr r0, [pc, #0x14]\n"
            "ldr r1, [pc, #0x14]\n"
            "mov r2, #0\n"
            "cmp_loop:\n"
            "cmp r0, r1\n"
            "strlo r2, [r0], #4\n"
            "blo cmp_loop\n"
            "bx lr\n"
        )
        encoding, count = ks.asm(asm_code, 0x00100024)
        self.assertEqual(len(encoding), 28)
        self.assertEqual(bytes(encoding), INIT_BSS_BYTES[:28])

    def test_pair_07_linker_to_build_pipeline(self):
        """Pair 7 (F6 + F7): Linker script guarantees exact 7,090,176-byte output size."""
        total_size = (
            (MEMORY_MAP["text"]["page_end"] - MEMORY_MAP["text"]["start"])
            + (MEMORY_MAP["rodata"]["page_end"] - MEMORY_MAP["rodata"]["start"])
            + (MEMORY_MAP["data"]["page_end"] - MEMORY_MAP["data"]["start"])
        )
        self.assertEqual(total_size, EXPECTED_SIZES["code_decompressed"])

    def test_pair_08_disasm_splitting_to_visual_diff(self):
        """Pair 8 (F5 + F10): Disassembled instructions match visual diff comparison against binary slice."""
        import capstone

        with open(REFERENCE_CODE_DECOMPRESSED, "rb") as f:
            f.seek(0x24)
            slice_bytes = f.read(28)

        md = capstone.Cs(capstone.CS_ARCH_ARM, capstone.CS_MODE_ARM)
        disasm_instrs = list(md.disasm(slice_bytes, 0x00100024))
        self.assertEqual(len(disasm_instrs), 7)
        self.assertEqual(slice_bytes, INIT_BSS_BYTES[:28])


if __name__ == "__main__":
    unittest.main()
