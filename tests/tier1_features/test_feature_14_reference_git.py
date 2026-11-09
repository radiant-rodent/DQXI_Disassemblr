"""Tier 1: Feature 14 - Reference Git Pristine State Tests.
Verifies that ../3DS_Translate remains strictly pristine and read-only with zero modifications.
"""

import subprocess
import unittest
from tests.common import REFERENCE_PROJECT

# Baseline known untracked docs images in 3DS_Translate before start
KNOWN_UNTRACKED_PNGS = {
    "docs/2d_talk_wrap_after.png",
    "docs/2d_talk_wrap_before.png",
    "docs/battle_long_name.png",
    "docs/battle_word_wrap.png",
    "docs/name_keyboard_2026-10-16.png",
    "docs/name_squeeze_preview.png",
    "docs/shop_crash_before_after.png",
}


class TestFeature14ReferenceGit(unittest.TestCase):
    """Feature 14: Reference Repository Pristine Git Invariant."""

    def test_reference_repo_is_git_repository(self):
        """Verify ../3DS_Translate has a valid .git directory."""
        git_dir = REFERENCE_PROJECT / ".git"
        self.assertTrue(
            git_dir.is_dir(),
            f"Expected .git directory at {git_dir}",
        )

    def test_no_tracked_modifications_in_reference_repo(self):
        """The reference project is unchanged since this test run started.

        It is the user's own working copy and may be dirty; what must never
        happen is that this project's tools or tests modify it.
        """
        from tests.common import reference_changes_since_start
        changes = reference_changes_since_start()
        self.assertEqual(changes, [], f"reference project changed during the run: {changes}")

    def test_no_staged_changes_in_reference_repo(self):
        """Verify git diff --cached reports 0 staged changes in 3DS_Translate."""
        res = subprocess.run(
            ["git", "diff", "--cached", "--exit-code"],
            cwd=str(REFERENCE_PROJECT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(
            res.returncode,
            0,
            f"Staged changes detected in reference repo! Diff output:\n{res.stdout}",
        )

    def test_no_new_untracked_files_added_by_agents(self):
        """The reference project is unchanged since this test run started.

        It is the user's own working copy and may be dirty; what must never
        happen is that this project's tools or tests modify it.
        """
        from tests.common import reference_changes_since_start
        changes = reference_changes_since_start()
        self.assertEqual(changes, [], f"reference project changed during the run: {changes}")

    def test_reference_branch_and_commit_state(self):
        """Verify repository HEAD points to valid commit on main."""
        res = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            cwd=str(REFERENCE_PROJECT),
            capture_output=True,
            text=True,
        )
        self.assertEqual(res.returncode, 0)
        self.assertEqual(res.stdout.strip(), "main")


if __name__ == "__main__":
    unittest.main()
