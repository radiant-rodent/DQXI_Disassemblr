"""Tests for tools/script_build.py: the two script editing levels.

The slow whole-corpus measurement lives in `python tools/script_build.py verify`
(it writes `audit/SCRIPT_BUILD.md`); these tests pin the mechanics on real
scripts so a regression fails fast.
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tools import pack, script_build, squirrel_decompile, sqbin
from tools.sqbin import OP

ROOT = Path(__file__).resolve().parent.parent
CNUT_DIR = ROOT / "game_data" / "packs" / "script"


def load_area(area: str) -> tuple[bytes, str]:
    data = (CNUT_DIR / area / "script.cnut").read_bytes()
    source, _ = squirrel_decompile.decompile_bytes(data, area)
    return data, source


class ScriptBuildTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.data, cls.source = load_area("a000_area")
        cls.a000_bytes, cls.a000_source = load_area("a_000")

    def test_assembly_listing_round_trips_bit_exactly(self) -> None:
        for area in ("a000_area", "a_000", "common"):
            with self.subTest(area=area):
                data = (CNUT_DIR / area / "script.cnut").read_bytes()
                listing = sqbin.disasm(sqbin.parse(data))
                rebuilt, info = script_build.assembly_build(listing)
                self.assertEqual(info["tier"], "asm")
                self.assertEqual(rebuilt, data)

    def test_assembly_edit_changes_the_immediate(self) -> None:
        listing = sqbin.disasm(sqbin.parse(self.a000_bytes))
        needle = "[   0] LOADINT      1    255   0   0"
        self.assertIn(needle, listing)
        edited = listing.replace(needle, "[   0] LOADINT      1      7   0   0", 1)
        data, info = script_build.assembly_build(edited)
        self.assertNotEqual(data, self.a000_bytes)
        back, _ = squirrel_decompile.decompile_bytes(data, "a_000")
        self.assertIn("return 7;", back)

    def test_untouched_source_rebuild_is_byte_identical(self) -> None:
        rebuilt, info = script_build.source_build(self.source, self.data, reuse=True)
        self.assertEqual(rebuilt, self.data, "an unchanged script must not change a single byte")
        self.assertGreater(info["reused"], 0)
        self.assertEqual(info["compiled"], 0)

    def test_every_function_compiles_and_means_the_same_thing(self) -> None:
        rebuilt, info = script_build.source_build(self.source, self.data, reuse=False)
        self.assertGreater(info["compiled"], 0)
        # The compiler is free to allocate registers differently, so require a
        # valid stream that decompiles to the same program, not equal bytes.
        parsed = sqbin.parse(rebuilt)
        self.assertEqual(sqbin.build(parsed), rebuilt)
        back, _ = squirrel_decompile.decompile_bytes(rebuilt, "a000_area")
        self.assertEqual(
            script_build._semantic_key(script_build.parse_source(back)),
            script_build._semantic_key(script_build.parse_source(self.source)),
        )

    def test_literal_edit_reaches_the_bytecode(self) -> None:
        edited = self.a000_source.replace("return 255;", "return 7;", 1)
        self.assertNotEqual(edited, self.a000_source)
        data, info = script_build.source_build(edited, self.a000_bytes, reuse=True)
        self.assertNotEqual(data, self.a000_bytes)
        # The edited function and the script body that embeds its prototype are
        # recompiled; every other function is copied byte for byte.
        by_name = {row["name"]: row for row in info["functions_report"]}
        self.assertFalse(by_name["OnSelectRuraPattern"]["reused"])
        self.assertTrue(by_name["OnSelectRiremitoUsable"]["reused"])
        self.assertGreaterEqual(info["reused"], 5)
        back, _ = squirrel_decompile.decompile_bytes(data, "a_000")
        self.assertIn("return 7;", back)
        self.assertNotIn("return 255;", back)

    def test_added_statement_compiles(self) -> None:
        edited = self.a000_source.replace(
            "function OnPreSetupLevel() {}",
            "function OnPreSetupLevel() {\n        SQCommand(99);\n    }",
            1,
        )
        self.assertNotEqual(edited, self.a000_source)
        data, info = script_build.source_build(edited, self.a000_bytes, reuse=True)
        by_name = {row["name"]: row for row in info["functions_report"]}
        self.assertFalse(by_name["OnPreSetupLevel"]["reused"])
        self.assertTrue(by_name["OnSelectRuraPattern"]["reused"])
        back, _ = squirrel_decompile.decompile_bytes(data, "a_000")
        self.assertIn("SQCommand(99);", back)

    def test_python_compiler_is_not_byte_exact_with_retail(self) -> None:
        # Honest property: a full compile reproduces *behaviour*, but Squirrel's
        # register allocation and debug line table are not recovered, so the
        # bytes differ. The assembly tier is the bit-exact path.
        rebuilt, _ = script_build.source_build(self.source, self.data, reuse=False)
        self.assertNotEqual(rebuilt, self.data)

    def test_broken_source_reports_a_line(self) -> None:
        broken = self.source.replace("function StartEvent(func) {", "function StartEvent(func) {{", 1)
        with self.assertRaises(script_build.BuildError) as ctx:
            script_build.source_build(broken, self.data, reuse=True)
        self.assertIsNotNone(ctx.exception.line)

    def test_pack_staging_writes_a_valid_mod_pack(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            mod = Path(tmp)
            edited = self.a000_source.replace("return 255;", "return 3;", 1)
            data, _ = script_build.source_build(edited, self.a000_bytes, reuse=True)
            info = script_build.save_to_mod(data, "a_000", mod)
            staged = mod / "romfs" / "script" / "a_000.pack"
            self.assertTrue(staged.is_file(), info)
            rebuilt = pack.Pack.parse(staged.read_bytes())
            member = next(e for e in rebuilt.entries if e.name == "script.cnut")
            self.assertEqual(member.data, data)
            self.assertEqual(info["member"], "script.cnut")

    def test_scan_decompiled_finds_functions_natives_and_calls(self) -> None:
        text = (ROOT / "game_assets" / "scripts" / "packs" / "script" / "a000_area"
                / "script.decompiled.nut").read_text(encoding="utf-8")
        script_build.NATIVE_NAMES = {"RegistThread", "RegistSubThread"}
        funcs, natives, calls = script_build.scan_decompiled(text)
        names = [f["name"] for f in funcs]
        self.assertIn("StartEvent", names)
        self.assertEqual(natives, ["RegistSubThread", "RegistThread"])
        self.assertIn("StartEvent", calls)
        self.assertIn("RegistThread", calls["StartEvent"])

    def test_source_and_listing_are_detected(self) -> None:
        self.assertFalse(script_build.looks_like_listing(self.source))
        listing = sqbin.disasm(sqbin.parse(self.data))
        self.assertTrue(script_build.looks_like_listing(listing))
        data, info = script_build.build_text(listing, self.data, "auto")
        self.assertEqual(info["tier"], "asm")
        self.assertEqual(data, self.data)


class ScriptCompilerFrameTests(unittest.TestCase):
    """The VM frame rules that a recompiled script must satisfy.

    This pins the bug found by the boot tests: a statement-position call used to
    compile with `CALL -1` (0xFF) as its result register, and this VM stores a
    resumed callee's value through that register, so the scene-load event wrote
    past its frame and the game crashed with no script error.
    """

    @classmethod
    def setUpClass(cls) -> None:
        cls.data, cls.source = load_area("b011")

    def _scene_load_edit(self) -> str:
        """The previously crashing edit: a new function started from OnBeginScene."""
        old = (
            "    function OnBeginScene() {\n"
            "        if (IsSetupLocationCS()) {\n"
            "            StartEvent(LocationCS2Way);\n"
            "        }\n"
            "    }\n"
        )
        new = (
            "    function X3SceneEvent() {\n"
            "        BookIDMessageSetup(26);\n"
            "        MessageLoop(-1);\n"
            "    }\n"
            "    function OnBeginScene() {\n"
            "        StartEvent(X3SceneEvent);\n"
            "        if (IsSetupLocationCS()) {\n"
            "            StartEvent(LocationCS2Way);\n"
            "        }\n"
            "    }\n"
        )
        edited = self.source.replace(old, new, 1)
        self.assertNotEqual(edited, self.source, "the b011 source layout changed; update the edit")
        return edited

    def test_retail_functions_satisfy_the_frame_rules(self) -> None:
        # The rules are read off retail, so retail itself must be clean.
        self.assertEqual(script_build.validate_nut(sqbin.parse(self.data)), [])

    def test_scene_load_edit_keeps_every_call_inside_its_frame(self) -> None:
        data, info = script_build.source_build(self._scene_load_edit(), self.data, reuse=True)
        func = sqbin.parse(data)
        self.assertEqual(script_build.validate_nut(func), [])

        by_name = {row["name"]: row for row in info["functions_report"]}
        self.assertFalse(by_name["OnBeginScene"]["reused"])
        self.assertFalse(by_name["X3SceneEvent"]["reused"])

        # BookIDMessageSetup(26); MessageLoop(-1); are statement-position calls:
        # their result is discarded, but the target register must still exist
        # because this VM writes a resumed value through it.
        event = func.find("X3SceneEvent")
        self.assertIsNotNone(event)
        calls = [ins for ins in event.instructions if ins.op == OP["CALL"]]
        self.assertEqual(len(calls), 2)
        for ins in calls:
            self.assertNotEqual(ins.arg0, 0xFF, "a discarded result must not target register -1")
            self.assertLess(ins.arg0, event.stacksize)

    def test_inserting_a_function_does_not_recompile_its_neighbours(self) -> None:
        _, info = script_build.source_build(self._scene_load_edit(), self.data, reuse=True)
        reused = {row["name"] for row in info["functions_report"] if row["reused"]}
        self.assertIn("OnPreSetupLevel", reused)
        self.assertIn("TrgRCommand", reused)
        self.assertIn("LocationCS2Way", reused)
        # Before matching children by name this reported 15 compiled functions
        # (every function after the insertion point), which is how the crash
        # spread from a two-line edit to half the pack.
        self.assertLessEqual(info["compiled"], 4)

    def test_validator_refuses_a_discarded_result_in_register_255(self) -> None:
        data, _ = script_build.source_build(self._scene_load_edit(), self.data, reuse=True)
        func = sqbin.parse(data)
        event = func.find("X3SceneEvent")
        call = next(ins for ins in event.instructions if ins.op == OP["CALL"])
        call.arg0 = 0xFF
        problems = script_build.validate_nut(func)
        self.assertTrue(problems, "an out-of-frame CALL target must be reported")
        self.assertIn("0xFF", problems[0])
        with self.assertRaises(script_build.BuildError) as ctx:
            script_build.require_valid(func, "source")
        self.assertIn("refusing", ctx.exception.text())
        self.assertIn("script.nut", ctx.exception.text())

    def test_validator_refuses_a_register_past_the_frame(self) -> None:
        func = sqbin.parse(self.data)
        event = func.find("IE_Z_M01_TAIJU")
        ins = next(i for i in event.instructions if i.op == OP["PREPCALLK"])
        ins.arg2 = event.stacksize          # object register outside the frame
        problems = script_build.validate_nut(func)
        self.assertTrue(any("PREPCALLK" in p for p in problems), problems)

    def test_discarded_call_targets_reusable_temporary(self) -> None:
        # A discarded result may not go to 0xFF, but it should also land on the
        # lowest free temporary so the next statement overwrites it. Otherwise
        # the decompiler keeps it as a pending value and loses the statement.
        data, _ = script_build.source_build(self._scene_load_edit(), self.data, reuse=True)
        event = sqbin.parse(data).find("X3SceneEvent")
        call = next(i for i in event.instructions if i.op == OP["CALL"])
        self.assertEqual(call.arg0, 1, "the first free temporary after `this` is register 1")
        self.assertLessEqual(call.arg0, call.arg1)
        self.assertLess(call.arg0, event.stacksize)

    def test_chain_of_or_operators_round_trips_through_the_decompiler(self) -> None:
        # b009 has long `a || b || c` chains. Reusing one destination register is
        # legal, but a discarded call left pending above it used to turn the
        # chain into an ASM FALLBACK and break the corpus semantic check.
        data = (CNUT_DIR / "b009" / "script.cnut").read_bytes()
        source, _ = squirrel_decompile.decompile_bytes(data, "b009")
        rebuilt, _ = script_build.source_build(source, data, reuse=False)
        back, _ = squirrel_decompile.decompile_bytes(rebuilt, "b009")
        self.assertNotIn("ASM FALLBACK", back)
        self.assertEqual(
            script_build._semantic_key(script_build.parse_source(back)),
            script_build._semantic_key(script_build.parse_source(source)),
        )


if __name__ == "__main__":
    unittest.main()
