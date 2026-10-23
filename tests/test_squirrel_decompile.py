#!/usr/bin/env python3
"""tests/test_squirrel_decompile.py - Squirrel bytecode decompiler (tools/squirrel_decompile.py)."""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from tools import sqbin, squirrel_decompile as sd  # noqa: E402

SCRIPTS = PROJECT_ROOT / "game_data" / "packs" / "script"


def script(name: str) -> sqbin.Func:
    return sqbin.parse((SCRIPTS / name / "script.cnut").read_bytes())


def func_text(root: sqbin.Func, name: str) -> str:
    """Decompile one nested function on its own (without the surrounding table)."""
    d = sd.FuncDecomp(root.find(name))
    d.decompile()
    return d.render_block(d.stmts, "")


@unittest.skipUnless(SCRIPTS.exists(), "game_data/packs/script not extracted")
class TestRealFunctions(unittest.TestCase):
    def test_a000_table_setup(self):
        text, stats = sd.decompile_func(script("a_000"))
        self.assertTrue(text.startswith("a_000 <- {\n"))
        self.assertIn("    function OnSelectRuraPattern() {\n        return 255;\n    }", text)
        self.assertIn("    function OnSelectRiremitoUsable() {\n        return -1;\n    }", text)
        self.assertIn("    function OnCutSceneEnd(csid) {}", text)
        self.assertIn("    function StartEventArg(func, ...) {", text)
        self.assertTrue(text.rstrip().endswith("delegate getroottable() : a_000;"))
        self.assertEqual(len(stats), 12)
        self.assertTrue(all(s["fallback_blocks"] == 0 and s["unresolved_regs"] == 0 for s in stats))

    def test_event_handler_calls(self):
        self.assertEqual(func_text(script("a_000"), "StartEvent"), (
            "g_req_event = newthread(ThreadExecute);\n"
            'RegistThread("g_req_event", func);\n'
            "g_req_event.call(a_000, func);\n"))

    def test_else_if_chain_and_varargs(self):
        text = func_text(script("a_000"), "StartEventArg")
        self.assertIn("if (vargc == 0) {\n    g_req_event.call(a_000, func);\n} else if (vargc == 1) {", text)
        self.assertIn("g_req_event.call(a_000, func, vargv[0], vargv[1], vargv[2], vargv[3]);", text)

    def test_locals_and_short_circuit(self):
        text = func_text(script("a_010"), "OnPreSetupLevel")
        self.assertIn("local map_id = GetLevelMapID();", text)
        self.assertIn("local flag_a010 = GetScenarioFlag(0);", text)
        self.assertIn("if (flag_a010 >= 0 && flag_a010 <= 3) {", text)
        self.assertIn("FixedTimeZone(1);", text)
        self.assertIn("if (map_id == 15 || map_id == 17) {", text)

    def test_loop_arithmetic_and_compound_assign(self):
        text = func_text(script("base"), "MoveFloorCameraMoveThread")
        self.assertIn("while (frame < targetFrame) {", text)
        self.assertIn("t /= d / 2.0;", text)
        self.assertIn("easing = c / 2.0 * t * t + b;", text)
        self.assertIn("easing = -c / 2.0 * (t * (t - 2.0) - 1.0) + b;", text)
        self.assertIn("++frame;", text)

    def test_for_loop(self):
        text = func_text(script("a_010_cs_090"), "Cut001")
        self.assertIn("for (i = 0; i <= 15; i++) {", text)

    def test_tailcall_returns_value(self):
        self.assertEqual(func_text(script("base"), "Message"),
                         "return MessageEx(text_id, actor_id, swing, 255);\n")

    def test_block_final_local(self):
        # local declared as the last statement of a block (its scope closes before it opens)
        text = func_text(script("a_050"), "TrgRCommand")
        self.assertIn("local evil_beast_win = GetGlobalGameFlag(30);", text)


class TestFallback(unittest.TestCase):
    def _func(self, insns, lits=()):
        f = sqbin.Func(sqbin.S("t.nut"), sqbin.S("f"), literals=[sqbin.S(x) for x in lits],
                       parameters=[sqbin.S("this")], localvarinfos=[(sqbin.S("this"), 0, 0, len(insns))],
                       instructions=insns)
        return sd.decompile_func(f)

    def test_unknown_opcode_becomes_asm_block(self):
        O = sqbin.OP
        text, stats = self._func([
            sqbin.Insn(O["LOADINT"], 1, 5), sqbin.Insn(O["YIELD"], 1, 1),
            sqbin.Insn(O["RETURN"], 255)])
        self.assertIn("ASM FALLBACK", text)
        self.assertIn("YIELD", text)
        self.assertEqual(stats[0]["fallback_blocks"], 1)

    def test_simple_call(self):
        O = sqbin.OP
        text, _ = self._func([
            sqbin.Insn(O["PREPCALLK"], 1, 0, 0, 2), sqbin.Insn(O["LOADINT"], 3, 7),
            sqbin.Insn(O["CALL"], 1, 1, 2, 2), sqbin.Insn(O["RETURN"], 255)], ["WaitFrame"])
        self.assertEqual(text, "WaitFrame(7);\n")


@unittest.skipUnless(SCRIPTS.exists(), "game_data/packs/script not extracted")
class TestAllScripts(unittest.TestCase):
    def test_every_script_decompiles(self):
        srcs = sorted((PROJECT_ROOT / "game_data" / "packs").rglob("*.cnut"))
        self.assertGreaterEqual(len(srcs), 769)
        for src in srcs:
            with self.subTest(script=src.parent.name):
                text, stats = sd.decompile_bytes(src.read_bytes(), src.parent.name)
                self.assertTrue(text)
                self.assertTrue(stats)


if __name__ == "__main__":
    unittest.main()
