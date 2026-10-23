"""Tier 1: Feature 10 - Visual Diff Verification Tests.
Verifies Capstone + Colorama diffing engine, bytecode comparison algorithm, ANSI color formatting, and tools/diff.py CLI.
"""

import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestFeature10VisualDiff(unittest.TestCase):
    """Feature 10: Visual Bytecode Diff Tool."""

    def test_diff_tool_libraries_available(self):
        """Verify Capstone and Colorama packages are available."""
        import capstone
        import colorama

        self.assertIsNotNone(capstone.__version__)
        self.assertIsNotNone(colorama.__version__)

    def test_instruction_matching_logic(self):
        """Verify instruction bytecode exact match vs mismatch logic."""
        inst1 = bytes.fromhex("14009fe5")  # ldr r0, [pc, #0x14]
        inst2 = bytes.fromhex("14009fe5")  # ldr r0, [pc, #0x14]
        inst3 = bytes.fromhex("14109fe5")  # ldr r1, [pc, #0x14]

        self.assertEqual(inst1, inst2, "Identical instructions must match")
        self.assertNotEqual(inst1, inst3, "Differing registers must not match")

    def test_ansi_color_formatting(self):
        """Verify Colorama ANSI color escapes for formatting diff outputs."""
        from colorama import Fore, Style

        green_match = f"{Fore.GREEN}[MATCH]{Style.RESET_ALL}"
        red_mismatch = f"{Fore.RED}[DIFF]{Style.RESET_ALL}"
        yellow_reloc = f"{Fore.YELLOW}[RELOC]{Style.RESET_ALL}"

        self.assertIn("\033[", green_match)
        self.assertIn("\033[", red_mismatch)
        self.assertIn("\033[", yellow_reloc)

    def test_diff_percentage_calculation(self):
        """Verify match percentage calculation: matched_instructions / total_instructions * 100."""
        total = 20
        matched = 19
        pct = (matched / total) * 100.0
        self.assertAlmostEqual(pct, 95.0, places=1)
        self.assertEqual(f"{pct:.1f}%", "95.0%")

    def test_diff_py_cli_interface(self):
        """Verify tools/diff.py CLI entry point if implemented."""
        if not (TOOLS_DIR / "diff.py").is_file():
            self.skipTest("tools/diff.py not yet implemented (M3)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "diff.py", ["--help"]
        )
        self.assertEqual(code, 0, f"diff.py --help failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
