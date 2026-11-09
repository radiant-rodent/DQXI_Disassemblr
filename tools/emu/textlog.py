"""Test-only text logger + host-side recorder (ported from the translation project).

Why this exists
---------------
``tests/emu`` must prove that an edited dialogue line is what the *game* shows, not merely
that the bytes reached RAM.  The translation project's approach is a small ARM code cave that
copies every string a layout pane receives into a ring buffer in the unused tail of the
linear heap; ``emutest/textrec.py`` drains that ring over the emulator's RPC socket and writes
``events.jsonl`` with the game time of each string plus a screenshot.

We reuse the idea, reduced to what this project needs:

* the two pane ``SetString`` functions (0x53F940 NUL-terminated, 0x53F9EC length form) end
  with ``ldrb r0, [r4, #0xd0]`` (r4 = pane).  That instruction becomes ``bl stub``; the stub
  calls the logger, recounts the pane text, and executes the replaced load.
* the logger itself (``logwrap``/``tlog``) is the translation project's, with the English
  grammar pass replaced by a no-op ``bx lr`` -- Japanese text has no grammar markers, so the
  raw pane text is the displayed text.
* records carry the pane address/name, the HID tick (game seconds), a sequence number and the
  UTF-16 text.  The ring lives in 256 KB the test build leaves unused
  (``memfix.reserve_tail``); the UI heap keeps its normal size.

This module is **never exported**.  It only runs in the emulator test builds built by
``tests/emu``.  It is ported from ``..\\3DS_Translate\\dq11tool\\textlog.py``
and ``emutest\\textrec.py`` (read-only there); credit to that project.

Layout (identical to the source project so its tools can be compared):

    CTL 0x839F20: +0 ring address, +4 ring size, +8 write offset, +12 seq,
                  +16 HID tick address
    record: u16 size, u16 units, u32 seq, u32 frame, u32 pane, u64 tick,
            u16 start, u8 phase, u8 pad, char[24] name, UTF-16 text
"""
from __future__ import annotations

import json
import os
import struct
import threading
import time

BASE = 0x100000
CAVE = 0x724C00              # .text tail (free in the retail executable)
CAVE_END = 0x724F00          # the input hook starts here
STUB = 0x724380              # grammar pass cave in the translation build; free here
CTL = 0x839F20
FRAME = 0x839F10             # CTL - 16
HID_TICK = 0x10002000
RING_RESERVE = 0x40000       # 256 KiB
CACHE = 0x400                # dedupe cache at the end of the reserve
MAX_UNITS = 0x400
HEADER = 52

