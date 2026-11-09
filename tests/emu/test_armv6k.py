"""Fast checks for tools/check_armv6k.py and the exporter's refusal (no emulator needed).

    python -m unittest tests.emu.test_armv6k -v

These are the rules a real 3DS/2DS enforces: ARM11 MPCore, ARMv6K, VFPv2 only.  Azahar
executes ARMv7/VFPv3 too, so an emulator boot cannot prove a code cave is safe; the exporter
must refuse it instead.
"""
from __future__ import annotations

import json
import struct
import subprocess
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from tests.emu import fixtures as F  # noqa: E402
from tools.check_armv6k import check_code  # noqa: E402

CAVE = 0x724D00          # free .text tail used by the emulator-only probes


class Armv6kTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.retail = F.RETAIL_CODE.read_bytes()

    def patched(self, word: int, at: int = CAVE) -> bytes:
        out = bytearray(self.retail)
        struct.pack_into("<I", out, at - 0x100000, word)
        return bytes(out)

    def test_test_build_is_armv6k_safe(self):
        """The input hook + text logger used by the emulator tests must pass the same gate."""
        r = check_code(self.retail, F.test_code())
        self.assertTrue(r["ok"], [h for h in r["hits"] if not h.get("data")])
        self.assertEqual(r["changed_words"], 215)      # hook + logger + their literal words

    def test_vfpv3_immediate_is_rejected(self):
        # vmov.f32 s0, #1.0  (VFPv3) - the exact instruction that crashed a real 2DS
        r = check_code(self.retail, self.patched(0xEEB70A00))
        self.assertFalse(r["ok"])
        self.assertEqual(len([h for h in r["hits"] if not h.get("data")]), 1)
        self.assertIn("VFPv3", r["hits"][0]["name"])

    def test_armv7_divides_are_rejected(self):
        for word, name in ((0xE710F110, "sdiv/udiv"), (0xE7A00050, "ubfx/sbfx"),
                           (0xE7C00010, "bfi/bfc"), (0xE6FF0F30, "rbit")):
            with self.subTest(name=name):
                r = check_code(self.retail, self.patched(word))
                self.assertFalse(r["ok"], name)

    def test_movw_movt_are_rejected(self):
        for word in (0xE3000123, 0xE3400123):
            with self.subTest(word=f"{word:08X}"):
                self.assertFalse(check_code(self.retail, self.patched(word))["ok"])

    def test_literal_pool_word_is_data_not_code(self):
        # Put a VFPv3-looking word into a literal pool that an ldr pc loads from?  Simpler:
        # the word must be in a pool address used by a PC-relative ldr.  Build one in the
        # cave: ldr r0, [pc, #0] at CAVE, value at CAVE+8.
        code = bytearray(self.retail)
        base = CAVE - 0x100000
        struct.pack_into("<I", code, base, 0xE59F0000)       # ldr r0, [pc, #0]
        struct.pack_into("<I", code, base + 8, 0xEEB70A00)   # VFPv3 word (data)
        r = check_code(self.retail, bytes(code))
        self.assertTrue(r["ok"], r["hits"])
        self.assertTrue(any(h.get("data") for h in r["hits"]))

    def test_exporter_refuses_a_violating_mod(self):
        """tools/export_mod.py must exit 2 and write nothing for a VFPv3 code cave."""
        ws = F.workspace("armv6k_refusal")
        # a real change at the cave, with the emulator-only test build around it
        bad = bytearray(F.test_code())
        struct.pack_into("<I", bad, CAVE - 0x100000, 0xEEB70A00)
        F.add_code(ws, bytes(bad))
        out = F.OUT / "armv6k_refusal"
        if out.exists():
            import shutil
            shutil.rmtree(out)
        p = subprocess.run([sys.executable, "tools/export_mod.py", "--mod", str(ws),
                            "--out", str(out), "--target", "luma"],
                           cwd=REPO, capture_output=True, text=True)
        self.assertEqual(p.returncode, 2, p.stdout + p.stderr)
        self.assertIn("real 3DS", p.stderr + p.stdout)
        self.assertIn("vmov", p.stderr + p.stdout)
        self.assertFalse((out / "luma").exists(), "a refused export must leave no output")

    def test_exporter_accepts_the_safe_test_build(self):
        ws = F.workspace("armv6k_accept")
        F.add_code(ws)
        rc, text, out = F.export(ws, "armv6k_accept")
        self.assertEqual(rc, 0, text)
        report = json.loads((out / "EXPORT_REPORT.json").read_text(encoding="utf-8"))
        self.assertTrue(report["armv6k"]["ok"])
        self.assertEqual(report["armv6k"]["violations"], [])

    def test_code_ips_round_trip(self):
        """The Luma code.ips is a real diff: applying it must reproduce the executable."""
        ws = F.workspace("ips_roundtrip")
        F.add_code(ws)
        rc, text, out = F.export(ws, "ips_roundtrip", code="ips")
        self.assertEqual(rc, 0, text)
        ips = (F.luma_title_dir(out) / "code.ips").read_bytes()
        self.assertEqual(ips[:5], b"PATCH")
        self.assertEqual(F.apply_code_ips(ips), F.test_code())


if __name__ == "__main__":
    unittest.main()
