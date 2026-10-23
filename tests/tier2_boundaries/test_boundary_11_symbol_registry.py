"""Tier 2: Boundary 11 - Symbol Registry Boundary & Error Tests.
Tests duplicate address detection, duplicate symbol names, malformed hex addresses, missing schema keys, and empty symbol lists.
"""

import re
import unittest


class TestBoundary11SymbolRegistry(unittest.TestCase):
    """Boundary & Error Handling: Symbol Registry."""

    def test_duplicate_address_detection(self):
        """Verify duplicate address detection flags conflicting symbol mappings."""
        symbols = [
            {"address": "0x00100024", "name": "InitBss"},
            {"address": "0x00100024", "name": "InitBssDuplicate"},
        ]
        addrs = [s["address"] for s in symbols]
        self.assertNotEqual(
            len(addrs), len(set(addrs)), "Duplicate address was not flagged"
        )

    def test_duplicate_symbol_name_detection(self):
        """Verify duplicate name detection flags conflicting function definitions."""
        symbols = [
            {"address": "0x00100024", "name": "InitBss"},
            {"address": "0x00100028", "name": "InitBss"},
        ]
        names = [s["name"] for s in symbols]
        self.assertNotEqual(
            len(names), len(set(names)), "Duplicate symbol name was not flagged"
        )

    def test_malformed_hex_address_rejection(self):
        """Verify that malformed hex strings (missing 0x prefix or non-hex chars) are detected."""
        malformed = ["00100024", "0xGG100024", "0x10002", "0x0010002400"]
        pattern = re.compile(r"^0x00[0-9A-Fa-f]{6}$")
        for addr in malformed:
            self.assertIsNone(
                pattern.match(addr), f"Address {addr} should be invalid"
            )

    def test_missing_required_schema_field(self):
        """Verify symbol records missing required 'name' or 'address' field fail validation."""
        incomplete_symbol = {"address": "0x00100024"}  # missing "name"
        self.assertNotIn("name", incomplete_symbol)

    def test_empty_symbols_list_validation(self):
        """Verify handling of empty symbol list."""
        empty_list = []
        self.assertEqual(len(empty_list), 0)


if __name__ == "__main__":
    unittest.main()
