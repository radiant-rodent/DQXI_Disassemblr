"""Tier 4: Scenario 7 - Full End-to-End Clean Rebuild & Verification (verify.py).
Features Exercised: F1 through F14.
Verifies end-to-end multi-tier pipeline results and runs tools/verify.py.
"""

import unittest
from tests.common import EXPECTED_HASHES, EXPECTED_SIZES, TOOLS_DIR, run_python_tool


class TestScenario7FullPipelineVerification(unittest.TestCase):
    """Scenario 7: Full End-to-End Clean Rebuild & Verification."""

    def test_scenario_7_all_baseline_hashes_accounted(self):
        """Verify baseline hashes inventory is fully defined across all game modules."""
        essential_keys = [
            "rom",
            "code_decompressed",
            "code_compressed",
            "romfs",
            "exheader",
            "logo",
            "plain",
            "banner",
            "icon",
        ]
        for k in essential_keys:
            self.assertIn(k, EXPECTED_HASHES)
            self.assertEqual(len(EXPECTED_HASHES[k]), 64)

    def test_scenario_7_all_baseline_sizes_accounted(self):
        """Verify baseline component sizes inventory is fully defined."""
        essential_keys = [
            "rom",
            "code_decompressed",
            "code_compressed",
            "romfs",
            "exheader",
            "logo",
            "plain",
            "banner",
            "icon",
        ]
        for k in essential_keys:
            self.assertIn(k, EXPECTED_SIZES)
            self.assertGreater(EXPECTED_SIZES[k], 0)

    def test_scenario_7_verify_py_execution(self):
        """Execute tools/verify.py full suite if implemented in M1/M5."""
        verify_tool = TOOLS_DIR / "verify.py"
        if not verify_tool.is_file():
            self.skipTest("tools/verify.py not yet implemented (M1)")

        code, stdout, stderr = run_python_tool(verify_tool, [])
        self.assertEqual(code, 0, f"tools/verify.py failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
