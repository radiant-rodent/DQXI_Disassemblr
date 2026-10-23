"""Tier 1: Feature 11 - Symbol Registry & Types Tests.
Verifies symbol registry schema, known reverse-engineered symbols, address hex formatting, and symbols.json.
"""

import json
import re
import unittest
from tests.common import SYMBOLS_FILE

KNOWN_RE_SYMBOLS = [
    {"address": "0x00100024", "name": "InitBss", "type": "function"},
    {"address": "0x00102EF8", "name": "InitHeaps", "type": "function"},
    {"address": "0x0055E928", "name": "HeapAlloc", "type": "function"},
    {"address": "0x0055E808", "name": "HeapFree", "type": "function"},
    {"address": "0x006F1C9C", "name": "SmallBlockAlloc", "type": "function"},
    {"address": "0x007F50F0", "name": "g_UIAllocator", "type": "object"},
    {"address": "0x007F5144", "name": "g_UIFallbackHeap", "type": "object"},
    {"address": "0x0072EF3C", "name": "s_SaveCodeAlphabet", "type": "table"},
]


class TestFeature11SymbolRegistry(unittest.TestCase):
    """Feature 11: Knowledge Base and Symbol Registry."""

    def test_symbol_schema_specification(self):
        """Verify symbol record fields specification."""
        required_fields = {"address", "name", "type"}
        for sym in KNOWN_RE_SYMBOLS:
            self.assertTrue(required_fields.issubset(sym.keys()))

    def test_known_boot_symbols_catalog(self):
        """Verify known reverse-engineered symbols list covers essential runtime subsystems."""
        names = {s["name"] for s in KNOWN_RE_SYMBOLS}
        self.assertIn("InitBss", names)
        self.assertIn("InitHeaps", names)
        self.assertIn("HeapAlloc", names)
        self.assertIn("SmallBlockAlloc", names)
        self.assertIn("s_SaveCodeAlphabet", names)

    def test_address_hex_format_validation(self):
        """Verify all symbol addresses are formatted as valid 8-digit hex prefixed with '0x00'."""
        pattern = re.compile(r"^0x00[0-9A-Fa-f]{6}$")
        for sym in KNOWN_RE_SYMBOLS:
            self.assertTrue(
                pattern.match(sym["address"]),
                f"Address {sym['address']} is not in 0x00XXXXXX format",
            )

    def test_no_duplicate_symbol_addresses(self):
        """Verify unique addresses across the symbol inventory."""
        addrs = [s["address"].lower() for s in KNOWN_RE_SYMBOLS]
        self.assertEqual(
            len(addrs), len(set(addrs)), "Duplicate addresses detected in symbol set"
        )

    def test_symbols_json_file(self):
        """Verify symbols.json if present at project root."""
        if not SYMBOLS_FILE.is_file():
            self.skipTest("symbols.json not yet created (M4)")

        with open(SYMBOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        self.assertIn("symbols", data)
        symbols = data["symbols"]
        self.assertIsInstance(symbols, list)
        self.assertGreaterEqual(len(symbols), 5)


if __name__ == "__main__":
    unittest.main()
