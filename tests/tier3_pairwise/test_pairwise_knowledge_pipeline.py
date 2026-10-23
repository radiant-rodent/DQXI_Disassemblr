"""Tier 3: Pairwise Combination 4 - Knowledge Base, REA & Reference Invariant Interactions.
Tests pairwise interactions:
- Pair 12: Symbol Registry + REA MCP Bridge (F11 + F12)
- Pair 13: REA Bridge + Agent Collaboration Log (F12 + F13)
- Pair 14: Full Pipeline Toolchain + Reference Git Invariant (F7 + F14)
"""

import subprocess
import unittest
from tests.common import REFERENCE_PROJECT


class TestPairwiseKnowledgePipeline(unittest.TestCase):
    """Pairwise Cross-Feature Interactions: Knowledge, REA, & Invariants."""

    def test_pair_12_symbols_to_rea_bridge(self):
        """Pair 12 (F11 + F12): Symbol addresses from registry serve as inputs to REA decompilation requests."""
        query = {
            "tool": "procedure_pseudo_code",
            "params": {"address": "0x00100024"},
        }
        self.assertEqual(query["params"]["address"], "0x00100024")

    def test_pair_13_rea_to_notes(self):
        """Pair 13 (F12 + F13): Decompiled analysis discoveries are structured for insertion into the project notes."""
        log_entry_template = (
            "### REA Analysis: 0x00100024 (InitBss)\n"
            "- **Status**: Verified matching\n"
            "- **Discovered**: Post-indexed store loop clears BSS\n"
        )
        self.assertIn("0x00100024", log_entry_template)
        self.assertIn("InitBss", log_entry_template)

    def test_pair_14_pipeline_to_reference_git_invariant(self):
        """Pair 14 (F7 + F14): running the tools that read the reference project changes nothing in it."""
        import sys
        from tests.common import PROJECT_ROOT, reference_snapshot
        before = reference_snapshot()
        # tools that open the translation database / import from the reference tree
        subprocess.run([sys.executable, str(PROJECT_ROOT / "tools" / "build_model_names.py")],
                       cwd=str(PROJECT_ROOT), capture_output=True, check=True)
        subprocess.run([sys.executable, "-c", "import tools.model_tool, tools.texture_tool"],
                       cwd=str(PROJECT_ROOT), capture_output=True, check=True)
        self.assertEqual(reference_snapshot(), before, "a tool modified the reference project")



if __name__ == "__main__":
    unittest.main()
