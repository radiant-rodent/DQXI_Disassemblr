"""Test-only input hook for emulator runs (ported from the translation project).

The retail executable has no way to accept input from a script: the emulator's own window
can only be driven by a recorded ``.ctm`` movie.  The translation project solved this with a
small code cave that ORs a "mailbox" in RAM into every HID pad entry the game reads, so a
test can press buttons through emulator memory writes (Azahar RPC).  This module is that
idea, copied from ``..\\3DS_Translate\\dq11tool\\testhook.py`` (read-only
there) and reduced to the input hook -- the debug probes are not needed here.

It is **never part of a shipped mod**.  It exists so ``tests/emu`` can drive menus and
dialogue without pixel-perfect movie timing, and it doubles as the "native code edit" proof:
a build with this hook is a real, non-trivial change to ``code.bin`` (and therefore to the
exported ``code.ips``) whose effect is directly observable -- live presses work.

Hook site (same executable as the translation project's JP build; verified by the matching
``code_jp.bin`` hash):

    0x11AD3C  ldr r1, [sp, #0x20]   (end of nn::hid::PadReader::Read)
    0x724F00  code cave in the zero-filled .text tail (also used by the grammar pass in the
              translation build; our retail executable leaves it unused)

When the game returns pad entries, the hook ORs the hold/trigger words from MAILBOX into
each entry and counts reads in MAILBOX+16.  A "pulse" (MAILBOX+20 buttons, MAILBOX+24 count)
is held for exactly ``count`` reads, which is one press at the game's own frame rate.
"""
from __future__ import annotations

BASE = 0x100000
RETURN_AT = 0x11AD3C
ORIGINAL = bytes.fromhex("20109de5")         # ldr r1, [sp, #0x20]
HOOK = 0x724F00
MAILBOX = 0x839F00
CODE = bytes.fromhex(
    "1d402de988009fe5002090e5043090e5184090e5000054e3050000da000059e3030000da014044e2184080e5"
    "144090e5042082e10040a0e3000059e3044080c5090054e10c0000aa04c281e000e09ce502e08ee100e08ce5"
    "04e09ce503e08ee104e08ce50ce090e501001ee308e090150ce08c15014084e2f0ffffea104090e5014084e2"
    "104080e51d40bde820109de51eff2fe1009f8300")
CALL = bytes.fromhex("6f2818eb")             # bl HOOK (from RETURN_AT)


def apply(code: bytes) -> bytes:
    """Return ``code`` with the input hook installed; raises if the target is not retail."""
    out = bytearray(code)
    r, h = RETURN_AT - BASE, HOOK - BASE
    if out[r:r + 4] != ORIGINAL:
        raise ValueError("input hook: PadReader::Read not found at the expected address "
                         "(different game version?)")
    if any(out[h:h + len(CODE)]):
        raise ValueError("input hook: code cave at 0x%X is not free" % HOOK)
    out[h:h + len(CODE)] = CODE
    out[r:r + 4] = CALL
    return bytes(out)
