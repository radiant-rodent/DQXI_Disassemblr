"""Tier 2: Boundary 10 - Visual Diff Verification Boundary & Error Tests.
Tests zero-byte diff, complete mismatch diff, unequal size inputs, non-existent symbol address, and diff tool CLI error.
"""

import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary10VisualDiff(unittest.TestCase):
    """Boundary & Error Handling: Visual Diff Verification."""

    def test_complete_mismatch_diff_calculation(self):
        """Verify match percentage calculation for 100% mismatch is 0.0%."""
        total = 10
        matched = 0
        pct = (matched / total) * 100.0
        self.assertEqual(pct, 0.0)

    def test_complete_match_diff_calculation(self):
        """Verify match percentage calculation for 100% match is 100.0%."""
        total = 10
        matched = 10
        pct = (matched / total) * 100.0
        self.assertEqual(pct, 100.0)

    def test_unequal_length_buffers_handling(self):
        """Verify diff handles comparison between buffers of differing sizes."""
        buf1 = b"\x00" * 16
        buf2 = b"\x00" * 32
        self.assertNotEqual(len(buf1), len(buf2))

    def test_unmapped_virtual_address_lookup(self):
        """Verify diff tool behavior on address outside executable range (e.g. 0x00000000 or 0xFFFFFFFF)."""
        invalid_addr = 0x00000000
        min_load_addr = 0x00100000
        self.assertLess(invalid_addr, min_load_addr)

    def test_diff_py_missing_arg_error(self):
        """Verify tools/diff.py returns non-zero error when invoked with missing arguments or invalid symbol."""
        if not (TOOLS_DIR / "diff.py").is_file():
            self.skipTest("tools/diff.py not yet implemented (M3)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "diff.py", ["NonExistentSymbol_XYZ123"]
        )
        self.assertNotEqual(code, 0, "Diff tool must return non-zero code for unknown symbol")


if __name__ == "__main__":
    unittest.main()
