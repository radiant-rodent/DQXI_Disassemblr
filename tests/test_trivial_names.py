#!/usr/bin/env python3
"""Tests for tools/trivial_names.py.

Two halves:

* synthetic instruction sequences, one per rule, built as raw bytes so the decoder and the rule
  matching are exercised end to end (including the cases that must *not* match);
* twenty real functions from the retail executable, each checked against the assembly by hand.
  The expected instruction sequence below is what ``asm/text/*.s`` shows for the addresses where
  the sweep is in the right mode, and what the raw bytes say where it is not (0x00102B90 and
  0x00115410 are the two mode traps documented in the tool's docstring).

Run with:  python tests/test_trivial_names.py      (or python -m pytest tests/test_trivial_names.py)
"""
from __future__ import annotations

import struct
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))

import trivial_names as T  # noqa: E402

BASE = T.BASE


# ---------------------------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------------------------
def arm_image(words: list[int], base: int = BASE) -> T.Code:
    """A Code image whose first words are ``words`` (little-endian ARM)."""
    data = bytearray(0x400)
    for i, word in enumerate(words):
        struct.pack_into("<I", data, i * 4, word)
    return T.Code(bytes(data))


def thumb_image(halfwords: list[int], base: int = BASE) -> T.Code:
    data = bytearray(0x400)
    for i, half in enumerate(halfwords):
        struct.pack_into("<H", data, i * 2, half)
    return T.Code(bytes(data))


class AlwaysAgrees:
    """Stand-in for AsmText: the synthetic images have no asm/text entry."""

    def agrees(self, instructions):
        return True


class NeverAgrees:
    def agrees(self, instructions):
        return False


def make_ctx(code: T.Code, names: dict[int, str] | None = None,
             signatures: dict[int, str] | None = None,
             vtables: dict[int, str] | None = None) -> dict:
    names = dict(names or {})
    signatures = dict(signatures or {})
    vtables = dict(vtables or {})
    # BASE is always the function under test, so the size lookup in rule 4 finds it.  The size
    # is 0x10: a stub is a handful of instructions, and a callee at +0x20 must count as outside.
    by_addr = {addr: {"addr": addr, "name": names.get(addr, f"func_{addr:08X}"),
                      "signature": signatures.get(addr, f"void func_{addr:08X}(void);"),
                      "size": 0x10}
               for addr in set(names) | set(signatures) | {BASE}}
    by_vtable: dict[str, list[int]] = {}
    for addr, group in vtables.items():
        by_vtable.setdefault(group, []).append(addr)
    return {
        "code": code,
        "names": names,
        "by_addr": by_addr,
        "function_addrs": set(by_addr),
        "size": {addr: 0x10 for addr in by_addr},
        "confidence": {},
        "xref": {},
        "vtables": vtables,
        "by_vtable": by_vtable,
    }


def propose_at(code: T.Code, addr: int, mode: str, ctx: dict, text=None) -> dict | None:
    analysis = T.analyse(code, text or AlwaysAgrees(), addr, mode)
    if analysis.terminal is None:
        return None
    return T.propose(addr, analysis, ctx)


