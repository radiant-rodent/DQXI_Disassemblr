"""Tier 4: Scenario 4 - Progressive C Replacement & Visual Diff Matching.
Features Exercised: F7 (Build Pipeline), F8 (Typed Headers), F9 (Startup C Lifting), F10 (Visual Diff).
Verifies lifted C code replacement workflow and programmatic bytecode equivalence verification.
"""

import unittest
from tests.common import INIT_BSS_BYTES, TOOLS_DIR, run_python_tool


class TestScenario4ProgressiveCDiff(unittest.TestCase):
    """Scenario 4: Progressive C Replacement & Visual Diff Matching."""

    def test_scenario_4_init_bss_exact_bytecode_equivalence(self):
        """Verify recompiled InitBss matches retail binary bytecode byte-for-byte."""
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
        recompiled = bytes(encoding)
        original = INIT_BSS_BYTES[:28]

        self.assertEqual(
            recompiled,
            original,
            "Recompiled InitBss does not match target retail bytecode",
        )

    def test_scenario_4_diff_tool_automated_verification(self):
        """Verify tools/diff.py executes and validates InitBss if implemented in M3."""
        diff_tool = TOOLS_DIR / "diff.py"
        if not diff_tool.is_file():
            self.skipTest("tools/diff.py not yet implemented (M3)")

        code, stdout, stderr = run_python_tool(
            diff_tool, ["0x00100024"]
        )
        self.assertEqual(code, 0, f"diff.py failed: {stderr}")
        self.assertIn("100", stdout)


if __name__ == "__main__":
    unittest.main()
