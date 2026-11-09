#!/usr/bin/env python3
"""Regression tests for grown/added content (X5).

Every case here is about *size*: a PACK member that gets bigger, a BXON row
array with one more record (appended or inserted mid-table), a text string that
no longer fits its slot, a new RomFS path, a bigger texture and a longer audio
stream.  The invariant is always the same:

* unchanged input must rebuild byte-identically (no accidental normalisation),
* grown input must parse back with the old records intact and the new data
  present, and the container/hash layers must be consistent.

The RomFS cases use the small synthetic image helper from
``tests/test_asset_roundtrip.py`` instead of copying the 2.7 GB retail image, so
the whole module runs in a few seconds.  The real-image proof lives in the
tier-4 mod-export scenario and in the opt-in emulator cases.
"""
from __future__ import annotations

import struct
import tempfile
import unittest
from pathlib import Path

from tests.common import PROJECT_ROOT
from tests.test_asset_roundtrip import _read_test_romfs, _write_test_romfs

from tools import bxon_grow, pack, romfs_build, romfs_hash, text_tool
from tools.export_mod import RomFsIndex
from tools.patch_asset import rebuild_pack
from tools.table_edit import Table

PACKS = PROJECT_ROOT / "game_data" / "romfs"
PACK_DATA = PROJECT_ROOT / "game_data" / "packs"


def _skip_without(path: Path, what: str) -> None:
    if not path.is_file():
        raise unittest.SkipTest(f"{what} not extracted ({path})")


class PackGrowthTests(unittest.TestCase):
    # A small uncompressed PACK with two members (BCH + ANI).
    UNCOMPRESSED = PACKS / "2d/battle2/bg/bg.pack"

    def test_unchanged_pack_round_trips_byte_identically(self):
        src = self.UNCOMPRESSED
        _skip_without(src, "bg.pack")
        raw = src.read_bytes()
        p = pack.Pack.parse(raw)
        self.assertEqual(p.build(), raw)
        self.assertFalse(p.compressed)

    def test_unchanged_paca_round_trips_byte_identically(self):
        # A recompressed BLZ stream is not byte-identical to the original, so an
        # unchanged PACA must return the original file, not an encoder output.
        src = PACKS / "syscmn.pack"
        _skip_without(src, "syscmn.pack")
        raw = src.read_bytes()
        p = pack.Pack.parse(raw)
        self.assertTrue(p.compressed)
        self.assertEqual(p.build(), raw)

    def test_grown_member_is_preserved_and_other_members_are_untouched(self):
        src = self.UNCOMPRESSED
        _skip_without(src, "bg.pack")
        original = pack.Pack.parse(src.read_bytes())
        target = original.entries[0]
        grown = target.data + b"X5-GROWN" * 37
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            replacement = td / target.name
            replacement.write_bytes(grown)
            out = td / "grown.pack"
            built = rebuild_pack(src, target.name, replacement, out)
        after = pack.Pack.parse(built)
        self.assertGreater(len(built), len(src.read_bytes()))
        self.assertEqual(len(after.entries), len(original.entries))
        for old, new in zip(original.entries, after.entries):
            self.assertEqual(old.name, new.name)
            if old.name == target.name:
                self.assertEqual(new.data, grown)
            else:
                self.assertEqual(new.data, old.data)

    def test_grown_member_inside_paca_preserves_every_member(self):
        src = PACKS / "syscmn.pack"
        _skip_without(src, "syscmn.pack")
        original = pack.Pack.parse(src.read_bytes())
        item = next(e for e in original.entries if e.name == "item.bxon")
        # Make it unambiguously larger even after BLZ recompression.
        grown = item.data + bytes(range(256)) * 128
        with tempfile.TemporaryDirectory() as td:
            td = Path(td)
            replacement = td / "item.bxon"
            replacement.write_bytes(grown)
            built = rebuild_pack(src, "item.bxon", replacement, td / "syscmn.pack")
            self.assertTrue(built.startswith(b"PACA"))
            self.assertGreater(len(built), len(src.read_bytes()))
            after = pack.Pack.parse(built)
        self.assertTrue(after.compressed)
        self.assertEqual(next(e.data for e in after.entries if e.name == "item.bxon"), grown)
        for old, new in zip(original.entries, after.entries):
            if old.name != "item.bxon":
                self.assertEqual(old.data, new.data, old.name)


class BxonGrowthTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.item_path = PACK_DATA / "syscmn" / "item.bxon"
        _skip_without(cls.item_path, "item.bxon")
        cls.item = cls.item_path.read_bytes()
        cls.row_size, cls.pointers = bxon_grow.pointer_offsets_from_schema(
            "syscmn/item.json")
        cls.rows = len(Table("syscmn/item.json", cls.item))

    def test_append_keeps_every_retail_row(self):
        grown = bxon_grow.grow_table(self.item, self.row_size, self.pointers,
                                     rows=1, source_row=0, at=-1)
        table = Table("syscmn/item.json", grown)
        self.assertEqual(len(table), self.rows + 1)
        retail = Table("syscmn/item.json", self.item)
        for row in range(self.rows):
            for field in ("name", "buy_price", "attack", "defence"):
                spec = retail.field(field)
                self.assertEqual(table.read(row, spec), retail.read(row, spec),
                                 f"row {row} field {field}")
        # the appended row is a copy of the herb
        self.assertEqual(table.read(self.rows, table.field("name")), "やくそう")

    def test_insert_moves_rows_without_changing_their_values(self):
        at = 164
        grown = bxon_grow.grow_table(self.item, self.row_size, self.pointers,
                                     rows=1, source_row=0, at=at)
        table = Table("syscmn/item.json", grown)
        retail = Table("syscmn/item.json", self.item)
        self.assertEqual(len(table), self.rows + 1)
        self.assertEqual(table.read(at, table.field("name")), "やくそう")
        for row in range(self.rows):
            new_row = row if row < at else row + 1
            for field in ("name", "buy_price", "id"):
                spec = retail.field(field)
                self.assertEqual(table.read(new_row, spec), retail.read(row, spec),
                                 f"retail row {row} moved to {new_row}, field {field}")

    def test_insert_position_is_validated(self):
        with self.assertRaises(ValueError):
            bxon_grow.grow_table(self.item, self.row_size, self.pointers, at=self.rows + 1)
        with self.assertRaises(ValueError):
            bxon_grow.grow_table(self.item, self.row_size, self.pointers, at=-2)

    def test_claimed_placeholder_row_keeps_the_row_count(self):
        retail = Table("syscmn/item.json", self.item)
        # 2690 is an id-0 placeholder in the retail table.
        claimed = bxon_grow.claim_placeholder(self.item, self.row_size, self.pointers,
                                              source_row=0, dest_row=2690,
                                              id_offset=retail.field("id")["offset"],
                                              new_id=2700)
        self.assertEqual(len(Table("syscmn/item.json", claimed)), self.rows)
        table = Table("syscmn/item.json", claimed)
        self.assertEqual(table.read(2690, table.field("id")), 2700)
        self.assertEqual(table.read(2690, table.field("name")), "やくそう")
        # an occupied row must be refused
        with self.assertRaises(ValueError):
            bxon_grow.claim_placeholder(self.item, self.row_size, self.pointers,
                                        source_row=0, dest_row=0,
                                        id_offset=retail.field("id")["offset"],
                                        new_id=2700)


class TextGrowthTests(unittest.TestCase):
    def test_longer_string_relocates_and_still_parses(self):
        bank = text_tool.import_bank("ui/common_2d/mainmenu_msg")
        entry = min(bank.entries, key=lambda e: len(e.text))
        marker = entry.text + "X5-GROWN-" + "A" * 40
        grown = text_tool.rebuild_bank(bank.data, {entry.offset: marker})
        self.assertGreater(len(grown), len(bank.data))
        from tools.bxon import Bxon

        parsed = Bxon.parse(grown)
        self.assertFalse(parsed.skipped)
        self.assertTrue(any("X5-GROWN-" in s.text for s in parsed.strings))
        # an empty edit is a byte-identical no-op
        self.assertEqual(text_tool.rebuild_bank(bank.data, {}), bank.data)


