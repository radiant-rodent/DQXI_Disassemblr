"""Tier 4: Scenario 6 - Pristine Invariant Verification on 3DS_Translate.
Features Exercised: F14 (Reference Git Invariant).
Verifies that ../3DS_Translate remains strictly read-only and unpolluted.
"""

import subprocess
import unittest
from tests.common import REFERENCE_PROJECT

KNOWN_DOCS_PNGS = {
    "docs/2d_talk_wrap_after.png",
    "docs/2d_talk_wrap_before.png",
    "docs/battle_long_name.png",
    "docs/battle_word_wrap.png",
    "docs/name_keyboard_2026-10-16.png",
    "docs/name_squeeze_preview.png",
    "docs/shop_crash_before_after.png",
}


class TestScenario6ReferencePristineInvariant(unittest.TestCase):
    """Scenario 6: Pristine Invariant Verification on 3DS_Translate."""

    def test_scenario_6_git_status_clean(self):
        """The reference project is unchanged since this test run started.

        It is the user's own working copy and may be dirty; what must never
        happen is that this project's tools or tests modify it.
        """
        from tests.common import reference_changes_since_start
        changes = reference_changes_since_start()
        self.assertEqual(changes, [], f"reference project changed during the run: {changes}")

    def test_scenario_6_git_diff_empty(self):
        """The reference project is unchanged since this test run started.

        It is the user's own working copy and may be dirty; what must never
        happen is that this project's tools or tests modify it.
        """
        from tests.common import reference_changes_since_start
        changes = reference_changes_since_start()
        self.assertEqual(changes, [], f"reference project changed during the run: {changes}")



if __name__ == "__main__":
    unittest.main()
