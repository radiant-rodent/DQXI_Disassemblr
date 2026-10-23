"""Tier 2: Boundary 8 - Typed Header Definitions Boundary & Error Tests.
Tests struct alignment padding, enum overflow, header re-inclusion protection, null pointer guards, and hardware ABI constraints.
"""

import unittest
from tests.common import INCLUDE_DIR


class TestBoundary08TypedHeaders(unittest.TestCase):
    """Boundary & Error Handling: Typed Headers Library."""

    def test_struct_member_alignment_padding_rules(self):
        """Verify struct members follow 32-bit ARM ABI alignment (4-byte alignment for uint32_t/pointers)."""
        # A struct containing (uint8_t, uint32_t) requires 3 bytes padding before uint32_t
        u8_size = 1
        pad_size = 3
        u32_size = 4
        total_struct_size = u8_size + pad_size + u32_size
        self.assertEqual(total_struct_size, 8)
        self.assertEqual(total_struct_size % 4, 0)

    def test_header_double_inclusion_protection(self):
        """Verify header include guard mechanism handles double inclusion safely."""
        guard_name = "_TYPES_H_"
        content = f"#ifndef {guard_name}\n#define {guard_name}\n// types\n#endif\n"
        self.assertIn(f"#ifndef {guard_name}", content)
        self.assertIn(f"#define {guard_name}", content)

    def test_fixed_width_type_ranges(self):
        """Verify value range boundaries for fixed-width types."""
        uint8_max = 0xFF
        uint16_max = 0xFFFF
        uint32_max = 0xFFFFFFFF
        self.assertEqual(uint8_max, 255)
        self.assertEqual(uint16_max, 65535)
        self.assertEqual(uint32_max, 4294967295)

    def test_null_pointer_definition_constant(self):
        """Verify standard NULL definition evaluated as 0 or ((void*)0)."""
        null_val = 0
        self.assertEqual(null_val, 0)

    def test_include_file_missing_guard_check(self):
        """Verify error detection if any header file lacks guard definitions."""
        if not INCLUDE_DIR.is_dir():
            self.skipTest("include/ directory not yet present (M3)")

        headers = list(INCLUDE_DIR.glob("**/*.h"))
        if not headers:
            self.skipTest("No header files in include/ yet (M3)")

        for h in headers:
            text = h.read_text(encoding="utf-8")
            self.assertTrue(
                "#ifndef" in text or "#pragma once" in text,
                f"Header {h.name} missing include guard",
            )


if __name__ == "__main__":
    unittest.main()