# The logger body is the translation project's, with GFIX resolved to a local `bx lr`.
SOURCE = r"""
logwrap:
    push {r0, r1, r8, r9, lr}
    mov r2, #0
    bl tlog
    mov r8, r0
    mov r9, r1
    ldr r0, [sp]
    ldr r1, [sp, #4]
    bl GFIX
    cmp r9, #0
    beq lw_out
    mov r2, #1
    mov r3, r8
    bl tlog
lw_out:
    pop {r0, r1, r8, r9, pc}

tlog:
    push {r4-r11, lr}
    ldr r6, ctl_addr
    ldr r7, [r6]
    cmp r7, #0
    beq t_out0
    ldr r8, [r4, #0xa4]
    ldrh r9, [r4, #0xcc]
    cmp r8, #0
    beq t_out0
    mov r10, #0
    mov r0, #0
th_loop:
    cmp r10, r9
    bhs th_done
    cmp r10, #MAXU
    bhs th_done
    add ip, r8, r10, lsl #1
    ldrh ip, [ip]
    cmp ip, #0
    beq th_done
    add r0, r0, r0, lsl #5
    eor r0, r0, ip
    add r10, r10, #1
    b th_loop
th_done:
    add r0, r0, r10
    cmp r2, #0
    beq t_dedupe
    cmp r0, r3
    beq t_out0
    b t_write
t_dedupe:
    ldr r11, [r6, #-16]
    ldr r1, [r6, #4]
    add r1, r7, r1
    eor ip, r4, r4, lsr #5
    mov ip, ip, lsr #4
    and ip, ip, #31
    add ip, ip, ip, lsl #1
    add r1, r1, ip, lsl #3
    ldr ip, [r1]
    cmp ip, r4
    bne t_newslot
    ldr ip, [r1, #4]
    str r11, [r1, #4]
    sub ip, r11, ip
    cmp ip, #2
    bhi t_reset
    ldr ip, [r1, #8]
    cmp ip, r0
    beq t_out0
    ldr ip, [r1, #12]
    cmp ip, r0
    beq t_out0
    ldr ip, [r1, #16]
    cmp ip, r0
    beq t_out0
    ldr ip, [r1, #20]
    cmp ip, r0
    beq t_out0
    ldr ip, [r1, #16]
    str ip, [r1, #20]
    ldr ip, [r1, #12]
    str ip, [r1, #16]
    ldr ip, [r1, #8]
    str ip, [r1, #12]
    str r0, [r1, #8]
    b t_write
t_newslot:
    str r4, [r1]
    str r11, [r1, #4]
t_reset:
    str r0, [r1, #8]
    mvn ip, #0
    str ip, [r1, #12]
    str ip, [r1, #16]
    str ip, [r1, #20]
t_write:
    mov r3, r0
    add r1, r10, r10
    add r1, r1, #HDR3
    bic r1, r1, #3
    ldr ip, [r6, #4]
    ldr r11, [r6, #8]
    add lr, r11, r1
    cmp lr, ip
    bls t_fits
    add lr, r11, #2
    cmp lr, ip
    movls lr, #0
    strhls lr, [r7, r11]
    mov r11, #0
t_fits:
    add lr, r7, r11
    strh r1, [lr]
    strh r10, [lr, #2]
    ldr ip, [r6, #12]
    str ip, [lr, #4]
    add ip, ip, #1
    str ip, [r6, #12]
    ldr ip, [r6, #-16]
    str ip, [lr, #8]
    str r4, [lr, #12]
    mov r0, #0
    str r0, [lr, #16]
    str r0, [lr, #20]
    ldr ip, [r6, #16]
    cmp ip, #0
    ldrne r0, [ip]
    strne r0, [lr, #16]
    ldrne r0, [ip, #4]
    strne r0, [lr, #20]
    strh r5, [lr, #24]
    strb r2, [lr, #26]
    mov r0, #0
    strb r0, [lr, #27]
    add r9, lr, #28
tn_loop:
    add ip, r4, #0x80
    ldrb ip, [ip, r0]
    strb ip, [r9, r0]
    add r0, r0, #1
    cmp r0, #24
    blo tn_loop
    mov r0, #0
    add r9, lr, #HDR
tu_loop:
    cmp r0, r10
    bhs tu_done
    add ip, r8, r0, lsl #1
    ldrh ip, [ip]
    add lr, r9, r0, lsl #1
    strh ip, [lr]
    add r0, r0, #1
    b tu_loop
tu_done:
    add r11, r11, r1
    str r11, [r6, #8]
    mov r0, r3
    mov r1, #1
    pop {r4-r11, pc}
t_out0:
    mov r1, #0
    pop {r4-r11, pc}
ctl_addr:
    .word CTLADDR
gfix_noop:
    bx lr
"""

# A minimal SetString tail hook: log, recount the pane's NUL-terminated text, then execute
# the replaced instruction.  (`r5` is the text start index, `r6` the length the caller gets.)
STUB_SOURCE = r"""
stub:
    push {r0-r3, ip, lr}
    bl pane_fix
    subs r6, r0, r5
    movlo r6, #0
    pop {r0-r3, ip, lr}
    ldrb r0, [r4, #0xd0]
    bx lr

pane_fix:
    push {r4, lr}
    ldr r0, [r4, #0xa4]
    ldrh r1, [r4, #0xcc]
    cmp r0, #0
    cmpne r1, #1
    bls pf_none
    bl LOGGER
    ldr r0, [r4, #0xa4]
    mov r1, #0
pf_len:
    ldrh r2, [r0], #2
    cmp r2, #0
    addne r1, r1, #1
    bne pf_len
    strh r1, [r4, #0xce]
    mov r0, r1
    pop {r4, pc}
pf_none:
    ldrh r0, [r4, #0xce]
    pop {r4, pc}
"""

HOOKS = ((0x53F9D8, bytes.fromhex("d000d4e5")),
         (0x53FA74, bytes.fromhex("d000d4e5")))


def _assemble(src: str, at: int) -> bytes:
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_ARM, keystone.KS_MODE_ARM)
    return bytes(ks.asm(src, at)[0])


def _bl(at: int, target: int) -> bytes:
    return struct.pack("<I", 0xEB000000 | (((target - at - 8) >> 2) & 0xFFFFFF))


