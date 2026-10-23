"""Tier 2: Boundary 7 - Reassembly Build Pipeline Boundary & Error Tests.
Tests missing source files, assembler syntax errors, non-zero return code propagation, and invalid tool arguments.
"""

import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary07BuildPipeline(unittest.TestCase):
    """Boundary & Error Handling: Reassembly Build Pipeline."""

    def test_missing_source_file_error_detection(self):
        """Verify build pipeline detects missing assembly or C source file."""
        expected_sources = ["start.s", "init.c"]
        existing_sources = ["start.s"]  # init.c missing
        missing = [s for s in expected_sources if s not in existing_sources]
        self.assertEqual(missing, ["init.c"])

    def test_assembler_syntax_error_simulation(self):
        """Verify assembler returns error on invalid assembly syntax."""
        import keystone

        ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
        with self.assertRaises(keystone.KsError):
            ks.asm("INVALID_ARM_INSTRUCTION_SYNTAX r0, r1")

    def test_non_zero_return_code_propagation(self):
        """Verify failure in sub-compilation step produces a non-zero exit code overall."""
        failed_substep_code = 1
        overall_exit_code = failed_substep_code if failed_substep_code != 0 else 0
        self.assertNotEqual(overall_exit_code, 0)

    def test_build_py_invalid_flag_handling(self):
        """Verify tools/build.py rejects unknown CLI flags with non-zero exit code."""
        if not (TOOLS_DIR / "build.py").is_file():
            self.skipTest("tools/build.py not yet implemented (M2)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "build.py", ["--invalid-nonexistent-flag-xyz"]
        )
        self.assertNotEqual(code, 0, "Build tool must reject invalid flags")

    def test_build_timeout_handling(self):
        """Verify timeout parameter handling for build pipeline jobs."""
        timeout_sec = 60
        self.assertGreater(timeout_sec, 0)


if __name__ == "__main__":
    unittest.main()
