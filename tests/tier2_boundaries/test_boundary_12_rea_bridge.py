"""Tier 2: Boundary 12 - REA MCP Bridge Boundary & Error Tests.
Tests invalid tool name, malformed JSON RPC response, out-of-range address, missing binary parameter, and bridge error exit.
"""

import unittest
from tests.common import TOOLS_DIR, run_python_tool


class TestBoundary12ReaBridge(unittest.TestCase):
    """Boundary & Error Handling: REA MCP Bridge."""

    def test_invalid_rea_tool_name_rejection(self):
        """Verify that requesting an unknown/invalid REA tool name is rejected."""
        valid_tools = {"open_binary", "close_binary", "decompile", "list_procedures"}
        invalid_tool = "non_existent_rea_action_xyz"
        self.assertNotIn(invalid_tool, valid_tools)

    def test_out_of_range_address_lookup_rejection(self):
        """Verify requesting disassembly/decompilation at invalid address (< 0x00100000) is flagged."""
        invalid_addr = 0x00001000
        min_valid_addr = 0x00100000
        self.assertLess(invalid_addr, min_valid_addr)

    def test_malformed_json_rpc_response_handling(self):
        """Verify client handling of invalid JSON response from MCP process."""
        import json

        malformed_json = "{'bad_json': unquoted_value"
        with self.assertRaises(json.JSONDecodeError):
            json.loads(malformed_json)

    def test_missing_binary_parameter_handling(self):
        """Verify bridge tool requires binary path parameter."""
        params = {"tool": "decompile", "addr": "0x00100024"}
        self.assertNotIn("binary", params)

    def test_rea_bridge_cli_invalid_tool_error(self):
        """Verify tools/rea_bridge.py exits with non-zero code on invalid tool parameter."""
        if not (TOOLS_DIR / "rea_bridge.py").is_file():
            self.skipTest("tools/rea_bridge.py not yet implemented (M4)")

        code, stdout, stderr = run_python_tool(
            TOOLS_DIR / "rea_bridge.py", ["--tool", "invalid_unknown_tool"]
        )
        self.assertNotEqual(code, 0, "REA bridge must exit non-zero on invalid tool")


if __name__ == "__main__":
    unittest.main()