def apply(code: bytes) -> bytes:
    """Install the text logger in a retail (or test-hook) executable."""
    out = bytearray(code)
    c = CAVE - BASE
    body = _assemble(
        SOURCE.replace("GFIX", "gfix_noop").replace("CTLADDR", f"{CTL:#x}")
        .replace("#MAXU", f"#{MAX_UNITS:#x}").replace("#HDR3", f"#{HEADER + 3}")
        .replace("#HDR", f"#{HEADER}"), CAVE)
    if len(body) > CAVE_END - CAVE:
        raise ValueError(f"text log: code too big ({len(body)} bytes; cave has "
                         f"{CAVE_END - CAVE})")
    if any(out[c:c + len(body)]):
        raise ValueError(f"text log: code cave at {CAVE:#x} is not free")
    out[c:c + len(body)] = body
    stub = _assemble(STUB_SOURCE.replace("LOGGER", f"{CAVE:#x}"), STUB)
    s = STUB - BASE
    if any(out[s:s + len(stub)]):
        raise ValueError(f"text log: stub cave at {STUB:#x} is not free")
    out[s:s + len(stub)] = stub
    for at, original in HOOKS:
        h = at - BASE
        if out[h:h + 4] != original:
            raise ValueError(f"text log: SetString tail at {at:#x} is not the retail "
                             "instruction (different game version?)")
        out[h:h + 4] = _bl(at, STUB)
    return bytes(out)


def decode(rec: bytes) -> dict:
    """Decode one ring record (see the layout in the module docstring)."""
    size, n, seq, frame, pane, tick, start, phase = struct.unpack_from("<HHIIIQHB", rec)
    name = rec[28:52].split(b"\0")[0].decode("ascii", "replace")
    text = rec[HEADER:HEADER + 2 * n].decode("utf-16-le", "replace")
    return {"size": size, "units": n, "seq": seq, "frame": frame, "pane": pane,
            "tick": tick, "start": start, "phase": phase, "name": name, "text": text}


def shown(text: str) -> str:
    """Readable form of a pane string: control codes made visible, braces kept literal."""
    out = []
    for ch in text:
        if ch == "\r":
            out.append("{CR}")
        elif ch == "\x1f":
            out.append("{PAGE}")
        elif ch == "\x01":
            out.append("{ruby:")
        elif ch == "\x02":
            out.append("|")
        elif ch == "\x03":
            out.append("}")
        elif ch == "\x04":
            out.append("{v:")
        elif ord(ch) < 0x20:
            out.append("{c%02X}" % ord(ch))
        else:
            out.append(ch)
    return "".join(out)


UI_HEAP = 0x7F5144          # allocator 2's fallback heap object: +4 size, +0x10 base
TICKS = 268111856           # HID ticks per emulated second
CHUNK = 0x7000


def ring_address(read) -> int:
    size, = struct.unpack("<I", read(UI_HEAP + 4, 4))
    base, = struct.unpack("<I", read(UI_HEAP + 0x10, 4))
    if not (0x30000000 <= base < 0x40000000 and 0x100000 <= size < 0x800000):
        raise RuntimeError(f"UI heap not set up yet (base {base:#x}, size {size:#x})")
    return base + size


