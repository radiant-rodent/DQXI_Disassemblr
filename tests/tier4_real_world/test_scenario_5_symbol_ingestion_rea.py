"""Tier 4: Scenario 5 - Master Symbol Ingestion, Header Compilation & REA Bridge.
Features Exercised: F8 (Typed Headers), F11 (Symbol Registry), F12 (REA Bridge), F13 (Agent Collaboration Log).
Verifies knowledge base ingestion and REA MCP workflow readiness.
"""

import json
import unittest
from tests.common import SYMBOLS_FILE, TOOLS_DIR, run_python_tool


class TestScenario5SymbolIngestionRea(unittest.TestCase):
    """Scenario 5: Master Symbol Ingestion, Header Compilation & REA Bridge."""

    def test_scenario_5_symbols_registry_integrity(self):
        """Verify symbols.json structure and presence of core engine subsystems if present."""
        if not SYMBOLS_FILE.is_file():
            self.skipTest("symbols.json not yet created (M4)")

        with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        symbols = data.get("symbols", [])
        self.assertGreaterEqual(len(symbols), 5)
        names = {s["name"] for s in symbols}
        self.assertIn("InitBss", names)

    def test_scenario_5_rea_bridge_query_execution(self):
        """Verify tools/rea_bridge.py CLI if implemented in M4."""
        bridge_tool = TOOLS_DIR / "rea_bridge.py"
        if not bridge_tool.is_file():
            self.skipTest("tools/rea_bridge.py not yet implemented (M4)")

        code, stdout, stderr = run_python_tool(
            bridge_tool, ["--help"]
        )
        self.assertEqual(code, 0, f"rea_bridge.py --help failed: {stderr}")


if __name__ == "__main__":
    unittest.main()
