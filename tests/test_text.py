"""Tests for tools/text_tool.py - the game text bank dump/rebuild path.

The core promise of the text editor is that text which was not edited comes
back byte for byte, so these tests re-encode every string of every bank and
compare the rebuilt BXON with the retail file.
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools import text_tool as tt  # noqa: E402


class TagCodecTest(unittest.TestCase):
    def test_every_control_code_round_trips(self):
        cases = [
            ("plain text", "plain text"),
            ("{literal}", "{{literal}}"),
            ("\x01使\x02つか\x03う", "{ruby:使|つか}う"),
            ("\x04\x01は", "{PLAYER}は"),
            ("\x04\x02", "{NAME}"),
            ("\x04\x03", "{TARGET}"),
            ("\x04\x04", "{PARTY3}"),
            ("\x04\x05", "{ITEM}"),
            ("\x04\x06", "{ITEM2}"),
            ("\x04\x07", "{ITEM3}"),
            ("\x04\x08", "{NUMBER}"),
            ("\x04\x0F", "{NUMBER8}"),
            ("\x04\x20", "{v:20}"),
            ("\x04\x66note\x04\x64", "{FMT:66}note{FMT:64}"),
            ("line\r\nnext", "line{CR}\nnext"),
            ("page\x1fbreak", "page{PAGE}break"),
            ("tab\there", "tab{c09}here"),
        ]
        for raw, tagged in cases:
            with self.subTest(raw=raw):
                self.assertEqual(tt.game_string(raw), tagged)
                self.assertEqual(tt.game_raw(tagged), raw)
                tt.check_codec(raw)

    def test_unknown_tag_is_refused(self):
        # A typo in a tag must be an error, never silently become text.
        with self.assertRaises(ValueError):
            tt.game_raw("hello {BOGUS} world")
        with self.assertRaises(ValueError):
            tt.game_raw("{FMT:01}")

    def test_literal_braces_are_escaped(self):
        self.assertEqual(tt.game_raw("{{PLAYER}}"), "{PLAYER}")


class BankTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.banks = tt.all_banks()
        cls.npc = tt.import_bank("param/region/r001/npc_ie")
        cls.shop = tt.import_bank("ui/common_3d/shop_msg")

    def test_all_banks_rebuild_byte_identically(self):
        self.assertGreater(len(self.banks), 700)
        failures = []
        strings = 0
        for bank in self.banks:
            bank.load()
            strings += len(bank.entries)
            rebuilt = tt.rebuild_bank(
                bank.data, {e.offset: e.text for e in bank.entries})
            if rebuilt != bank.data:
                failures.append(bank.key)
        self.assertEqual(failures, [], f"{len(failures)} bank(s) did not round-trip")
        self.assertGreater(strings, 60_000)

    def test_npc_bank_keeps_speaker_and_talk_location(self):
        entry = next(e for e in self.npc.entries if e.offset == 0x19FC)
        self.assertEqual(entry.role, "text")
        self.assertEqual(entry.speaker, "ダン")
        self.assertEqual(entry.location, "talk[15]/variant[0]/line[0]")
        self.assertTrue(entry.text.startswith("「{PLAYER}と"))
        # the speaker's own name string is editable too
        speaker = next(e for e in self.npc.entries if e.offset == 0x19F0)
        self.assertEqual(speaker.role, "speaker")
        self.assertEqual(speaker.text, "ダン")

    def test_nested_message_banks_find_their_text(self):
        # shop_msg stores each message in a small nested record; before the
        # structural walk this bank had no locations at all.
        located = [e for e in self.shop.entries if not e.location.startswith("text@")]
        self.assertEqual(len(located), len(self.shop.entries))
        self.assertTrue(any(e.location == "row[0].1[2]" for e in located))
        self.assertTrue(any("{ITEM}" in e.text for e in self.shop.entries))

    def test_json_export_import_round_trip(self):
        doc = self.npc.as_json()
        for key in ("bank", "pack", "member", "kind", "category", "font",
                    "box_width", "box_lines", "entries"):
            self.assertIn(key, doc)
        self.assertEqual(doc["font"], "3D14")
        self.assertEqual(doc["box_width"], 321)
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "npc_ie.json"
            path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
            loaded = tt.read_bank_json(path)
            texts = tt.texts_from_json(loaded, self.npc)
            self.assertEqual(tt.rebuild_bank(self.npc.data, texts), self.npc.data)

    def test_longer_npc_line_repaints_its_pointer(self):
        # A grown talk line must be re-pointed from the 28-byte line record;
        # this is the check that the trusted-pointer filter is doing its job.
        texts = {e.offset: e.text for e in self.npc.entries}
        target = next(e for e in self.npc.entries
                      if e.role == "text" and e.location == "talk[15]/variant[0]/line[1]")
        longer = target.text + "（追加）"
        texts[target.offset] = longer
        built = tt.rebuild_bank(self.npc.data, texts)
        self.assertGreater(len(built), len(self.npc.data))
        again = tt.extract_entries(built, self.npc.kind)
        hit = next(e for e in again
                   if e.role == "text" and e.location == "talk[15]/variant[0]/line[1]")
        self.assertEqual(hit.text, longer)
        self.assertEqual(hit.speaker, "ダン")

    def test_longer_text_is_relocated_and_readable(self):
        texts = {e.offset: e.text for e in self.shop.entries}
        target = next(e for e in self.shop.entries
                      if e.role == "text" and e.location == "row[0].1[2]")
        longer = "{ITEM} welcome, traveller! " * 3
        texts[target.offset] = longer
        built = tt.rebuild_bank(self.shop.data, texts)
        self.assertGreater(len(built), len(self.shop.data))
        again = tt.extract_entries(built, self.shop.kind)
        self.assertTrue(any(e.text == longer for e in again))
        # no other *referenced* string changed meaning
        old = {e.offset: e.text for e in self.shop.entries}
        for entry in again:
            if entry.offset in old and entry.text != longer:
                self.assertEqual(entry.text, old[entry.offset])

    def test_missing_offsets_are_refused(self):
        doc = self.shop.as_json()
        doc["entries"].pop()
        with self.assertRaises(SystemExit):
            tt.texts_from_json(doc, self.shop)


if __name__ == "__main__":
    unittest.main()