# ---------------------------------------------------------------------------------------------
# synthetic: one case per rule
# ---------------------------------------------------------------------------------------------
class SyntheticRules(unittest.TestCase):
    def test_arm_field_getter_u32(self):
        # ldr r0,[r0,#0x10] ; bx lr
        code = arm_image([0xE5900010, 0xE12FFF1E])
        p = propose_at(code, BASE, "arm", make_ctx(code))
        self.assertEqual(p["name"], "Obj_GetU32At0x10")
        self.assertEqual(p["confidence"], 0.5)
        self.assertIn("ldr r0, [r0, #0x10]; bx lr", p["evidence"])

    def test_arm_field_getter_u8(self):
        # ldrb r0,[r0,#0xc] ; bx lr
        code = arm_image([0xE5D0000C, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "Obj_GetU8At0xC")

    def test_arm_field_getter_u16(self):
        # ldrh r0,[r0,#0x8] ; bx lr
        code = arm_image([0xE1D000B8, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "Obj_GetU16At0x8")

    def test_arm_field_getter_s16(self):
        # ldrsh r0,[r0,#0x4] ; bx lr
        code = arm_image([0xE1D000F4, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "Obj_GetS16At0x4")

    def test_arm_field_getter_through_add(self):
        # add r0,r0,#0x20 ; ldr r0,[r0,#0x4] ; bx lr  -> offset 0x24
        code = arm_image([0xE2800020, 0xE5900004, 0xE12FFF1E])
        p = propose_at(code, BASE, "arm", make_ctx(code))
        self.assertEqual(p["name"], "Obj_GetU32At0x24")
        self.assertIn("0x20 + 0x4", p["summary"])

    def test_arm_field_setter_u32(self):
        # str r1,[r0,#0x18] ; bx lr
        code = arm_image([0xE5801018, 0xE12FFF1E])
        p = propose_at(code, BASE, "arm", make_ctx(code))
        self.assertEqual(p["name"], "Obj_SetU32At0x18")
        self.assertEqual(p["signature"], "void Obj_SetU32At0x18(void* self, u32 value)")

    def test_arm_field_setter_u8(self):
        # strb r1,[r0,#0x2] ; bx lr
        code = arm_image([0xE5C01002, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "Obj_SetU8At0x2")

    def test_arm_constant_zero(self):
        # mov r0,#0 ; bx lr
        code = arm_image([0xE3A00000, 0xE12FFF1E])
        p = propose_at(code, BASE, "arm", make_ctx(code))
        self.assertEqual(p["name"], "ReturnsZero")
        self.assertEqual(p["signature"], "u32 ReturnsZero(void)")

    def test_arm_constant_one(self):
        # mov r0,#1 ; bx lr
        code = arm_image([0xE3A00001, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "ReturnsTrue")

    def test_arm_constant_minus_one(self):
        # mvn r0,#0 ; bx lr
        code = arm_image([0xE3E00000, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "ReturnsMinusOne")

    def test_arm_constant_movw(self):
        # movw r0,#0x1234 ; bx lr
        code = arm_image([0xE3010234, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"],
                         "ReturnsConstant0x1234")

    def test_arm_constant_movw_movt(self):
        # movw r0,#0x5678 ; movt r0,#0x1234 ; bx lr
        code = arm_image([0xE3050678, 0xE3410234, 0xE12FFF1E])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"],
                         "ReturnsConstant0x12345678")

    def test_arm_constant_from_literal_pool(self):
        # ldr r0,[pc,#0] ; bx lr ; .word 0x2a
        code = arm_image([0xE59F0000, 0xE12FFF1E, 0x0000002A])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"],
                         "ReturnsConstant0x2A")

    def test_arm_literal_pointing_into_the_image_is_not_a_constant(self):
        # ldr r0,[pc,#0] ; bx lr ; .word 0x007BE2D0 (a singleton address, not a constant)
        code = arm_image([0xE59F0000, 0xE12FFF1E, 0x007BE2D0])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_arm_forwarder_call_and_return(self):
        # push {r4,lr} ; bl 0x00100020 ; pop {r4,pc}
        code = arm_image([0xE92D4010, 0xEB000005, 0xE8BD8010])
        ctx = make_ctx(code, names={0x00100020: "Camera_GetHeadingAngle"},
                       signatures={0x00100020: "float Camera_GetHeadingAngle(void* self);"})
        p = propose_at(code, BASE, "arm", ctx)
        self.assertEqual(p["name"], "Camera_GetHeadingAngleThunk")
        self.assertEqual(p["signature"], "float Camera_GetHeadingAngleThunk(void* self)")

    def test_arm_forwarder_tail_call(self):
        # b 0x00100020
        code = arm_image([0xEA000006])
        ctx = make_ctx(code, names={0x00100020: "Sound_PlaySeById"})
        self.assertEqual(propose_at(code, BASE, "arm", ctx)["name"], "Sound_PlaySeByIdThunk")

    def test_arm_forwarder_to_unnamed_callee(self):
        # push {r4,lr} ; bl 0x00100020 ; pop {r4,pc}
        code = arm_image([0xE92D4010, 0xEB000005, 0xE8BD8010])
        ctx = make_ctx(code, names={0x00100020: "maybe_Something"})
        p = propose_at(code, BASE, "arm", ctx)
        self.assertEqual(p["name"], "maybe_Thunk_Call00100020")
        self.assertEqual(p["confidence"], 0.45)
        self.assertEqual(p["change"], "kept_maybe")

    def test_arm_empty_stub(self):
        # bx lr
        code = arm_image([0xE12FFF1E])
        p = propose_at(code, BASE, "arm", make_ctx(code))
        self.assertEqual(p["name"], "Nop_00100000")
        self.assertEqual(p["signature"], "void Nop_00100000(void)")

    def test_arm_empty_stub_with_frame(self):
        # push {r4,lr} ; pop {r4,pc}
        code = arm_image([0xE92D4010, 0xE8BD8010])
        self.assertEqual(propose_at(code, BASE, "arm", make_ctx(code))["name"], "Nop_00100000")

    def test_arm_accessor_plus_field(self):
        # bl 0x00100020 ; ldr r0,[r0,#0x5c] ; bx lr   (bl at 0x00100000: PC = addr + 8)
        code = arm_image([0xEB000006, 0xE590005C, 0xE12FFF1E])
        ctx = make_ctx(code, names={0x00100020: "Os_GetGameWork"})
        p = propose_at(code, BASE, "arm", ctx)
        self.assertEqual(p["name"], "Os_GetGameWork_Field0x5C")

    def test_thumb_field_getter(self):
        # ldr r0,[r0,#4] ; bx lr   (imm5 = 1, scaled by 4 for word loads)
        code = thumb_image([0x6840, 0x4770])
        self.assertEqual(propose_at(code, BASE, "thumb", make_ctx(code))["name"],
                         "Obj_GetU32At0x4")

    def test_thumb_constant(self):
        # movs r0,#0 ; bx lr
        code = thumb_image([0x2000, 0x4770])
        self.assertEqual(propose_at(code, BASE, "thumb", make_ctx(code))["name"], "ReturnsZero")

    def test_thumb_forwarder(self):
        # push {r4,lr} ; bl 0x00100022 ; pop {r4,pc}
        # The bl sits at 0x00100002 (right after the 2-byte push), and a Thumb bl branches to
        # PC + offset with PC = the instruction's own address + 4, so the callee is 0x00100022.
        code = thumb_image([0xB510, 0xF000, 0xF80E, 0xBD10])
        ctx = make_ctx(code, names={0x00100022: "Ui_Bar_StartFadeIn"})
        self.assertEqual(propose_at(code, BASE, "thumb", ctx)["name"],
                         "Ui_Bar_StartFadeInThunk")

    def test_class_prefix_from_vtable_siblings(self):
        # ldr r0,[r0,#0x10] ; bx lr, with three named Ui_Overlay_* siblings in the same vtable
        code = arm_image([0xE5900010, 0xE12FFF1E])
        ctx = make_ctx(code, names={
            0x00100000: "maybe_Unnamed",
            0x00100100: "Ui_Overlay_ApplySlotSetup",
            0x00100110: "Ui_Overlay_Update",
            0x00100120: "Ui_Overlay_Draw",
        }, vtables={0x00100000: "0x007E7000", 0x00100100: "0x007E7000",
                    0x00100110: "0x007E7000", 0x00100120: "0x007E7000"})
        p = propose_at(code, BASE, "arm", ctx)
        self.assertEqual(p["name"], "Ui_Overlay_GetU32At0x10")
        self.assertIn("Ui_Overlay_ApplySlotSetup", p["evidence"])

    def test_two_siblings_are_not_enough_for_a_class_prefix(self):
        code = arm_image([0xE5900010, 0xE12FFF1E])
        ctx = make_ctx(code, names={
            0x00100000: "maybe_Unnamed",
            0x00100100: "Ui_Overlay_ApplySlotSetup",
            0x00100110: "Ui_Overlay_Update",
        }, vtables={0x00100000: "0x007E7000", 0x00100100: "0x007E7000",
                    0x00100110: "0x007E7000"})
        self.assertEqual(propose_at(code, BASE, "arm", ctx)["name"], "Obj_GetU32At0x10")


# ---------------------------------------------------------------------------------------------
# synthetic: the cases that must be left alone
# ---------------------------------------------------------------------------------------------
class SyntheticRejections(unittest.TestCase):
    def test_conditional_branch_is_not_a_return(self):
        # push {r4,lr} ; cmp r1,#0 ; beq 0x00100010 ; ldrb r1,[r1] ; ...
        code = arm_image([0xE92D4010, 0xE3510000, 0x0A000009, 0xE5D10000])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_conditional_mov_is_not_a_constant_return(self):
        # movne r0,#0 ; bx lr  (returns 0 only when Z is clear: not a constant returner)
        code = arm_image([0x13A00000, 0xE12FFF1E])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_getter_from_another_register_is_not_a_field_getter(self):
        # ldr r0,[r1,#0x10] ; bx lr
        code = arm_image([0xE5910010, 0xE12FFF1E])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_setter_from_another_register_is_not_a_field_setter(self):
        # str r1,[r2,#0x10] ; bx lr
        code = arm_image([0xE5821010, 0xE12FFF1E])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_two_callees_are_not_a_pure_forwarder(self):
        # push {r4,lr} ; bl 0x00100020 ; pop {r4,lr} ; b 0x00100040  (destructor + deallocator)
        code = arm_image([0xE92D4010, 0xEB000005, 0xE8BD4010, 0xEA00000B])
        ctx = make_ctx(code, names={0x00100020: "Ui_Object_DtorBase",
                                    0x00100040: "Os_Free"})
        self.assertIsNone(propose_at(code, BASE, "arm", ctx))

    def test_call_then_constant_is_not_a_forwarder(self):
        # push {r4,lr} ; bl 0x00100020 ; mov r0,#1 ; pop {r4,pc}
        code = arm_image([0xE92D4010, 0xEB000005, 0xE3A00001, 0xE8BD8010])
        ctx = make_ctx(code, names={0x00100020: "Script_ReturnTop"})
        self.assertIsNone(propose_at(code, BASE, "arm", ctx))

    def test_tail_call_into_itself_is_not_a_thunk(self):
        # b 0x00100000 (a jump to its own entry, not a forwarder)
        code = arm_image([0xEAFFFFFE])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code)))

    def test_push_then_branch_is_not_an_empty_stub(self):
        # push {r4,lr} ; b 0x00100020  (a tail call, not a no-op)
        code = arm_image([0xE92D4010, 0xEA000005])
        ctx = make_ctx(code, names={0x00100020: "Actor_Update"})
        p = propose_at(code, BASE, "arm", ctx)
        self.assertEqual(p["name"], "Actor_UpdateThunk")

    def test_disagreeing_disassembly_blocks_the_proposal(self):
        code = arm_image([0xE5900010, 0xE12FFF1E])
        self.assertIsNone(propose_at(code, BASE, "arm", make_ctx(code), text=NeverAgrees()))


# ---------------------------------------------------------------------------------------------
# real functions, checked by hand against asm/text and the raw bytes
# ---------------------------------------------------------------------------------------------
# (address, declared mode, expected decoded sequence, expected proposed name or None)
# The sequence is what the tool decodes after the asm/text cross-check; for the two mode traps it
# is the garbage the wrong mode produces, which is exactly why no rule may match it.
REAL = [
    # --- the 18 forwarders in R_T01.json -----------------------------------------------------
    (0x00101AA0, "thumb", "push {r4, lr}; bl 0x00100F04; pop {r4, pc}", "maybe_Thunk_Call00100F04"),
    (0x0014DBAC, "thumb", "bl 0x0063B368; pop {r3, pc}", "Camera_GetHeadingAngleThunk"),
    (0x0022213C, "arm", "push {r4, lr}; bl 0x006C47BC; pop {r4, pc}", "maybe_Thunk_Call006C47BC"),
    (0x00222B48, "arm", "push {r4, lr}; bl 0x006C47BC; pop {r4, pc}", "maybe_Thunk_Call006C47BC"),
    (0x0022411C, "arm", "push {r4, lr}; bl 0x00574428; pop {r4, pc}", "maybe_Thunk_Call00574428"),
    (0x002BDFEC, "arm", "push {r4, lr}; bl 0x00180910; pop {r4, pc}", "maybe_Thunk_Call00180910"),
    (0x002BFA68, "thumb", "b 0x0022CECC", "Actor_TrySelectIdleAnimationThunk"),
    (0x002D1588, "arm", "push {r4, lr}; bl 0x006C8108; pop {r4, pc}", "maybe_Thunk_Call006C8108"),
    (0x002D1804, "arm", "push {r4, lr}; bl 0x006C8108; pop {r4, pc}", "maybe_Thunk_Call006C8108"),
    (0x002D1F1C, "arm", "push {r4, lr}; bl 0x006C8108; pop {r4, pc}", "maybe_Thunk_Call006C8108"),
    (0x0042164C, "thumb", "bl 0x0010EBE4; pop {r3, r4, r5, pc}", "maybe_Thunk_Call0010EBE4"),
    (0x00440308, "arm", "push {r4, lr}; bl 0x001CEE24; pop {r4, pc}", "maybe_Thunk_Call001CEE24"),
    (0x00479288, "thumb", "b 0x001A6768", "Ui_Object_DtorBaseThunk"),
    (0x0047E4CC, "thumb", "b 0x001EBC68", "Sound_PlaySeByIdThunk"),
    (0x005248B0, "arm", "push {r4, lr}; bl 0x0052E08C; pop {r4, pc}", "Fx_ApplyParticleStateThunk"),
    (0x005248C0, "arm", "push {r4, lr}; bl 0x0052E08C; pop {r4, pc}", "Fx_ApplyParticleStateThunk"),
    (0x0060E5A8, "thumb", "b 0x0017BBFC", "Ui_Bar_StartFadeInThunk"),
    (0x0063E064, "arm", "push {r4, lr}; bl 0x00713C7C; pop {r4, pc}", "maybe_Thunk_Call00713C7C"),
    # --- mode traps: the two disassemblers disagree, so no rule may match --------------------
    # asm/text prints Thumb "ands r0, r2" here; the bytes are ARM push {r4,lr}.  The tool falls
    # back to Thumb (the sweep's mode), gets garbage, and no rule matches it.
    (0x00102B90, "arm", ".word 0x00004010; .word 0xE92D14C0; .word 0xEB000FC0; b 0x00102EDE", None),
    # Ghidra says Thumb; the bytes are ARM ldr fp,[pc,#0x514] (a 2920-byte sound function).
    # Neither mode can be confirmed, so the function is refused outright.
    (0x00115410, "thumb", None, None),
]


class RealFunctions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.ctx = T.build_context()
        wanted = set()
        for addr, _mode, _seq, _name in REAL:
            wanted.update(range(addr, addr + T.MAX_SCAN, 2))
        cls.text = T.AsmText(wanted)

    def test_decoded_sequences(self):
        for addr, mode, expected, _name in REAL:
            if expected is None:
                continue
            with self.subTest(address=f"0x{addr:08X}"):
                analysis = T.analyse(self.ctx["code"], self.text, addr, mode)
                self.assertEqual(T.sequence(analysis.instructions), expected)

    def test_proposals(self):
        for addr, mode, _seq, expected in REAL:
            with self.subTest(address=f"0x{addr:08X}"):
                analysis = T.analyse(self.ctx["code"], self.text, addr, mode)
                if expected is None:
                    # Either the decode is refused (asm/text disagrees) or no rule matches.
                    if analysis.terminal is not None:
                        self.assertIsNone(T.propose(addr, analysis, self.ctx))
                    continue
                self.assertIsNotNone(analysis.terminal, "decode refused")
                proposal = T.propose(addr, analysis, self.ctx)
                self.assertIsNotNone(proposal, "no rule matched")
                self.assertEqual(proposal["name"], expected)

    def test_mode_traps_are_refused_by_the_cross_check(self):
        # 0x00102B90: asm/text is in Thumb mode there, so the ARM decode cannot be confirmed and
        # the Thumb fallback produces garbage that matches no rule.
        analysis = T.analyse(self.ctx["code"], self.text, 0x00102B90, "arm")
        self.assertIsNotNone(analysis.terminal)
        self.assertIsNone(T.propose(0x00102B90, analysis, self.ctx))
        # 0x00115410: Ghidra says Thumb, the bytes are ARM; neither decode can be confirmed.
        analysis = T.analyse(self.ctx["code"], self.text, 0x00115410, "thumb")
        self.assertIsNone(analysis.terminal)
        self.assertIn("asm/text", analysis.reason)


# ---------------------------------------------------------------------------------------------
# the generated batch
# ---------------------------------------------------------------------------------------------
class BatchFile(unittest.TestCase):
    def test_batch_is_valid(self):
        if not T.OUT.exists():
            self.skipTest("R_T01.json not generated yet")
        import json
        proposals = json.loads(T.OUT.read_text(encoding="utf-8"))
        ctx = T.build_context()
        self.assertEqual(T.validate(proposals, ctx), [])
        self.assertGreater(len(proposals), 0)

    def test_every_entry_has_evidence_and_a_previous_name(self):
        if not T.OUT.exists():
            self.skipTest("R_T01.json not generated yet")
        import json
        for entry in json.loads(T.OUT.read_text(encoding="utf-8")):
            self.assertTrue(entry["evidence"])
            self.assertTrue(entry["previous_name"])
            self.assertIn(entry["change"], ("corrected", "confirmed", "kept_maybe"))
            self.assertEqual(entry["confidence"] < 0.5,
                             entry["name"].startswith("maybe_"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
