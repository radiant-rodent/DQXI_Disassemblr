# X4_cia — unblock the CIA export target

**Status: completed (with the honest limits in §7; no real 3DS install was possible).**

Resumed a stopped worker. What already existed on disk: `tools/ctr_cia.py` (732 lines, written
21:07) — a port of `..\3DS_Translate\dq11tool\ctr\cia.py` + `formats.py` — and one
successful manual run of it (`build/DQXI.3ds` → a 2,685,129,728-byte CIA, `verify_cia` clean),
recorded in `orchestration/logs/X4_cia.log` before the quota ran out. Nothing else: `export_mod.py`
still had the BLOCKED stub, no CIA test, `docs/EXPORT.md` still said "CIA is not implemented", no
done report and no log entry. No prior worker code was discarded: the existing port is correct and
became the shipped builder, after the hardening below.

---

## 1. What the CIA target now does

```powershell
python tools/export_mod.py --target cia        # out/cia/DQXI_modded.cia + README.txt
python tools/export_mod.py --target all        # luma + 3ds + cia, reusing the built .3ds
```

- `--target cia` **builds the patched `.3ds` first** (a CIA must describe the patched contents),
  then packages that exact image. `--target all` reuses the image already built for the `3ds`
  target instead of repacking 4 GiB twice.
- `out/cia/DQXI_modded.cia` is the archive; `out/cia/README.txt` carries the install steps and the
  modder's name/version/author. A stale `BLOCKED.md` from older exports is deleted, and
  `out/EXPORT_REPORT.json` gains a `targets.cia` block: size, SHA-256, title ID, certificate /
  ticket / TMD / meta / content sizes, per-content SHA-256, the source `.3ds` and its hash, and
  `"signed": false`.
- `--no-rom` combined with `cia` (or `all`) is refused before any work:
  *"--no-rom cannot be combined with the CIA target: a CIA is made from the full .3ds image…"*.
- `run_export.bat` option 5 now says "installable CIA (needs a CFW console + FBI)", runs the real
  target and points at FBI instead of at the old blocked note.

## 2. How the archive is built (and why each part is legitimate)

`tools/ctr_cia.py` writes a standard CTR Importable Archive:

| Section | What it is here |
|---|---|
| Header | 0x2020 bytes; section sizes; content mask `0xC0` (contents 0 and 1) |
| Certificate chain | 0xA00 bytes copied verbatim from a **system-update CIA inside the cartridge's own update partition** (partition 7, falling back to 6, then `original/partitions/update_*.ncch`): CA (RSA-4096), CP (TMD signer), XS (ticket signer). Genuine Nintendo certificates — no key is invented. |
| Ticket | 0x350 bytes, **fakesigned**: RSA signature blanked, title key zeroed (contents are stored unencrypted), ticket ID / title ID / title version / license type / console ID set for `0004000000199200`, not console-locked. |
| TMD | 0xB04 + 2·0x30 bytes, **fakesigned**: CTR title type, save-data size from the ExHeader (0x80000), title version 0, boot content 0, two content records (game `flags 0`, manual `flags 0x4000` = optional/CFA), each with its SHA-256; content-info and chunk-record hashes are computed and stored. |
| Contents | Content 0 = the patched NCCH partition 0 (2,683,592,704 B); content 1 = the retail e-manual CFA (1,507,328 B). Payload bytes are copied from the rebuilt `.3ds`, never re-encoded. |
| Meta | 0x3AC0 bytes: dependency list from ExHeader `0x40..0x1C0`, core version 2, the 0x36C0 SMDH icon from the ExeFS at `0x400`. |

The design follows the translation project's proven builder exactly: **unencrypted contents + zero
title key + blank signatures**, which is what a decrypted dump can honestly produce. A new guard
refuses an *encrypted* NCCH (`NCCH flags[7] bit 2` clear) instead of writing a zero-key ticket for
ciphertext, and `verify_cia` now also checks that the certificate chain is non-empty, 64-byte
aligned and contains a `Root-CA` issuer.

## 3. Evidence — the port is the proven builder, byte for byte

Built from the same patched image with our module and with the reference module:

