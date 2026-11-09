"""Test-only heap tweak: leave a hole at the end of the linear heap for the text log ring.

Ported from ``..\\3DS_Translate\\dq11tool\\memfix.py`` (read-only there).  Only
``reserve_tail`` is needed here; the translation build's heap-growth patches are not.

The game carves the linear heap into heaps at boot, one after another.  Small-block allocator
1's fallback heap is at ``0x7F4F??``; allocator 2 (UI layouts) starts after it and ends at the
end of the linear heap.  ``reserve_tail(code, N)`` shrinks allocator 1 by N bytes: allocator 2
then starts and ends N bytes lower, so the last N bytes of the linear heap are never handed
out.  That hole is where ``textlog`` puts its 256 KB ring, so logging cannot overwrite a pane
buffer (the 2way UI needs more of the heap than 2D, so without this the ring overlaps it).
"""
from __future__ import annotations

import struct

BASE = 0x100000
DONOR_LITERAL = 0x103534     # .word 0x1DC340: fallback heap of small-block allocator 1
DONOR_SIZE = 0x1DC340
MAX_AMOUNT = 0x140000        # translation project's safe upper bound (leaves ~650 KB)


def reserve_tail(code: bytes, amount: int) -> bytes:
    """Take ``amount`` bytes (multiple of 64 KiB) out of the linear heap, for a test ring."""
    if amount <= 0:
        return code
    if amount % 0x10000:
        raise ValueError("reserve must be a multiple of 64 KiB")
    out = bytearray(code)
    donor = struct.unpack_from("<I", out, DONOR_LITERAL - BASE)[0]
    if not (DONOR_SIZE - MAX_AMOUNT <= donor <= DONOR_SIZE):
        raise ValueError("heap setup literal not as expected (different game version?)")
    if donor - amount < DONOR_SIZE - MAX_AMOUNT - 0x40000:
        raise ValueError("reserve too big for allocator 1's fallback heap")
    struct.pack_into("<I", out, DONOR_LITERAL - BASE, donor - amount)
    return bytes(out)
