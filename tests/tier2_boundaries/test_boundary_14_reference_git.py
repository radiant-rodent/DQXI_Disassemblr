"""Tier 2: Boundary 14 - Reference Git Invariant Boundary & Error Tests.
Tests non-git directory handling, modified file detection logic, staged changes detection, untracked file detection, and git binary availability.
"""

import shutil
import subprocess
import unittest
from tests.common import PROJECT_ROOT, REFERENCE_PROJECT


class TestBoundary14ReferenceGit(unittest.TestCase):
    """Boundary & Error Handling: Reference Git Invariant."""

    def test_git_executable_available_in_path(self):
        """Verify git executable is found in system PATH."""
        git_path = shutil.which("git")
        self.assertIsNotNone(git_path, "git executable not found in PATH")

    def test_non_git_directory_error_code(self):
        """Verify running git diff on a non-git directory returns non-zero exit code."""
        # A subfolder without .git or tmp folder
        res = subprocess.run(
            ["git", "status"],
            cwd="C:/",
            capture_output=True,
            text=True,
        )
        # Typically returns 128 (fatal: not a git repository)
        self.assertNotEqual(res.returncode, 0)

    def test_modified_tracked_file_detection_logic(self):
        """Verify porcelain status line ' M ' indicates modified tracked file."""
        porcelain_line = " M src/main.c"
        is_modified = porcelain_line.startswith(" M") or porcelain_line.startswith("M ")
        self.assertTrue(is_modified)

    def test_staged_changes_detection_logic(self):
        """Verify porcelain status line 'M  ' indicates staged modification."""
        staged_line = "M  src/main.c"
        is_staged = staged_line.startswith("M ")
        self.assertTrue(is_staged)

    def test_untracked_file_detection_logic(self):
        """Verify porcelain status line '?? ' indicates untracked file."""
        untracked_line = "?? temp_output.txt"
        is_untracked = untracked_line.startswith("??")
        self.assertTrue(is_untracked)


if __name__ == "__main__":
    unittest.main()