class RomFsGrowthTests(unittest.TestCase):
    def test_new_top_level_directory_and_files_are_reachable(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "romfs.bin"
            _write_test_romfs(image, [("retail.bin", b"RETAIL" * 100)])
            additions = [
                ("/new.bin", b"NEW" * 50),
                ("/dir/nested.bin", b"NEST"),
                ("/dir/two.bin", b"TWO"),
                ("/other/x.bin", b"X"),
            ]
            rep = romfs_build.rebuild_metadata(image, additions)
            self.assertEqual(len(rep["placements"]), len(additions))
            self.assertTrue(romfs_hash.verify(image)["ok"])
            index = RomFsIndex(image)
            self.assertEqual(index.read("/retail.bin"), b"RETAIL" * 100)
            for path, data in additions:
                self.assertIn(path, index.files)
                self.assertEqual(index.read(path), data)
            # the file data is behind the retail data, not overwriting it
            retail = _read_test_romfs(image)["retail.bin"]
            self.assertEqual(retail[1], b"RETAIL" * 100)

    def test_unchanged_synthetic_image_is_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            image = Path(td) / "romfs.bin"
            _write_test_romfs(image, [("retail.bin", b"RETAIL" * 100)])
            before = image.read_bytes()
            rep = romfs_build.rebuild_metadata(image, [])
            self.assertEqual(rep["placements"], [])
            self.assertEqual(image.read_bytes(), before)
            self.assertTrue(romfs_hash.verify(image)["ok"])


class ImageGrowthTests(unittest.TestCase):
    def test_texture_can_be_encoded_at_a_new_size(self):
        from PIL import Image

        from tools import texture_tool

        sample = next((PROJECT_ROOT / "game_data/arcs").rglob("*.bflim"), None)
        if sample is None:
            self.skipTest("no BFLIM extracted")
        original = sample.read_bytes()
        info = texture_tool.bflim_info(original)
        rgba, _ = texture_tool.decode_bflim(original)
        bigger = Image.fromarray(rgba, "RGBA").resize(
            (info["width"] * 2, info["height"] * 2), Image.Resampling.NEAREST)
        import numpy as np

        rebuilt = texture_tool.encode_bflim(np.asarray(bigger, dtype=np.uint8),
                                            dict(info, width=bigger.width,
                                                 height=bigger.height),
                                            footer_template=original)
        new_info = texture_tool.bflim_info(rebuilt)
        self.assertEqual((new_info["width"], new_info["height"]),
                         (info["width"] * 2, info["height"] * 2))
        new_rgba, _ = texture_tool.decode_bflim(rebuilt)
        self.assertEqual(new_rgba.shape[:2], (bigger.height, bigger.width))
        self.assertGreater(len(rebuilt), len(original))

    def test_audio_stream_can_change_length(self):
        import numpy as np

        from tools import audio_tool
        from tools.bcstm_encode import build_bcstm_dsp

        sample = PROJECT_ROOT / "game_data/romfs/sound/str/muon.dspadpcm.bcstm"
        _skip_without(sample, "a BCSTM")
        template = sample.read_bytes()
        info, _ = audio_tool.parse_bcstm_info(template)
        self.assertEqual(info.channels, 1)
        # 0.2 s of a quiet tone: a different sample count from the retail stream.
        samples = 1600
        pcm = (np.sin(np.arange(samples) * 0.05) * 3000).astype(np.int16)
        rebuilt = build_bcstm_dsp(template, pcm, info.sample_rate, info.channels)
        new_info, _ = audio_tool.parse_bcstm_info(rebuilt)
        self.assertEqual(new_info.total_samples, samples)
        decoded, rate, channels = audio_tool.decode_bcstm(rebuilt)
        self.assertEqual((rate, channels), (info.sample_rate, info.channels))
        # decode_bcstm returns interleaved PCM16 bytes
        self.assertEqual(len(decoded), samples * channels * 2)


if __name__ == "__main__":
    unittest.main()
