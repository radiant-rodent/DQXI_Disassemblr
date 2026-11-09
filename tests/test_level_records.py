#!/usr/bin/env python3
"""Regression tests for adding / duplicating / deleting level records (tools/level_records.py).

The invariants: a duplicate appends one object and a delete removes one, nothing that was in the
file changes except the rewritten array descriptor, the transforms written for a new record land in
that record, and a project's float edits and structural ops agree.
"""
from __future__ import annotations

import unittest

from tests.common import PROJECT_ROOT
from tools import level_records as lr
from tools.bxon_struct import StructDecoder
from tools.map_tool import candidate_objects

LEVELS = PROJECT_ROOT / "game_data" / "packs" / "level3d"


def _raw(level: str) -> bytes | None:
    path = LEVELS / level / "level3d.bxon"
    return path.read_bytes() if path.is_file() else None


def _objects(raw: bytes) -> list[dict]:
    return candidate_objects(StructDecoder(raw).decode(), raw)


class LevelRecordTests(unittest.TestCase):
    def setUp(self):
        self.raw = _raw("b001_102c")
        if self.raw is None:
            self.skipTest("game_data/packs/level3d is not extracted")

    def test_duplicate_a_transform_adds_exactly_one_object(self):
        before = _objects(self.raw)
        new, _ = lr.apply_ops(self.raw, [{"op": "duplicate", "offset": "0x928"}])
        self.assertEqual(len(_objects(new)), len(before) + 1)
        # the old bytes are untouched apart from the rewritten array descriptor
        changed = [i for i in range(len(self.raw)) if self.raw[i] != new[i]]
        self.assertLessEqual(len(changed), 8)

    def test_duplicate_a_placement_copies_its_wrapper(self):
        before = _objects(self.raw)
        new, _ = lr.apply_ops(self.raw, [{"op": "duplicate", "offset": "0x5B8"}])
        self.assertEqual(len(_objects(new)), len(before) + 1)

    def test_delete_removes_one_object_and_keeps_the_rest(self):
        before = _objects(self.raw)
        new, _ = lr.apply_ops(self.raw, [{"op": "delete", "offset": "0x928"}])
        after = _objects(new)
        self.assertEqual(len(after), len(before) - 1)
        def key(o):
            return (o["shape"], tuple(round(v, 4) for v in o["position"]), tuple(round(v, 4) for v in o["scale"]))
        remaining = sorted(key(o) for o in after)
        original = sorted(key(o) for o in before)
        for k in remaining:
            original.remove(k)  # every remaining object existed before
        self.assertEqual(len(original), 1)

    def test_the_new_record_gets_the_requested_transform(self):
        want = {"position": [5.0, 1.0, 2.0], "scale": [2.0, 2.0, 2.0], "rotation": [0.0, 1.5, 0.0]}
        new, _ = lr.apply_ops(self.raw, [{"op": "duplicate", "offset": "0x928", "shape": 120, "set": want}])
        last = max((o for o in _objects(new) if o["shape"] == 120), key=lambda o: int(o["record_offset"], 16))
        self.assertEqual([round(v, 3) for v in last["position"]], want["position"])
        self.assertEqual([round(v, 3) for v in last["scale"]], want["scale"])
        self.assertEqual([round(v, 3) for v in last["rotation"]], want["rotation"])

    def test_two_duplicates_each_get_their_own_transform_and_the_originals_stay_put(self):
        before = _objects(self.raw)
        a = {"position": [0.75, 0.5, 0.5], "scale": [1.5, 3.0, 1.0], "rotation": [0.0, 0.0, 0.0]}
        b = {"position": [2.25, 0.5, 0.5], "scale": [1.5, 3.0, 1.0], "rotation": [0.0, 0.0, 0.0]}
        new, _ = lr.apply_ops(self.raw, [
            {"op": "duplicate", "offset": "0x928", "shape": 120, "set": a},
            {"op": "duplicate", "offset": "0x928", "shape": 120, "set": b},
        ])
        after = _objects(new)
        self.assertEqual(len(after), len(before) + 2)
        def positions(objs):
            return sorted(tuple(round(v, 3) for v in o["position"]) for o in objs if o["shape"] == 120)
        expected = sorted(positions(before) + [tuple(a["position"]), tuple(b["position"])])
        self.assertEqual(positions(after), expected)

    def test_operations_address_records_by_their_original_offset(self):
        before = _objects(self.raw)
        new, _ = lr.apply_ops(self.raw, [
            {"op": "duplicate", "offset": "0x928"},
            {"op": "duplicate", "offset": "0x928"},
            {"op": "delete", "offset": "0x928"},
        ])
        self.assertEqual(len(_objects(new)), len(before) + 1)

    def test_the_last_element_of_an_array_cannot_be_deleted(self):
        with self.assertRaises(lr.RecordError):
            lr.apply_ops(self.raw, [{"op": "delete", "offset": "0x5B8"}])

    def test_shared_blocks_do_not_trip_the_verification(self):
        raw = _raw("x002_001a")
        if raw is None:
            self.skipTest("level x002_001a not extracted")
        new, _ = lr.apply_ops(raw, [{"op": "duplicate", "offset": "0xA48"}])
        self.assertGreater(len(new), len(raw))


if __name__ == "__main__":
    unittest.main()