```
tools/ctr_cia.py       -> 2,685,129,728 B  SHA-256 517d38cdc920183a0afd6f813ace4095d024cce26d3bf8ba97d25eb822d5424d
dq11tool/ctr/cia.py    -> 2,685,129,728 B  SHA-256 517d38cdc920183a0afd6f813ace4095d024cce26d3bf8ba97d25eb822d5424d
identical: True
```

The reference project's `CLAUDE.md` requires its Python `.cia` output to match its browser patcher
(`docs/dq11patch.js`) byte for byte, and the JS `buildCia`/`ciaTicket`/`ciaTmd` code is the same
algorithm; so the port sits on the exact implementation that project ships to players. Our extra
work is integration + independent verification, not a second opinion on the format.

## 4. Evidence — Azahar installed and booted the CIA

The project's own portable Azahar (`third_party/emutest/azahar/azahar.exe`, from
`A_emu_harness`) has a CLI installer (its usage string: `-i, --install [path]  Install a CIA file
at the given path`). Run on the CIA built from the **modded** image (item-table edit), launched
with `SW_SHOWNOACTIVATE`, then closed; no dialog was driven and no other Azahar was touched:

- exit after 226 s (the install plus a short boot; the process ended after the CLI install and was
  not left running);
- emulated SD card received
  `sdmc/Nintendo 3DS/…/title/00040000/00199200/content/00000000.tmd` — **byte-identical to the
  TMD inside the CIA** (`inst_tmd == tmd`), 2,916 B;
- `content/00000000/00000000.app` = 2,683,592,704 B and `00000001.app` = 1,507,328 B, each
  **SHA-256 equal to the TMD content record**;
- save-data directories were initialised (`data/00000001/{Data0,Data1,Data2,mini_0..2,system}`);
- Azahar then **booted the installed title**: log `citra_qt.cpp: BootGame: Loading per application
  config file for title 0004000000199200` and `ncch.cpp: Load: Program ID: 0004000000199200`
  (the only failed open is the *update* title `0004000e/00199200`, which is expected — no update is
  installed). It did not reach the title screen before it was closed.

So an AM/FBI-style installer accepted the ticket/TMD, wrote both contents, created save data and
loaded the title from them. That is the strongest "Azahar can load the CIA" check available here.
The machine-local evidence summary is
`third_party/emutest/runs/cia/azahar_install_proof.json`. The installed title was left in the
emulator's SD card (machine-local, 2.7 GB,
`third_party/emutest/azahar/user/sdmc/.../title/00040000/00199200/`) and in `nand/dbs/ticket.db`;
explicit-file boots (what `python -m tools.emu boot` does) are unaffected.

## 5. Files changed

**New**
- `tools/ctr_cia.py` — the builder/verifier (ported from `3DS_Translate/dq11tool/ctr/cia.py` and
  `formats.py`, credited in the module docstring; hardened as in §2). It also has a
  `build` / `verify` / `info` CLI for direct use.

**Changed**
- `tools/export_mod.py` — `cia` target implemented; module docstring target description; `--no-rom`
  guard; report fields; stale `BLOCKED.md` removal; `--target all` image reuse.
- `tests/tier4_real_world/test_scenario_9_mod_export.py` — the old
  `test_cia_target_is_blocked_not_faked` is replaced by eight CIA test methods that build a real
  CIA in `setUpClass` and parse it with the test's own reader (see §6).
- `docs/EXPORT.md` — §3 `cia` rewritten (what is inside, why it is fakesigned, FBI/Luma install
  steps, what was verified, cost), checks table row, troubleshooting rows (no-rom, encrypted dump,
  trimmed dump, FBI signature/invalid errors), not-verified item.
- `run_export.bat` — CIA menu text/steps only (was still advertising the blocked target).
- `README.md`, `docs/README.md` — one-line accuracy fixes (export now includes an installable CIA).
- `AGENT_LOG.md` — Entry 169.
- `orchestration/done/X4_cia.md` — this report.

No shared editor file (`viewer_rs/…`) was touched. Nothing in `..\3DS_Translate` was
modified (only imported read-only to compare output).

## 6. Tests

The new CIA tests in `tests/tier4_real_world/test_scenario_9_mod_export.py` (eight methods):

1. `test_cia_target_builds_a_verified_archive` — real `--target cia` run, exit 0, no
   `BLOCKED.md`, `out/cia/DQXI_modded.cia` present, report size/hash/source match, verifier and
   `parse_cia` clean, title ID, 2 contents, section sizes (0xA00 / 0x350 / 0xB64 / 0x3AC0).
