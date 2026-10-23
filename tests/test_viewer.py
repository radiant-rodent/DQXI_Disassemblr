"""Smoke tests for the DQXI Explorer desktop viewer.

Run standalone (``python tests/test_viewer.py``) or via unittest
(``python -m unittest tests.test_viewer`` from the project root).

The tests build a real Tk window (withdrawn) and drive the same code paths
the UI uses: index construction, mesh parsing, layout preview rendering,
audio decoding, dialogue lookup and the global search panel.  Everything is
read-only, so no project files change.
"""

from __future__ import annotations

import os
import sys
import time
import math
import tkinter as tk
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# never run the background index preload inside tests (keeps timing deterministic)
os.environ.setdefault("DQXI_VIEWER_NO_PRELOAD", "1")

from viewer import utils  # noqa: E402
from viewer.app import App  # noqa: E402
from viewer.render import obj as obj_mod  # noqa: E402
from viewer.render import waveform as wf  # noqa: E402
from viewer.render.layout_preview import (LayoutPreview, PreviewOptions,  # noqa: E402
                                          choose_y_up)
from viewer.render.renderer3d import MeshViewer  # noqa: E402
from viewer.ui.panels import PANELS  # noqa: E402
from viewer.ui.widgets import THUMBS  # noqa: E402

SECTION_KEYS = [cls.key for cls in PANELS]


