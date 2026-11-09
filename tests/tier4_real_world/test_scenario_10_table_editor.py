"""Tier 4: Scenario 10 - the BXON table editor round trip.

Features exercised: the field schemas in `tools/table_schemas.json`, name-based
reading and writing in `tools/table_edit.py`, same-size byte patches, value
validation, reference integrity, and staging a patched table into the mod
workspace as its RomFS pack.

The round-trip rule under test is the one the DQXI Studio Table editor relies on:
**an unmodified table must save back byte-identically**, and a modified value must
re-parse to the new value. Every table that has field names is checked, not just
the item table.
"""

import json
import shutil
import struct
import tempfile
import unittest
from pathlib import Path

from tests.common import PROJECT_ROOT, TOOLS_DIR

import sys

sys.path.insert(0, str(PROJECT_ROOT))

from tools import table_edit

SCHEMAS = TOOLS_DIR / "table_schemas.json"
SOURCES = PROJECT_ROOT / "game_data" / "packs"
ROMFS = PROJECT_ROOT / "game_data" / "romfs"

# The families the task asked for: items/equipment, monsters, spells/skills,
# shops, party growth and the shared model lookup.
REQUIRED_TABLES = [
    "syscmn/item.json",
    "gamecmn/enemy_base.json",
    "gamecmn/enemy_battle.json",
    "gamecmn/spell.json",
    "fieldcmn/shop.json",
    "syscmn/player_param_hero.json",
    "gamecmn/password_exp_table.json",
    "gamecmn/res_model3d.json",
]


def named_tables() -> list[str]:
    schemas = table_edit.Schemas()
    return [t for t in table_edit.all_tables() if schemas.get(t)]


