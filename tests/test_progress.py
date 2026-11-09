"""Unit tests for tools/progress.py type-recovery tracking and overview rendering.

Covers:
  * fake types tree with G_*, S_* and V_* worker answers plus malformed files;
  * separation between worker answers (named vs guessed/maybe_) and merged headers/maps;
  * batch completion counts (done = orchestration/done/<id>.md exists);
  * header fallback when orchestration/types/merged/*.json maps are absent;
  * overview HTML ("Data & types" card + stacked bars + badge-types.svg) and
    history.jsonl / history.svg compatibility with older daily entries.

Run with:
    python -m unittest tests.test_progress -v
or (when pytest is available):
    python -m pytest tests -q -k progress
"""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from tools import progress  # noqa: E402


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class ProgressTypesTests(unittest.TestCase):
    def test_fake_types_tree_counts_and_malformed_tolerance(self):
        """Feed one G, one S, one V answer and one malformed file; verify all counts."""
        with tempfile.TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            types_dir = root / "orchestration" / "types"
            batches_dir = types_dir / "batches"
            out_dir = types_dir / "out"
            merged_dir = types_dir / "merged"
            done_dir = root / "orchestration" / "done"

            # 1. Inputs to recover: 5 globals, 2 classes with 5 fields (+1 empty namespace),
            #    and 2 functions with 6 placeholder variables (+1 `self`).
            _write_json(types_dir / "globals.json", {
                "globals": [
                    {"address": "0x00760000", "section": ".data", "size": 4},
                    {"address": "0x00760004", "section": ".data", "size": 4},
                    {"address": "0x00760008", "section": ".bss", "size": 4},
                    {"address": "0x0076000C", "section": ".bss", "size": 4},
                    {"address": "0x00760010", "section": ".rodata", "size": 8},
                ],
            })
            _write_json(types_dir / "structs.json", {
                "classes": [
                    {
                        "class": "Ui_GaugeWindow",
                        "fields": [
                            {"offset": 0, "size": 4},
                            {"offset": 76, "size": 4},
                            {"offset": 80, "size": 4},
                        ],
                    },
                    {
                        "class": "Battle_Unit",
                        "fields": [
                            {"offset": 0, "size": 4},
                            {"offset": 4, "size": 4},
                        ],
                    },
                    {
                        "class": "Empty_NamespaceOnly",
                        "fields": [],
                    },
                ],
            })
            _write_json(types_dir / "locals.json", {
                "functions": [
                    {
                        "address": "0x00123456",
                        "name": "Field_UpdateActor",
                        "variables": [
                            {"name": "self", "is_param": True},
                            {"name": "arg1", "is_param": True},
                            {"name": "iVar1", "is_param": False},
                            {"name": "iVar2", "is_param": False},
                            {"name": "uStack_14", "is_param": False},
                        ],
                    },
                    {
                        "address": "0x00123500",
                        "name": "Field_TickTimer",
                        "variables": [
                            {"name": "arg2", "is_param": True},
                            {"name": "local_10", "is_param": False},
                        ],
                    },
                ],
            })

            # 2. Batch files and done reports: G 1/2, S 1/3, V 1/2 -> total 3/7.
            for bid in ("G_001", "G_002", "S_001", "S_002", "S_003", "V_001", "V_002"):
                _write_json(batches_dir / f"{bid}.json", {"id": bid})
            for done_id in ("G_001", "S_001", "V_001"):
                _write_text(done_dir / f"{done_id}.md", f"# {done_id} done\n")

            # 3. Worker answers: one G, one S, one V, plus one malformed JSON file.
            _write_json(out_dir / "G_001.json", [
                {"address": "0x00760000", "name": "g_titleState", "type": "u32", "confidence": 0.85},
                {"address": "0x00760004", "name": "maybe_g_fadeTimer", "type": "u32", "confidence": 0.4},
                {"address": "0x00760008", "name": "g_lowConfFlag", "type": "u8", "confidence": 0.35},
                {"address": "0x0076000C", "name": "unknown", "type": "u32", "confidence": 0.0},
            ])
            _write_json(out_dir / "S_001.json", [
                {
                    "class": "Ui_GaugeWindow",
                    "type": "UiGaugeWindow",
                    "confidence": 0.75,
                    "fields": [
                        {"offset": 0, "name": "vtable", "type": "void*", "size": 4, "confidence": 0.95},
                        {"offset": 76, "name": "maybe_gaugePane", "type": "void*", "size": 4, "confidence": 0.4},
                        {"offset": 80, "name": "unknown_counter", "type": "u32", "size": 4, "confidence": 0.0},
                    ],
                },
                {
                    "class": "Battle_Unit",
                    "type": "maybe_BattleUnit",
                    "confidence": 0.35,
                    "fields": [
                        {"offset": 4, "name": "unitId", "type": "u32", "size": 4, "confidence": 0.8},
                    ],
                },
            ])
            _write_json(out_dir / "V_001.json", [
                {
                    "address": "0x00123456",
                    "function": "Field_UpdateActor",
                    "params": {"self": "self", "arg1": "actor"},
                    "locals": {"iVar1": "partyCount", "iVar2": "maybe_moveSpeed"},
                    "confidence": 0.7,
                },
                {
                    "address": "0x00123500",
                    "function": "Field_TickTimer",
                    "locals": {"local_10": "frameCounter"},
                    "confidence": 0.3,
                },
            ])
            # Malformed worker output (simulates interrupted write).
            _write_text(out_dir / "G_002.json", '[{"address": "0x00760010", "name": "broken"')

            # 4. Merged maps (plus a report.json with larger `--validate` counts that must
            #    NOT inflate `merged`).
            _write_json(merged_dir / "report.json", {
                "demo": False,
                "merged": {"globals": 999, "classes": 999, "fields": 999, "locals": 999},
                "errors": 2,
                "warnings": 1,
            })
            _write_json(merged_dir / "globals.json", {
                "globals": {
                    "0x00760000": {"name": "g_titleState", "type": "u32"},
                },
            })
            _write_json(merged_dir / "fields.json", {
                "classes": {
                    "Ui_GaugeWindow": {
                        "type": "UiGaugeWindow",
                        "fields": {
                            "0": {"name": "vtable", "type": "void*"},
                            "76": {"name": "maybe_gaugePane", "type": "void*"},
                        },
                    },
                },
            })
            _write_json(merged_dir / "locals.json", {
                "functions": {
                    "0x00123456": {
                        "params": {"arg1": "actor"},
                        "locals": {},
                    },
                },
            })

            res = progress.collect_types(root)

            # Malformed file counted, no crash.
            self.assertEqual(res["malformed_files"], 1)
            self.assertIn("orchestration/types/out/G_002.json", res["malformed"])
            self.assertEqual(res["errors"], 2)
            self.assertEqual(res["warnings"], 1)

            # Globals: 5 total, 4 answered (1 named, 2 guessed, 1 unknown), 1 merged, batches 1/2.
            g = res["globals"]
            self.assertEqual(g["total"], 5)
            self.assertEqual(g["answered"], 4)
            self.assertEqual(g["named"], 1)
            self.assertEqual(g["guessed"], 2)
            self.assertEqual(g["merged"], 1)
            self.assertEqual(g["batches"], {"kind": "G", "done": 1, "total": 2})

            # Classes: 2 total (empty namespace excluded), 2 answered (1 named, 1 guessed), 1 merged, batches 1/3.
            c = res["classes"]
            self.assertEqual(c["total"], 2)
            self.assertEqual(c["answered"], 2)
            self.assertEqual(c["named"], 1)
            self.assertEqual(c["guessed"], 1)
            self.assertEqual(c["merged"], 1)
            self.assertEqual(c["batches"], {"kind": "S", "done": 1, "total": 3})

            # Fields: 5 total, 4 answered (2 named, 1 guessed, 1 unknown_counter), 2 merged, batches 1/3.
            f = res["fields"]
            self.assertEqual(f["total"], 5)
            self.assertEqual(f["answered"], 4)
            self.assertEqual(f["named"], 2)
            self.assertEqual(f["guessed"], 1)
            self.assertEqual(f["merged"], 2)
            self.assertEqual(f["batches"], {"kind": "S", "done": 1, "total": 3})

            # Locals: 6 placeholder vars, 4 answered (2 named, 2 guessed; `self->self` ignored), 1 merged, batches 1/2.
            v = res["locals"]
            self.assertEqual(v["total"], 6)
            self.assertEqual(v["answered"], 4)
            self.assertEqual(v["named"], 2)
            self.assertEqual(v["guessed"], 2)
            self.assertEqual(v["merged"], 1)
            self.assertEqual(v["batches"], {"kind": "V", "done": 1, "total": 2})

            # Aggregate totals & batch roll-up.
            self.assertEqual(res["total"], 18)
            self.assertEqual(res["answered"], 14)
            self.assertEqual(res["named"], 6)
            self.assertEqual(res["guessed"], 6)
            self.assertEqual(res["merged"], 5)
            self.assertEqual(res["batches"], {
                "G": {"done": 1, "total": 2},
                "S": {"done": 1, "total": 3},
                "V": {"done": 1, "total": 2},
                "done": 3,
                "total": 7,
            })

    def test_header_fallback_and_answer_deduplication(self):
        """Fallback to include/dqxi/*.h when merged/*.json is absent, and upgrade guessed -> named."""
        with tempfile.TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            out_dir = root / "orchestration" / "types" / "out"
            headers_dir = root / "include" / "dqxi"

            # Two batches touch the same global; confident name must win over earlier maybe_.
            _write_json(out_dir / "G_001.json", [
                {"address": "0x006897AC", "name": "maybe_g_battleCtx", "confidence": 0.3},
            ])
            _write_json(out_dir / "G_002.json", [
                {"address": "0x006897AC", "name": "g_battleContext", "confidence": 0.9},
            ])

            _write_text(headers_dir / "globals.h", (
                "#pragma once\n"
                "extern u32 g_battleContext; /* 0x006897AC */\n"
                "extern u8 g_menuMode; /* 0x006897B0 */\n"
            ))
            _write_text(headers_dir / "structs.h", (
                "#pragma once\n"
                "typedef struct UiGaugeWindow {\n"
                "    u8 _base[0x4C]; /* +0x0000 inherited UiAnimRef */\n"
                "    void* gaugePane; /* +0x004C */\n"
                "    void* flashPane; /* +0x0050 */\n"
                "} UiGaugeWindow;\n"
            ))

            res = progress.collect_types(root)
            self.assertEqual(res["globals"]["answered"], 1)
            self.assertEqual(res["globals"]["named"], 1)
            self.assertEqual(res["globals"]["guessed"], 0)
            self.assertEqual(res["globals"]["merged"], 2)
            self.assertEqual(res["classes"]["merged"], 1)
            self.assertEqual(res["fields"]["merged"], 2)

    def test_empty_and_corrupt_binary_files_never_crash(self):
        """Missing directories, invalid UTF-8 bytes, and wrong JSON root shapes never raise."""
        with tempfile.TemporaryDirectory() as tmp_str:
            empty_root = Path(tmp_str) / "empty"
            empty_root.mkdir()
            empty_res = progress.collect_types(empty_root)
            self.assertEqual(empty_res["total"], 0)
            self.assertEqual(empty_res["malformed_files"], 0)
            self.assertEqual(empty_res["source"], "not generated yet")

            bad_root = Path(tmp_str) / "corrupt"
            types_dir = bad_root / "orchestration" / "types"
            out_dir = types_dir / "out"
            out_dir.mkdir(parents=True)
            # Invalid UTF-8 bytes in globals.json and wrong root/entry shapes in structs.json & out/*.json.
            (types_dir / "globals.json").write_bytes(b"\xff\xfe\x80not-utf8")
            _write_json(types_dir / "structs.json", ["wrong_top_level_list"])
            _write_json(out_dir / "S_001.json", {"unexpected_key": 123})
            _write_json(out_dir / "V_001.json", [123, "not_an_object"])

            bad_res = progress.collect_types(bad_root)
            self.assertEqual(bad_res["total"], 0)
            self.assertEqual(bad_res["malformed_files"], 4)

    def test_overview_html_badge_and_history_preserve_old_entries(self):
        """html_progress, badge-types.svg and history.jsonl/svg render Data & types cleanly."""
        with tempfile.TemporaryDirectory() as tmp_str:
            root = Path(tmp_str)
            types_dir = root / "orchestration" / "types"
            _write_json(types_dir / "globals.json", {"stats": {"globals": 10}})
            _write_json(types_dir / "structs.json", {"stats": {"classes_with_fields": 4, "fields": 20}})
            _write_json(types_dir / "locals.json", {"stats": {"variables_placeholder": 66}})
            _write_json(types_dir / "batches" / "G_001.json", {})
            _write_json(types_dir / "batches" / "G_002.json", {})
            _write_text(root / "orchestration" / "done" / "G_001.md", "done\n")
            _write_json(types_dir / "out" / "G_001.json", [
                {"address": "0x00760000", "name": "g_mainHeap", "confidence": 0.9},
                {"address": "0x00760004", "name": "maybe_g_subHeap", "confidence": 0.4},
            ])

            types_data = progress.collect_types(root)
            self.assertEqual(types_data["total"], 100)
            self.assertEqual(types_data["named"], 1)
            self.assertEqual(types_data["guessed"], 1)

            page = progress.html_progress(
                progress.native_fallback(),
                progress.scripts_fallback(),
                progress.assets_fallback(),
                progress.editor_fallback(),
                progress.build_fallback(),
                types_data,
                "2026-10-30 18:00:00 CET",
            )
            self.assertIn('id="functions-card"', page)
            self.assertIn('id="data-types-card"', page)
            self.assertIn("Data &amp; types", page)
            self.assertIn('href="badge-types.svg"', page)
            self.assertIn("batches 1/2", page)
            self.assertIn('class="seg-named"', page)
            self.assertIn('class="seg-guessed"', page)

            badge = progress.badge_svg("data & types", "1.0% (1/2)", "#15803d")
            self.assertTrue(badge.startswith("<svg "))
            self.assertIn("data &amp; types", badge)
            self.assertIn("1.0% (1/2)", badge)

            # Seed an older history entry that predates types_named_pct.
            hist_dir = root / "progress_out"
            old_entry = {
                "date": "2026-10-25",
                "timestamp": "2026-10-25T23:00:21+01:00",
                "functions_named_pct": 45.2,
                "functions_documented_pct": 42.98,
                "assets_pct": 85.49,
                "assets_editable_pct": 65.87,
                "editor_pct": 50.0,
                "functions_named": 8492,
                "functions_total": 18787,
                "assets_converted": 29292,
                "assets_source": 34262,
                "editor_done": 8,
                "editor_partial": 8,
                "editor_total": 24,
            }
            _write_text(hist_dir / "history.jsonl", json.dumps(old_entry) + "\n")

            now = datetime(2026, 10, 30, 18, 0, 0, tzinfo=timezone.utc)
            entries = progress.update_history(
                progress.native_fallback(),
                progress.assets_fallback(),
                progress.editor_fallback(),
                now,
                types=types_data,
                out_dir=hist_dir,
            )
            self.assertEqual(len(entries), 2)
            self.assertEqual(entries[0], old_entry)
            self.assertEqual(entries[1]["date"], "2026-10-30")
            self.assertEqual(entries[1]["types_named_pct"], 1.0)
            self.assertEqual(entries[1]["types_named"], 1)
            self.assertEqual(entries[1]["types_guessed"], 1)
            self.assertEqual(entries[1]["types_batches_done"], 1)
            self.assertEqual(entries[1]["types_batches_total"], 2)

            svg = progress.history_chart(entries)
            self.assertIn("data &amp; types 1.0%", svg)
            hist_html = progress.html_history(entries, "2026-10-30 18:00:00 UTC")
            self.assertIn("<th>Data &amp; types</th>", hist_html)

    def test_live_progress_json_and_badge_on_disk(self):
        """Verify the generated progress/ artifacts expose the full types schema."""
        pjson = PROJECT_ROOT / "progress" / "progress.json"
        phtml = PROJECT_ROOT / "progress" / "progress.html"
        pbadge = PROJECT_ROOT / "progress" / "badge-types.svg"
        if not pjson.is_file():
            self.skipTest("progress/progress.json has not been generated yet")

        payload = json.loads(pjson.read_text(encoding="utf-8"))
        self.assertIn("types", payload)
        t = payload["types"]
        for kind_key in ("globals", "classes", "fields", "locals"):
            self.assertIn(kind_key, t)
            blk = t[kind_key]
            for field_key in ("total", "answered", "named", "guessed", "merged", "batches"):
                self.assertIn(field_key, blk)
            self.assertIn("done", blk["batches"])
            self.assertIn("total", blk["batches"])
            self.assertGreaterEqual(blk["total"], blk["answered"])
            self.assertGreaterEqual(blk["answered"], blk["named"] + blk["guessed"])

        self.assertTrue(pbadge.is_file(), "progress/badge-types.svg must exist")
        self.assertIn("data &amp; types", pbadge.read_text(encoding="utf-8"))
        html_text = phtml.read_text(encoding="utf-8")
        self.assertIn('id="data-types-card"', html_text)
        self.assertIn('id="functions-card"', html_text)

        # Every generated file in progress/ must decode strictly as UTF-8.
        for name in (
            "progress.json", "progress.html", "history.jsonl", "history.svg",
            "history.html", "badge-functions.svg", "badge-types.svg",
            "badge-assets.svg", "badge-editor.svg",
        ):
            p = PROJECT_ROOT / "progress" / name
            if p.is_file():
                p.read_bytes().decode("utf-8")


if __name__ == "__main__":
    unittest.main()
