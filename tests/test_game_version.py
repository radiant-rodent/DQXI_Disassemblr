"""Tests for tools/game_version.py and tools/code_edit.py (retail / patched game versions).

The fast tests need no imported version. The ones that check the imported English version are
skipped when versions/en is missing (run `python -m tools.game_version import en` first).
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import build  # noqa: E402
from tools import code_edit  # noqa: E402
from tools import game_version as gv  # noqa: E402


def _varint(v: int) -> bytes:
    out = bytearray()
    while v >= 0x80:
        out.append(v & 0x7F | 0x80)
        v >>= 7
    out.append(v)
    return bytes(out)


class DeltaTest(unittest.TestCase):
    def test_copy_and_insert_ops(self):
        src = b"0123456789abcdef"
        # copy 4 bytes from 0, insert "XY", copy 3 bytes from 10 (zigzag offset +6 from prev end 4)
        ops = _varint(4 << 1) + _varint(0) + _varint(2 << 1 | 1) + b"XY" + _varint(3 << 1) + _varint(6 << 1)
        self.assertEqual(gv._apply_delta(src, ops, 9), b"0123XYabc")

    def test_runs_merge_close_changes(self):
        a = bytes(64)
        b = bytearray(a)
        b[3] = 1
        b[8] = 1          # 5 bytes later: same run
        b[40] = 1         # far away: own run
        self.assertEqual(gv._runs(a, bytes(b)), [(3, 9), (40, 41)])


class PadSourceTest(unittest.TestCase):
    def test_pad_listing_assembles_back_bit_exact(self):
        blob = bytes.fromhex("04e02de5" "00f020e3" "00000000" "1eff2fe1") + bytes(8)
        text = gv.pad_source("text", 0x0072403C, blob)
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "text_tail.s"
            path.write_text(text, encoding="utf-8")
            self.assertEqual(build.assemble_file(path, 0x0072403C), blob)


class AssembleTest(unittest.TestCase):
    def test_listing_columns_and_comments_are_ignored(self):
        text = ("; header comment\n"
                "00724A00  200058e3  cmp r8, #0x20\n"
                "    bl #0x724a00   @ absolute target\n"
                ".word 0x12345678\n")
        out = code_edit.assemble(text, 0x00724A00, "arm")
        self.assertEqual(out[:4], bytes.fromhex("200058e3"))
        self.assertEqual(out[4:8], bytes.fromhex("fdffffeb"))   # bl to itself - 4
        self.assertEqual(out[8:], bytes.fromhex("78563412"))


@unittest.skipUnless((gv.VERSIONS / "en" / "version.json").is_file(), "English version not imported")
class ImportedEnglishTest(unittest.TestCase):
    def test_code_changes_describe_the_patch(self):
        ch = gv.code_changes("en")
        self.assertTrue(ch["functions"])
        self.assertTrue(any(c["name"].startswith("EN_wordwrap") for c in ch["caves"]))
        code = gv.code_path("en").read_bytes()
        retail = gv.RETAIL_CODE.read_bytes()
        for f in ch["functions"]:
            off = f["address"] - gv.BASE
            size = max(f["size"], 4)
            self.assertNotEqual(code[off:off + size], retail[off:off + size], f["name"])

    def test_english_text_banks_hold_no_dead_japanese(self):
        """The patch leaves the replaced Japanese strings in the files; the banks must skip them."""
        import json
        import re
        kana = re.compile("[぀-ヿ]")
        m = gv.load_manifest("en")
        total = japanese = 0
        for rel, digest in m["files"].items():
            if rel.startswith("game_assets/text/banks/") and digest:
                for e in json.loads(gv.blob_path(digest).read_text(encoding="utf-8"))["entries"]:
                    total += 1
                    japanese += bool(kana.search(e["text"] or ""))
        self.assertGreater(total, 1000)
        self.assertLess(japanese, 20, f"{japanese} of {total} lines are Japanese")

    def test_manifest_blobs_exist(self):
        for name in ("original", "en"):
            for rel, digest in gv.load_manifest(name)["files"].items():
                if digest:
                    self.assertTrue(gv.blob_path(digest).is_file(), f"{name}: {rel}")


if __name__ == "__main__":
    unittest.main()