class TestTableEditorRoundTrip(unittest.TestCase):
    """Scenario 10: the table editor never corrupts a table."""

    @classmethod
    def setUpClass(cls):
        cls.schemas = table_edit.Schemas()
        cls.tables = named_tables()

    def test_every_required_family_has_a_schema(self):
        for table in REQUIRED_TABLES:
            with self.subTest(table=table):
                self.assertIsNotNone(self.schemas.get(table), f"{table} lost its field names")

    def test_schema_row_size_matches_the_file(self):
        """A schema that claims the wrong stride would write into the wrong row."""
        for table in self.tables:
            with self.subTest(table=table):
                doc = table_edit.Table(table)
                self.assertGreater(len(doc), 0, f"{table} decoded no rows")
                declared = doc.schema.get("row_size")
                self.assertEqual(declared, doc.row_size,
                                 f"{table}: schema says {declared} bytes per row, the file says {doc.row_size}")

    def test_every_named_field_round_trips_byte_identically(self):
        """Rewrite every named numeric field with its own value: no byte may move."""
        for table in self.tables:
            with self.subTest(table=table):
                doc = table_edit.Table(table)
                before = bytes(doc.raw)
                for row in range(len(doc)):
                    for field in doc.fields():
                        if field["type"] == "string":
                            continue
                        doc.write(row, field, doc.read(row, field))
                self.assertEqual(bytes(doc.raw), before,
                                 f"{table} changed when every field was rewritten with its own value")

    def test_a_modified_value_reparses_to_the_new_value(self):
        """A real write must land, keep the size and read back."""
        cases = [
            ("syscmn/item.json", 0, "buy_price", 5),
            ("syscmn/player_param_hero.json", 5, "exp_total", 1234),
            ("gamecmn/enemy_base.json", 0, "level", 7),
            ("fieldcmn/shop.json", 1, "item_01", 2332),
        ]
        for table, row, field_name, value in cases:
            with self.subTest(table=table, field=field_name):
                doc = table_edit.Table(table)
                field = doc.field(field_name)
                before = doc.read(row, field)
                self.assertNotEqual(before, value, "pick a value that differs from the original")
                doc.write(row, field, value)
                self.assertEqual(len(doc.raw), len(Table_size(table)))
                reread = table_edit.Table(table, bytes(doc.raw)).read(row, field)
                self.assertEqual(reread, value, f"{table}.{field_name} did not keep {value}")

    def test_editing_one_item_price_touches_one_word(self):
        """Same-size patching means exactly one 32-bit word changes."""
        doc = table_edit.Table("syscmn/item.json")
        field = doc.field("buy_price")
        before = bytes(doc.raw)
        position = doc.rows[0] + int(field["offset"])
        doc.write(0, field, 5)
        after = bytes(doc.raw)
        changed = [i for i in range(len(before)) if before[i] != after[i]]
        self.assertTrue(changed, "the edit did nothing")
        self.assertTrue(all(position <= i < position + 4 for i in changed),
                        f"bytes outside the price changed: {changed}")

    def test_validation_rejects_out_of_range_and_non_numbers(self):
        item = table_edit.Table("syscmn/item.json")
        price = item.field("buy_price")
        self.assertIsNotNone(table_edit.check_range(price, 9_999_999_999))
        self.assertIsNone(table_edit.check_range(price, 8))
        group = item.field("group")
        self.assertIsNotNone(table_edit.check_range(group, 300), "a u8 cannot hold 300")

    def test_reference_targets_exist_and_carry_an_id(self):
        """Every 'id - name' dropdown must point at a real table with an id field."""
        for table in self.tables:
            doc = table_edit.Table(table)
            for field in doc.fields():
                reference = field.get("ref")
                if not reference:
                    continue
                with self.subTest(table=table, field=field["name"], target=reference["table"]):
                    self.assertIn(reference["table"], self.tables,
                                  f"{table}.{field['name']} points at an unnamed table")
                    target = table_edit.Table(reference["table"])
                    self.assertIsNotNone(target.schema.get("id"),
                                         f"{reference['table']} has no id field to key on")
                    self.assertIsNotNone(target.schema.get("label"),
                                         f"{reference['table']} has no label field to show")

    def test_item_ids_match_the_shops_that_sell_them(self):
        """Cross-check two tables: shop slots must be real item ids."""
        items = table_edit.Table("syscmn/item.json")
        id_field = items.field("id")
        ids = {items.read(row, id_field) for row in range(len(items))}
        shops = table_edit.Table("fieldcmn/shop.json")
        slots = [f for f in shops.fields() if f["name"].startswith("item_")]
        total = 0
        hits = 0
        for row in range(len(shops)):
            for field in slots:
                value = shops.read(row, field)
                if value == 0xFFFF:
                    continue
                total += 1
                hits += value in ids
        self.assertGreater(total, 1000, "expected a large shop inventory")
        self.assertGreater(hits / total, 0.9,
                           f"only {hits}/{total} shop slots are item ids - the schemas disagree")

    def test_item_prices_are_sane(self):
        """buy_price and sell_price must behave like a shop price and half of it."""
        items = table_edit.Table("syscmn/item.json")
        buy = items.field("buy_price")
        sell = items.field("sell_price")
        priced = 0
        half = 0
        for row in range(len(items)):
            b = items.read(row, buy)
            s = items.read(row, sell)
            self.assertLess(b, 2_000_000, f"row {row} buy price is implausible: {b}")
            if b and s:
                priced += 1
                half += s == b // 2
        self.assertGreater(priced, 500)
        self.assertGreater(half / priced, 0.6, f"only {half}/{priced} items sell for half")

    def test_level_curve_is_monotonic(self):
        curve = table_edit.Table("syscmn/player_param_hero.json")
        exp = curve.field("exp_total")
        values = [curve.read(row, exp) for row in range(len(curve))]
        self.assertEqual(len(values), 99)
        self.assertEqual(values, sorted(values))
        self.assertEqual(len(set(values)), 99, "every level must need more experience than the last")

    def test_unnamed_tables_stay_editable(self):
        """Tables without field names must still open, and keep their size."""
        plain = "gamecmn/quest_param.json"
        self.assertIsNone(self.schemas.get(plain))
        doc = table_edit.Table(plain)
        self.assertGreater(len(doc), 0)
        before = bytes(doc.raw)
        # write a word at the start of row 0 and put it back
        word = struct.unpack_from("<I", doc.raw, doc.rows[0])[0]
        struct.pack_into("<I", doc.raw, doc.rows[0], word ^ 0xFF)
        struct.pack_into("<I", doc.raw, doc.rows[0], word)
        self.assertEqual(bytes(doc.raw), before)

    def test_save_mod_stages_the_pack_into_the_mod_workspace(self):
        """An edited table must reach mod/romfs as its pack, never as a loose file."""
        from tools import export_mod, pack

        if not (ROMFS / "syscmn.pack").is_file():
            self.skipTest("game_data/romfs/syscmn.pack is not extracted")

        edited = table_edit.Table("syscmn/item.json")
        price = edited.field("buy_price")
        edited.write(0, price, 4321)
        tmp = Path(tempfile.mkdtemp(prefix="dqxi_table_mod_"))
        try:
            replacement = tmp / "item.bxon"
            replacement.write_bytes(bytes(edited.raw))
            info = export_mod.stage_member(
                "syscmn.pack", "item.bxon", replacement, tmp / "mod", work_dir=tmp / "work")
            self.assertTrue(info["mod_file"].endswith("syscmn.pack"))
            self.assertFalse((tmp / "mod" / "romfs" / "item.bxon").exists(),
                             "a loose table must never appear in mod/romfs")
            parsed = pack.Pack.parse(Path(info["mod_file"]).read_bytes())
            member = next(e for e in parsed.entries if e.name == "item.bxon")
            self.assertEqual(struct.unpack_from("<I", member.data, 0x2C + 0x18)[0], 4321,
                             "the staged pack does not carry the edited price")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    def test_stride_decoder_agrees_with_the_structural_export(self):
        """The editor derives rows from the BXON header; the JSON export says the same."""
        structural = (PROJECT_ROOT / "game_assets" / "tables" / "packs" / "syscmn" / "item.json")
        if not structural.is_file():
            self.skipTest("structural table JSON is not generated")
        exported = json.loads(structural.read_text(encoding="utf-8"))["root"]
        doc = table_edit.Table("syscmn/item.json")
        self.assertEqual(len(doc), len(exported))
        self.assertEqual(doc.row_size, exported[0]["$size"])
        for index in (0, 1, len(exported) // 2, len(exported) - 1):
            self.assertEqual(doc.rows[index], int(exported[index]["$offset"], 16))


def Table_size(table: str) -> bytes:
    """The original bytes of a table, for the size check above."""
    return (SOURCES / Path(table).with_suffix(".bxon")).read_bytes()


if __name__ == "__main__":
    unittest.main(verbosity=2)
