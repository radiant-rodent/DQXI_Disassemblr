"""Unit tests for the real-hardware instruction check (no emulator needed).

Run with:  python -m unittest tests.emu.test_check_armv6k -v
These are also exercised by ``python -m tests.emu`` indirectly through every export.
"""
from __future__ import annotations

import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from tools import check_armv6k


ROOT = Path(__file__).resolve().parent.parent.parent
RETAIL = ROOT / "original" / "exefs" / "code.decompressed.bin"
CAVE = 0x724D00


def _retail() -> bytes:
    return RETAIL.read_bytes()


class CheckArmv6kTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.code = _retail()

    def test_retail_is_clean(self):
        result = check_armv6k.check_code(self.code, self.code)
        self.assertTrue(result["ok"])
        self.assertEqual(result["changed_words"], 0)

    def test_vfpv3_immediate_is_refused(self):
        try:
            import keystone
        except ImportError:
            self.skipTest("keystone is not installed")
        code = bytearray(self.code)
        enc = bytes(keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
                    .asm("vmov.f32 s0, #1.0", CAVE)[0])
        code[CAVE - 0x100000:CAVE - 0x100000 + 4] = enc
        result = check_armv6k.check_code(self.code, bytes(code))
        self.assertFalse(result["ok"])
        self.assertEqual(result["hits"][0]["address"], CAVE)
        self.assertIn("vmov", result["hits"][0]["name"])

    def test_changed_data_outside_text_is_not_an_instruction(self):
        code = bytearray(self.code)
        # .rodata starts at 0x725000; a VFPv3-looking word there is data, not code.
        at = 0x726000
        code[at - 0x100000:at - 0x100000 + 4] = struct.pack("<I", 0xEEB70A00)
        result = check_armv6k.check_code(self.code, bytes(code))
        self.assertTrue(result["ok"])

    def test_literal_pool_word_is_skipped(self):
        # 0x100040 is loaded by a PC-relative `ldr` (a literal pool); changing it to a
        # forbidden-looking value is data, not an instruction.
        code = bytearray(self.code)
        at = 0x100040
        code[at - 0x100000:at - 0x100000 + 4] = struct.pack("<I", 0xEEB70A00)
        result = check_armv6k.check_code(self.code, bytes(code))
        self.assertTrue(result["ok"])
        self.assertTrue(any(h.get("data") for h in result["hits"]))

    def test_export_refuses_changed_vfpv3_code(self):
        """The real exporter must exit 2 and write nothing for a bad native edit."""
        from tools import export_mod
        try:
            import keystone
        except ImportError:
            self.skipTest("keystone is not installed")
        tmp = Path(tempfile.mkdtemp(prefix="x3_arm_", dir=ROOT / "build"))
        try:
            (tmp / "mod" / "code").mkdir(parents=True)
            bad = bytearray(self.code)
            enc = bytes(keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
                        .asm("vmov.f32 s0, #1.0", CAVE)[0])
            bad[CAVE - 0x100000:CAVE - 0x100000 + 4] = enc
            (tmp / "mod" / "code" / "code.bin").write_bytes(bad)
            out = tmp / "out"
            rc = export_mod.main(["--mod", str(tmp / "mod"), "--out", str(out),
                                  "--target", "luma"])
            self.assertEqual(rc, 2)
            self.assertFalse((out / "luma").exists())
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    unittest.main()
