---
lane: export
after: X1_export
---
Unblock the CIA export target.

Owns: `tools/export_mod.py` (cia target only), new `tools/ctr_cia.py`, tests, `docs/EXPORT.md`.

`..\3DS_Translate\dq11tool\ctr\cia.py` (`build_cia(src_3ds, out_cia)`) already builds
CIAs for this exact game from a .3ds, and its CLAUDE.md describes how it's checked byte-for-byte
against the browser patcher. Read it and `dq11tool/ctr/build.py`, then port/adapt (credit the
source) into `tools/ctr_cia.py` so `export_mod.py --target cia` builds a CIA from the patched .3ds.
Replace the BLOCKED stub. Tests: CIA structure parses (header, cert chain, ticket, TMD, content
hashes match). If the translation project documents how its CIAs are installed (CFW, sigpatches),
put that in docs/EXPORT.md. If A_emu_harness exists, check Azahar can load the CIA.