class TextRecorder:
    """Drain the game-side ring from a background thread and record text + screenshots.

    ``rpc`` is a fresh AzaharRPC connection (the session has its own socket, and the
    translation project's recorder does the same so live input never competes for it).
    """

    def __init__(self, rpc, session, out: str, shots: bool = True,
                 poll: float = 0.02, settle: float = 0.30):
        self.rpc = rpc
        self.s = session
        self.out = out
        self.shots = shots
        self.poll = poll
        self.settle = settle
        self.events: list[dict] = []
        self.count = 0
        self.dropped = 0
        self.shot_files: list[str] = []
        self._pending = None
        self._stop = threading.Event()
        self._th = None
        self._lock = threading.RLock()
        os.makedirs(os.path.join(out, "shots"), exist_ok=True)
        self._fp = open(os.path.join(out, "events.jsonl"), "w", encoding="utf-8")

    def enable(self):
        if self.rpc.read_memory(CTL, 4) is None:
            raise RuntimeError("RPC read failed")
        code = self.rpc.read_memory(CAVE, 8)
        if not code or not any(code):
            raise RuntimeError("this build has no text logger")
        ring = ring_address(self.rpc.read_memory)
        self.ring, self.size = ring, RING_RESERVE - CACHE
        cur = struct.unpack("<5I", self.rpc.read_memory(CTL, 20))
        if cur[0] == ring:
            self.rpos, self.seq = cur[2], cur[3]
            return
        self.rpc.write_memory(ring + self.size, bytes(CACHE))
        self.rpc.write_memory(CTL + 4, struct.pack("<4I", self.size, 0, 0, HID_TICK))
        self.rpc.write_memory(CTL, struct.pack("<I", ring))
        self.rpos, self.seq = 0, 0

    def start(self):
        self.enable()
        self._th = threading.Thread(target=self._run, daemon=True)
        self._th.start()
        return self

    def stop(self):
        self._stop.set()
        if self._th:
            self._th.join(5)
        try:
            self.drain()
        except Exception as exc:      # emulator already gone: keep the records we have
            print("textlog: final drain failed:", exc, flush=True)
        finally:
            self._fp.close()

    def _run(self):
        while not self._stop.is_set():
            try:
                self.drain()
            except Exception as exc:      # emulator gone / RPC timeout: keep trying
                print("textlog:", exc, flush=True)
                time.sleep(0.5)
            time.sleep(self.poll)

    def _read(self, off: int, n: int) -> bytes:
        out = b""
        while n > 0:
            k = min(n, CHUNK)
            data = self.rpc.read_memory(self.ring + off, k)
            if data is None:
                raise RuntimeError("ring read failed")
            out += data
            off, n = off + k, n - k
        return out

    def _records(self, start: int, end: int, first_seq: int):
        spans = ([(start, self._read(start, end - start))] if start <= end else
                 [(start, self._read(start, self.size - start)), (0, self._read(0, end))])
        out, want = [], first_seq
        for _off, data in spans:
            o = 0
            while o + 2 <= len(data):
                sz, = struct.unpack_from("<H", data, o)
                if sz == 0:
                    break
                if sz < HEADER or o + sz > len(data):
                    return None
                rec = decode(data[o:o + sz])
                if rec["seq"] != want:
                    return None
                out.append(rec)
                want += 1
                o += sz
        return out

    def drain(self):
        with self._lock:
            pos, seq = struct.unpack("<II", self.rpc.read_memory(CTL + 8, 8))
            if seq == self.seq:
                self._settled_shot()
                return
            recs = (self._records(self.rpos, pos, self.seq)
                    if seq - self.seq < 20000 else None)
            if recs is None:
                recs = [r for r in (self._records(0, pos, 0) or []) if r["seq"] >= self.seq]
                lost = (recs[0]["seq"] if recs else seq) - self.seq
                self.dropped += lost
                self._emit({"lost": lost, "t": None})
            self.rpos = pos
            if recs:
                self.seq = recs[-1]["seq"] + 1
            for rec in recs:
                self._emit({"seq": rec["seq"], "t": round(rec["tick"] / TICKS, 3),
                            "frame": rec["frame"], "pane": f"{rec['pane']:08x}",
                            "name": rec["name"],
                            "phase": "resolved" if rec["phase"] else "raw",
                            "start": rec["start"], "text": rec["text"],
                            "shown": shown(rec["text"])})
            if recs:
                self._pending = recs[-1]["tick"] / TICKS

    def _emit(self, event: dict):
        event["shot"] = None
        if "seq" in event:
            self.count += 1
        self.events.append(event)
        self._fp.write(json.dumps(event, ensure_ascii=False) + "\n")
        self._fp.flush()

    def _settled_shot(self):
        if self._pending is None or not self.shots:
            return
        if self.now() - self._pending >= self.settle:
            self._pending = None
            self.shot("text")

    def now(self) -> float:
        return struct.unpack("<Q", self.rpc.read_memory(HID_TICK, 8))[0] / TICKS

    def shot(self, tag: str = "") -> str | None:
        with self._lock:
            if self._pending is not None:
                self._pending = None
            name = f"{len(self.shot_files):03d}_{tag}.png" if tag else f"{len(self.shot_files):03d}.png"
            path = os.path.join(self.out, "shots", name)
            ok = self.s.shot(path)
            if ok:
                self.shot_files.append(path)
                self._emit({"shot": path})
                return path
            return None

    def find(self, needle: str) -> list[dict]:
        """Events whose text contains ``needle`` (raw or readable form)."""
        return [e for e in self.events
                if "text" in e and (needle in e["text"] or needle in e.get("shown", ""))]
