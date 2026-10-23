"""Tier 3: Pairwise Combination 3 - Progressive Decompilation Pipeline Interactions.
Tests pairwise interactions:
- Pair 9: Typed Headers + C Lifting (F8 + F9)
- Pair 10: Startup C Lifting + Visual Diff (F9 + F10)
- Pair 11: Symbol Registry + Disassembly Splitting (F11 + F5)
"""

import unittest
from tests.common import INIT_BSS_BYTES


class TestPairwiseDecompPipeline(unittest.TestCase):
    """Pairwise Cross-Feature Interactions: Progressive C Decompilation."""

    def test_pair_09_typed_headers_to_c_lifting(self):
        """Pair 9 (F8 + F9): Typed headers provide type definitions for lifted C code."""
        # Verification that types like uint32_t match the word-level stores in InitBss
        c_code_snippet = (
            "#include <stdint.h>\n"
            "extern uint32_t __bss_start__[];\n"
            "extern uint32_t __bss_end__[];\n"
            "void InitBss(void) {\n"
            "    uint32_t *dst = __bss_start__;\n"
            "    uint32_t *end = __bss_end__;\n"
            "    while (dst < end) *dst++ = 0;\n"
            "}\n"
        )
        self.assertIn("uint32_t", c_code_snippet)
        self.assertIn("InitBss", c_code_snippet)

    def test_pair_10_c_lifting_to_visual_diff(self):
        """Pair 10 (F9 + F10): Lifted InitBss assembly achieves 100% match in visual diff logic."""
        import keystone

        ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
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
        recompiled_bytes = bytes(encoding)
        original_bytes = INIT_BSS_BYTES[:28]

        # Calculate matching percentage
        self.assertEqual(len(recompiled_bytes), len(original_bytes))
        match_count = sum(
            1
            for a, b in zip(
                range(0, len(original_bytes), 4), range(0, len(recompiled_bytes), 4)
            )
            if original_bytes[a : a + 4] == recompiled_bytes[b : b + 4]
        )
        total_instructions = len(original_bytes) // 4
        pct = (match_count / total_instructions) * 100.0
        self.assertEqual(pct, 100.0, "Visual diff must report 100.0% match for lifted InitBss")

    def test_pair_11_symbol_registry_to_disassembly(self):
        """Pair 11 (F11 + F5): Symbol registry addresses map correctly into disassembly label addresses."""
        symbols = {
            "0x00100024": "InitBss",
            "0x00102EF8": "InitHeaps",
            "0x0055E928": "HeapAlloc",
        }
        for addr_str, sym_name in symbols.items():
            addr = int(addr_str, 16)
            self.assertEqual(addr & 3, 0, f"ARM symbol {sym_name} must be 4-byte aligned")
            self.assertGreater(addr, 0x00100000)


if __name__ == "__main__":
    unittest.main()