2. `test_cia_header_sections_and_certificate_chain` — independent header parse, content mask
   `0xC0`, aligned content size, certificate chain 0xA00 with key ids `CA00000003`, `CP0000000b`,
   `XS0000000c` and two `Root-CA00000003` issuers.
3. `test_cia_ticket_is_fakesigned_and_names_the_game` — blank 0x100-byte signature, zero title
   key, ticket/title IDs, console ID 0, license type 0, common-key index 0.
4. `test_cia_tmd_hashes_match_and_describe_the_two_contents` — TMD title id/type/count/boot
   index/save size from ExHeader, content-info and chunk hashes, both content sizes from the NCSD
   partition table, both content SHA-256s **re-hashed from the rebuilt `.3ds`**, content 1 equal to
   the retail manual hash, NCCH magic in both contents.
5. `test_cia_meta_carries_dependencies_and_icon` — dependency list equals ExHeader `0x40..0x1C0`,
   core version 2, SMDH icon equals `original/exefs/icon`.
6. `test_cia_verifier_rejects_a_truncated_file` — a short file yields problems, not a pass.
7. `test_cia_refuses_no_rom_because_it_needs_the_full_image` — clear exit-2 error before any work.
8. `test_cia_builder_refuses_an_encrypted_image` — a minimal NCCH without the no-crypto flag is
   rejected, so a zero-key ticket can never be written for ciphertext.

Results (final code state):

```
python tests/run_all.py
Tier 1: 70/70  Tier 2: 70/70  Tier 3: 14/14  Tier 4: 69/69
TOTALS: 223/223 pass, 0 fail, 0 skip -> SUCCESS (247 s, threshold >= 161)

python tools/verify_project.py   -> OVERALL: PASS -> audit/PROJECT_VERIFICATION.json
python tools/verify.py           -> PASS: 16 manifest files + bit-matching repacked ROM
```

Manual end-to-end runs:

- empty mod → `--target cia`: exit 0, 58.8 s, `.3ds` SHA-256 = retail
  `0f04b51b…a9b74`, CIA 2,685,129,728 B, all checks clean;
- empty mod → `--target all`: exit 0, one 4 GiB build reused for luma + 3ds + cia;
- item-table mod → `--target cia` (inside the test class): both contents' hashes match the
  patched image; Azahar installed that file (§4).

## 7. Not verified / honest limits

1. **No real 3DS/2DS.** The install evidence is Azahar's AM implementation plus a full re-parse.
   Whether a given FBI + Luma version on hardware accepts it is very likely (the translation
   project distributes CIAs built by the same code to players) but **not demonstrated here**.
2. **Signatures are blank** on the ticket and TMD. This only installs with signature patches
   (Luma3DS or equivalent). Stock OFW will reject it — that is inherent, not a bug.
3. **Contents are unencrypted with a zero title key.** Valid for an installed title (the TMD
   content flags say "not encrypted") and exactly what the reference builder does. An eShop-style
   encrypted CIA would need a real ticket; not attempted.
4. **The installed title in the emulator was not played.** It booted (`Loader: Program ID
   0004000000199200`) but did not reach the title screen in the 226 s run (most of it was the
   2.7 GB install); the modded item value was not exercised.
5. **Partitions 6/7 are required** for the certificate chain. A trimmed dump cannot build a CIA;
   the error names the missing update partition. The project's `original/` keeps them.
6. **Cost**: `--target cia` writes a 4 GiB `.3ds` and a ~2.7 GB `.cia` (~7 GB peak), ~60 s here.
7. `run_export.bat` is outside the strict ownership list but was changed because it still described
   CIA as blocked; the edit is limited to the CIA text/steps.
8. **Test cost and shared scratch.** The scenario-9 class now repacks the 4 GiB image twice (once
   for `--target 3ds`, once because the standalone `--target cia` test genuinely exercises that
   target) and writes two 2.7 GB CIAs; tier 4 is ~232 s. `tools/repack_rom.py` uses
   `build/patched_input/`, the pre-existing shared scratch X1 already flagged; running this suite
   while another worker repacks a ROM can collide there.

## 8. Suggested follow-ups

