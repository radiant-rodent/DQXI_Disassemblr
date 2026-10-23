#!/usr/bin/env python3
"""Verify the ARMv6K C source-replacement loop.

Requires the xPack toolchain installed by tools/setup_arm_toolchain.ps1.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


class SourceReplacementTests(unittest.TestCase):
    def test_clean_c_compiles_for_armv6k(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "check_clean_c.py")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("23/23", r.stdout)

    def test_init_bss_c_replacement_bit_matches(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build_c_replacement.py")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        report = json.loads((ROOT / "build" / "replacement_report.json").read_text(encoding="utf-8"))
        self.assertTrue(all(x["ok"] for x in report), report)
        self.assertTrue((ROOT / "build" / "replacements" / "init.bin").is_file())
        self.assertTrue((ROOT / "build" / "replacements" / "talk_party_no.bin").is_file())
        self.assertTrue((ROOT / "build" / "replacements" / "talk_party_page.bin").is_file())
        self.assertTrue((ROOT / "build" / "replacements" / "talk_party_yes.bin").is_file())

    def test_full_build_uses_replacement_and_matches(self):
        r = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "build.py")],
            capture_output=True,
            text=True,
            cwd=str(ROOT),
        )
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn("Using compiled C replacement", r.stdout)
        code = (ROOT / "build" / "code.bin").read_bytes()
        self.assertEqual(
            hashlib.sha256(code).hexdigest(),
            "dfcd1b7ad170eab3932abfaa702b694e6673dc0a8744bfc070765cc8c8cc24d8",
        )


if __name__ == "__main__":
    unittest.main()