class ViewerSmokeTest(unittest.TestCase):
    app: App

    @classmethod
    def setUpClass(cls) -> None:
        cls.app = App()
        cls.app.withdraw()
        cls.app.update()

    @classmethod
    def tearDownClass(cls) -> None:
        try:
            cls.app.destroy()
        except tk.TclError:
            pass

    def _canvas_window(self, width: int = 960, height: int = 720):
        """A mapped (off-screen) window hosting a real-sized canvas.

        Tk reports ``winfo_width() == 1`` for widgets that were never mapped,
        and the renderers deliberately skip drawing on such canvases.
        """
        top = tk.Toplevel(self.app)
        top.geometry(f"{width}x{height}+4000+4000")
        top.overrideredirect(True)
        canvas = tk.Canvas(top, bg="#000000")
        canvas.pack(fill="both", expand=True)
        top.update_idletasks()
        top.update()
        return top, canvas

    # -- application shell ---------------------------------------------
    def test_01_window_builds(self) -> None:
        app = self.app
        self.assertTrue(app.winfo_exists())
        self.assertEqual(app._current, "overview")
        self.assertEqual(set(app._nav_buttons), set(SECTION_KEYS))

    def test_02_every_section_opens(self) -> None:
        app = self.app
        for key in SECTION_KEYS:
            app.show_section(key)
            app.update()
            self.assertEqual(app._current, key, f"section {key} did not become current")
            self.assertIn(key, app._panels)
            self.assertTrue(app._panels[key].winfo_exists())

    def test_03_show_section_passes_filters(self) -> None:
        app = self.app
        app.show_section("textures", query="b001")
        app.update()
        panel = app._panels["textures"]
        self.assertEqual(panel.entry.get_value(), "b001")
        app.show_section("maps", query="b001")
        app.update()
        self.assertEqual(app._panels["maps"].entry.get_value(), "b001")

    def test_04_status_bar(self) -> None:
        self.app.set_status("smoke test")
        self.app.update()
        self.assertEqual(self.app.status_label.cget("text"), "smoke test")

    # -- data indexes ---------------------------------------------------
    def test_10_texture_index(self) -> None:
        index = self.app.textures.ensure()
        self.assertGreater(len(index.items), 3000)
        self.assertTrue(index.packs())
        sample = index.items[0]
        self.assertTrue(sample.path.exists())
        self.assertTrue(sample.dims)
        hits = index.search("b001")
        self.assertTrue(hits)

    def test_11_model_index_and_mesh(self) -> None:
        index = self.app.models.ensure()
        self.assertGreaterEqual(len(index.items), 90)
        categories = dict(index.categories())
        self.assertIn("Monsters", categories)
        self.assertIn("Environments", categories)
        self.assertEqual(sum(categories.values()), len(index.items))

        for model in index.items[:10]:
            self.assertTrue(model.obj.exists(), f"missing {model.obj}")
            self.assertEqual(model.obj.stem, model.name)
            self.assertTrue(model.category)

        mesh_item = index.get("Slime") or index.items[0]
        mesh = obj_mod.load_obj(mesh_item.obj, mesh_item.mtl)
        stats = mesh.stats()
        self.assertGreater(stats["triangles"], 0)
        self.assertGreater(stats["vertices"], 0)
        self.assertGreaterEqual(stats["parts"], 1)

        top, canvas = self._canvas_window()
        try:
            self.assertGreater(canvas.winfo_width(), 10, "test canvas has no size")
            viewer = MeshViewer(canvas)
            viewer.set_mesh(mesh)
            viewer.draw()
            self.assertGreater(len(canvas.find_all()), 0, "renderer produced no canvas items")
            self.assertGreater(viewer.last_drawn, 0)
            viewer.wireframe = True
            viewer.draw()
            self.assertGreater(len(canvas.find_all()), 0)
        finally:
            top.destroy()

    def test_11b_salvages_corrupt_environment_mesh(self) -> None:
        """Exports with stray 1e30 / NaN vertices must still frame and draw."""
        index = self.app.models.ensure()
        candidates = ("Map_b005_106a", "Hotto_Steamy_Town", "Fortress_of_Fear",
                      "Manglegrove_Wilderness", "Map_b009_102a")
        mesh = None
        for name in candidates:
            model = index.get(name)
            if model is None:
                continue
            candidate = obj_mod.load_obj(model.obj, model.mtl)
            if candidate.nonfinite_count() or candidate.outlier_count():
                mesh = candidate
                break
        if mesh is None:
            self.skipTest("no corrupt environment vertices in this export")

        stats = mesh.stats()
        self.assertTrue(math.isfinite(mesh.radius), "radius must stay finite")
        self.assertLess(mesh.radius, 1e5, "camera framing must ignore stray vertices")
        self.assertGreater(stats["triangles"], 0)
        self.assertGreater(stats["nonfinite"] + stats["outliers"], 0)

        top, canvas = self._canvas_window(800, 600)
        try:
            viewer = MeshViewer(canvas)
            viewer.set_mesh(mesh)
            viewer.draw()
            self.assertGreater(viewer.last_drawn, 0, "dense environment drew nothing")
            self.assertGreater(len(canvas.find_all()), 0)
        finally:
            top.destroy()

    def test_12_layout_index_and_preview(self) -> None:
        index = self.app.layouts.ensure()
        self.assertTrue(index.items)
        item = next((l for l in index.items if l.stem.startswith("battle_2d_lw")),
                    index.items[0])
        data = index.load(item.path)
        self.assertTrue(data.get("panes"), "reference layout has no panes")
        expected_y_up = choose_y_up(data.get("panes") or [], 400.0, 240.0)
        self.assertIsInstance(expected_y_up, bool)

        top, canvas = self._canvas_window()
        try:
            self.assertGreater(canvas.winfo_width(), 10, "test canvas has no size")
            preview = LayoutPreview(canvas)
            boxes = preview.render(data, PreviewOptions(), resolver=self.app.textures.resolve)
            self.assertGreater(len(canvas.find_all()), 0, "layout preview produced no items")
            self.assertTrue(boxes, "layout preview produced no pane boxes")
            pane = boxes[0][0].get("name")
            if pane:
                preview.select(pane)
                self.assertEqual(preview.selected, pane)
        finally:
            top.destroy()

    def test_13_script_and_table_indexes(self) -> None:
        scripts = self.app.scripts.ensure()
        self.assertTrue(scripts.items)
        script = scripts.items[0]
        text = scripts.text(script)
        self.assertIn("function", text)
        outline = scripts.outline(script)
        self.assertIsInstance(outline, list)

        tables = self.app.tables.ensure()
        self.assertTrue(tables.items)
        table = tables.items[0]
        self.assertIsInstance(tables.summary(table), str)

    def test_14_audio_and_waveform(self) -> None:
        index = self.app.audio.ensure()
        self.assertTrue(index.streams)
        stream = index.streams[0]
        self.assertTrue(stream.path.exists())
        mins, maxs, info = wf.peaks(stream.path, 64)
        self.assertEqual(len(mins), 64)
        self.assertEqual(len(maxs), 64)
        self.assertTrue(info.get("rate"))

    def test_15_code_index(self) -> None:
        index = self.app.code.ensure()
        self.assertGreater(len(index.functions), 18000)
        func = index.functions[0]
        self.assertTrue(func.addr_hex.startswith("0x"))
        found = index.search(func.name[:8])
        self.assertTrue(found)

    def test_16_thumbnail_cache(self) -> None:
        index = self.app.textures.ensure()
        tex = next((t for t in index.items if t.size_bytes > 0), index.items[0])
        thumb = THUMBS.get(tex.path, 148)
        self.assertIsNotNone(thumb)
        self.assertLessEqual(max(thumb.size), 148)

    def test_17_model_panel_async_load(self) -> None:
        """The mesh worker must hand its result back to the Tk main thread."""
        app = self.app
        app.show_section("models")
        panel = app._panels["models"]
        self.assertTrue(panel._items, "model list is empty")
        target = app.models.get("Slime") or panel._items[0]
        iid = str(target.obj)
        panel.tree.selection_set(iid)
        panel.tree.see(iid)
        panel._on_select()
        deadline = time.time() + 60.0
        while time.time() < deadline and iid not in panel._mesh_cache:
            app.update()
            time.sleep(0.02)
        self.assertIn(iid, panel._mesh_cache, "mesh never reached the main thread")
        self.assertIn("tris", panel.stats_label.cget("text"))

    def test_18_model_panel_category_filter(self) -> None:
        app = self.app
        app.show_section("models")
        panel = app._panels["models"]
        panel.set_filter(category="Monsters")
        app.update()
        self.assertTrue(panel._items)
        self.assertTrue(all(m.category == "Monsters" for m in panel._items))
        panel.set_filter(query="Slime", category="")
        app.update()
        self.assertTrue(any("slime" in m.name.lower() for m in panel._items))

    def test_19_areas_link_scene_models(self) -> None:
        app = self.app
        app.models.ensure()
        app.areas.ensure(app.textures, app.scripts, app.audio, app.layouts,
                         app.dialogues, app.models)
        with_models = [a for a in app.areas.all_areas() if app.areas.dossier(a).models]
        self.assertGreaterEqual(len(with_models), 20, "no map areas reference 3D scenes")
        area = with_models[0]
        dossier = app.areas.dossier(area)
        self.assertTrue(all(name for name in dossier.models))
        self.assertIn("Map_b001_101b", app.areas.dossier("b001_101b").models)

    def test_19b_model_jump_selects_model(self) -> None:
        """Jumping from a map dossier / search hit opens the model, not just a filter."""
        app = self.app
        app.show_section("models", query="Map_b001_101b")
        app.update()
        panel = app._panels["models"]
        self.assertEqual(panel.name_label.cget("text"), "Map_b001_101b")
        self.assertEqual(panel.tree.selection(), (str(app.models.get("Map_b001_101b").obj),))

    # -- dialogues (read-only reference database) -----------------------
    def test_20_dialogue_index(self) -> None:
        db = self.app.dialogues
        self.assertTrue(db.available(), f"dialogue db missing at {db.path}")
        st = db.stats()
        self.assertGreater(st.sources, 40000)
        rows = db.search_sources("", limit=5)
        self.assertTrue(rows)
        self.assertTrue(db.locations(rows[0].id))

    def test_21_dialogue_db_untouched(self) -> None:
        db = self.app.dialogues
        before = db.path.stat().st_mtime_ns
        db.search_sources("battle", limit=10)
        db.count_sources("battle")
        if db.file_list():
            db.file_list()
        db.locations(1)
        after = db.path.stat().st_mtime_ns
        self.assertEqual(before, after, "read-only dialogue database was modified")

    # -- global search ---------------------------------------------------
    def test_30_search_panel_round_trip(self) -> None:
        app = self.app
        app.show_section("search")
        panel = app._panels["search"]
        panel.set_filter(query="battle")
        deadline = time.time() + 30.0
        while time.time() < deadline and not panel._hits:
            app.update()
            time.sleep(0.05)
        self.assertTrue(panel._hits, "search returned no hits for 'battle'")
        scopes = {hit.scope for hit in panel._hits}
        self.assertTrue(scopes)
        self.assertTrue(panel.summary())

        panel._open_selected()
        app.update()
        self.assertNotEqual(app._current, "search",
                            "opening a result should jump to its section")

    def test_31_search_jump_to_code(self) -> None:
        app = self.app
        needle = app.code.ensure().functions[0].name      # e.g. "ResetVector"
        app.show_section("search")
        panel = app._panels["search"]
        panel.set_filter(query=needle)
        deadline = time.time() + 30.0
        code_hits: list = []
        while time.time() < deadline:
            app.update()
            code_hits = [h for h in panel._hits if h.scope == "code"]
            if code_hits:
                break
            time.sleep(0.05)
        self.assertTrue(code_hits, f"no code hits for {needle!r}")

        target = next(iid for iid, hit in panel._by_iid.items() if hit.scope == "code")
        panel.tree.selection_set(target)
        panel._open_selected()
        app.update()
        self.assertEqual(app._current, "code")
        self.assertEqual(app._panels["code"].entry.get_value(), code_hits[0].payload["addr"])


def main() -> int:
    unittest.main(verbosity=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