1. **Real-console CIA install test** (the only missing evidence): copy `out/cia/DQXI_modded.cia` to
   a Luma3DS SD card, install with FBI, launch, confirm a modded value in-game. Record the FBI and
   Luma versions in `docs/EXPORT.md`.
2. **X3_boot_tests** should include the installed title (or install this CIA in its own emulator
   profile) so a CIA boot is part of the routine matrix, not a one-off.
3. If a **trimmed-dump** path is ever needed, derive the certificate chain from another source or
   reject early with a documented alternative (already a clear error; a UI hint would be nicer).
4. **Encrypted CIA support** would need a real ticket/title key and AES-CTR section encryption;
   nothing in this workspace has that, and it is not required for CFW use.


## 9. Independent re-check (resume verification)

**Duplicate dispatch note:** this section was written by a second session that was dispatched for
the same task while the first was finishing. It did not overwrite the report above; it re-ran the
load-bearing checks and appended its evidence here.

A second pass over the finished lane rebuilt the CIA from `build/DQXI_patched.3ds` with this
module and with `3DS_Translate/dq11tool/ctr/cia.py`: both are 2,685,129,728 B with SHA-256
`517d38cdc920183a0afd6f813ace4095d024cce26d3bf8ba97d25eb822d5424d` (byte-identical). The
0xA00 certificate chain in the produced file is byte-identical to the template CIA inside the
cartridge's update partition 7 (SHA-256 `8b4cb3e476781f477a1eb025d68876703d9b9acf9ef962f077b780cd5ca5298f`).
The files Azahar installed on its emulated SD card were re-hashed against the CIA: the TMD and
the ticket are byte-identical, and both `.app` files match their TMD records. Scenario 9 was
rerun after the final edits: `Ran 22 tests in 200.442s / OK`; `python tests/run_all.py`:
222/222 PASS; `python tools/verify_project.py`: OVERALL PASS; `python tools/verify.py`:
OVERALL VERIFICATION PASS. `git status` in `..\3DS_Translate` is clean.

After that re-check one more negative test (the encrypted-image refusal) was added, so the final
counts are **23 tests in scenario 9 and 223/223 overall** (see §6); none of the evidence above is
affected by that addition.

## 10. Final-state verification (third dispatch, 21:50–22:00)

A third dispatch found this lane already complete at 21:45 and deliberately did not rewrite the
deliverables. It re-ran the evidence on the **final** file state, after every edit:

| Check | Result |
|---|---|
| Our builder vs `3DS_Translate/dq11tool/ctr/cia.py` on `build/DQXI_patched.3ds` | byte-identical, 2,685,129,728 B, SHA-256 `517d38cd…d5424d` |
| Azahar-installed artifacts on the portable SD card | TMD byte-identical to the CIA TMD; `00000000.app` (2,683,592,704 B) and `00000001.app` (1,507,328 B) both re-hashed and equal to their TMD records; the seven save-data dirs exist |
| `python -m unittest tests.tier4_real_world.test_scenario_9_mod_export` | **Ran 23 tests in 208.631s — OK** |
| `python tests/run_all.py` | **223/223 PASS** (tier1 70, tier2 70, tier3 14, tier4 69; 217.11 s) |
| `python tools/verify_project.py` | `OVERALL: PASS -> audit/PROJECT_VERIFICATION.json` |
| `python tools/verify.py` | 16 manifest files PASS + bit-matching repacked ROM PASS |
| `--target all` (empty mod, temp dir) | exit 0 in 46.4 s; luma + 3ds + cia; exactly **one** `Repacking cartridge`, and `cia.source_rom_sha256 == 3ds.rom_sha256`, so the image is reused; empty-mod `.3ds` hash is retail `0f04b51b…a9b74` |
| `git -C ..\3DS_Translate status --short` | empty (clean) |

One wording correction was made during this pass: `docs/EXPORT.md` no longer claims the
translation project's README documents FBI installation; it says the project **ships** CIAs built
by the same code and used the same way. That is accurate (the `dq11tool/ctr/cia.py` docstring names
FBI; the README only points at the web patcher). No code changed in this pass, so no test result
above depends on the correction.

**Still not verified:** a real 3DS/2DS install (FBI + Luma on hardware). This pass verified the
Azahar installer's *artifacts* against the CIA but did not launch the emulator itself, and the
installed title was not played to the title screen.
