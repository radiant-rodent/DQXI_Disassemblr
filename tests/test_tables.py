"""Round-trip and schema checks for the BXON parameter tables.

These are the Python twin of the Rust tests in `viewer_rs/src/data/tables.rs`:

* every table in ``game_assets/tables`` must load and save with the same bytes;
* every field named in ``tools/table_schemas.json`` must rewrite its own value
  byte-identically, so an unmodified Save can never move a byte;
* a real edit must re-parse to the new value and stay the same size;
* the declared ranges must hold for every record of every named table.

Run with ``python -m unittest tests.test_tables -v`` (the tier runner
``tests/run_all.py`` only runs the tier folders).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools.table_edit import Schemas, Table  # noqa: E402

TABLES = PROJECT_ROOT / "game_assets" / "tables" / "packs"
SOURCES = PROJECT_ROOT / "game_data" / "packs"


def table_names() -> list[str]:
    """Every converted table, as the path the schema file uses."""
    return sorted(
        path.relative_to(TABLES).with_suffix(".json").as_posix()
        for path in TABLES.rglob("*.json")
    )


class TableRoundTripTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schemas = Schemas()
        cls.names = table_names()
        cls._cache: dict[str, Table] = {}

    def table(self, rel: str) -> Table:
        if rel not in self._cache:
            self._cache[rel] = Table(rel)
        return self._cache[rel]

    def test_every_table_loads_and_saves_byte_identically(self):
        """Load -> save with no edit is a byte-for-byte copy, for all 5,929 tables."""
        self.assertGreater(len(self.names), 5000, "the table library is not extracted")
        checked = 0
        for rel in self.names:
            source = SOURCES / Path(rel).with_suffix(".bxon")
            if not source.is_file():
                continue
            original = source.read_bytes()
            table = Table(rel)
            self.assertEqual(bytes(table.raw), original, f"{rel}: a clean load changed the file")
            if len(table):
                self.assertGreater(table.row_size, 0, rel)
                self.assertLessEqual(
                    table.rows[-1] + table.row_size,
                    len(table.raw),
                    f"{rel}: the last row runs past the end of the file",
                )
                self.assertEqual(
                    table.rows[-1] + table.row_size - table.rows[0],
                    table.row_size * len(table),
                    f"{rel}: rows are not evenly spaced",
                )
                # Exercise the same word writer the grid uses, then put the word
                # back: every table must survive a load/edit/revert cycle.
                for offset in range(0, min(table.row_size, 32) - 3, 4):
                    probe = {"name": "probe", "offset": offset, "type": "u32"}
                    value = table.read(0, probe)
                    table.write(0, probe, value ^ 1)
                    table.write(0, probe, value)
                self.assertEqual(
                    bytes(table.raw), original, f"{rel}: a write/restore cycle changed the file"
                )
            checked += 1
        self.assertGreater(checked, 5000, f"only {checked} tables had a source BXON")

    def test_every_named_field_rewrites_byte_identically(self):
        """Saving an unmodified named table must not move a single byte."""
        named = 0
        writes = 0
        for rel in self.names:
            if not self.schemas.get(rel):
                continue
            table = Table(rel)
            before = bytes(table.raw)
            for row in range(len(table)):
                for field in table.fields():
                    if field["type"] == "string":
                        continue
                    value = table.read(row, field)
                    table.write(row, field, value)
                    writes += 1
            self.assertEqual(bytes(table.raw), before, f"{rel}: rewrite changed the file")
            named += 1
        self.assertGreaterEqual(named, 40, f"only {named} tables have field names")
        self.assertGreater(writes, 200_000, f"only {writes} scalar writes were checked")

    def test_a_modified_value_reparses_to_the_new_value(self):
        table = Table("syscmn/item.json")
        original = bytes(table.raw)
        self.assertEqual(table.value(0, "buy_price"), 8)
        self.assertEqual(table.value(0, "sell_price"), 4)
        size = len(table.raw)

        table.set(0, "buy_price", "5")
        self.assertEqual(table.value(0, "buy_price"), 5)
        self.assertEqual(len(table.raw), size, "a table edit must not resize the file")

        # Re-parse the saved bytes, exactly like the game would.
        saved = Table("syscmn/item.json", bytes(table.raw))
        self.assertEqual(saved.value(0, "buy_price"), 5)
        self.assertEqual(saved.value(0, "sell_price"), 4)
        changed = [
            i
            for i, (before, after) in enumerate(zip(original, bytes(saved.raw)))
            if before != after
        ]
        self.assertEqual(changed, [saved.address(0, saved.field("buy_price"))])

        # The validator, not silent wrapping, rejects what the field cannot hold.
        with self.assertRaises(SystemExit):
            table.set(0, "buy_price", "999999999")
        with self.assertRaises(SystemExit):
            table.set(0, "buy_price", "not a number")

    def test_declared_ranges_hold_for_every_record(self):
        """A schema range that no longer matches the data is a bug, not a hint."""
        checked = 0
        for rel in self.names:
            spec = self.schemas.get(rel)
            if not spec:
                continue
            table = self.table(rel)
            for field in table.fields():
                span = field.get("range")
                if not span:
                    continue
                low, high = span
                for row in range(len(table)):
                    value = table.read(row, field)
                    self.assertGreaterEqual(
                        value, low, f"{rel} row {row} {field['name']} = {value} < {low}"
                    )
                    self.assertLessEqual(
                        value, high, f"{rel} row {row} {field['name']} = {value} > {high}"
                    )
                    checked += 1
        self.assertGreater(checked, 100_000, f"only {checked} range checks ran")

    def test_equipment_stats_are_named(self):
        table = self.table("syscmn/item.json")
        by_name: dict[str, int] = {}
        for row in range(len(table)):
            by_name.setdefault(table.read(row, table.field("name")).replace("\n", ""), row)
        iron = by_name["てつのつるぎ"]
        self.assertEqual(table.value(iron, "attack"), 20)
        self.assertEqual(table.value(iron, "upgrade_level"), 0)
        leather = by_name["皮のよろい"]
        self.assertEqual(table.value(leather, "defence"), 11)
        self.assertEqual(table.value(leather, "upgrade_level"), 0)

    def test_encounter_slots_are_real_monster_ids(self):
        table = self.table("gamecmn/encount_table.json")
        enemies = self.table("gamecmn/enemy_base.json")
        self.assertEqual(len(table), 3545)
        self.assertEqual(table.value(0, "monster_01"), 3, "row 0 slot 1 is the Slime")
        filled = 0
        for row in range(len(table)):
            for slot in range(1, 12):
                monster = table.value(row, f"monster_{slot:02d}")
                if monster == 65535:
                    continue
                self.assertLess(monster, len(enemies), f"row {row} slot {slot}: {monster}")
                self.assertLessEqual(table.value(row, f"level_{slot:02d}"), 8)
                self.assertLessEqual(table.value(row, f"count_{slot:02d}"), 8)
                filled += 1
        self.assertGreater(filled, 5000, f"only {filled} encounter slots are filled")

    def test_passive_skill_rows_describe_their_effect(self):
        table = self.table("gamecmn/passive_skill.json")
        self.assertIn("みのまもり", table.value(0, "name"))
        self.assertEqual(table.value(0, "effect_id"), 3, "3 = defence")
        self.assertEqual(table.value(0, "effect_value"), 10)
        self.assertEqual(table.value(1, "effect_id"), 2, "2 = strength")
        self.assertEqual(table.value(1, "effect_value"), 15)

    def test_skill_name_table_has_real_names(self):
        table = self.table("gamecmn/battle_act_text.json")
        self.assertEqual(table.value(0, "name"), "かえん斬り")
        self.assertEqual(table.value(1, "name"), "メタル斬り")


if __name__ == "__main__":
    unittest.main()
