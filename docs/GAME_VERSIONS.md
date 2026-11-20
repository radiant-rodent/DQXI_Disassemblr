# Game versions: retail or English translation

The project can work on the retail Japanese game (`original`) or on the game with your English
translation patch applied (`en`). You can switch between them at any time. Every tool, the
exporter and DQXI Studio then read and edit the version you picked.

```powershell
python -m tools.game_version status        # which version is active, what each one changes
python -m tools.game_version use en        # work on the English game
python -m tools.game_version use original  # back to the retail game
python -m tools.game_version import en     # re-read the patch after the translation changed
python -m tools.game_version functions     # native functions / code caves the patch changes
```

In DQXI Studio, use the **Game: … ▾** menu at the right of the menu bar. It switches the version,
reloads every section, and offers **Update** when the patch file changed since the last import.

## What a version is

The retail extraction (`game_data/`, `game_assets/`, `asm/`) stays the base. A version only stores
the files its patch changes, in a content-addressed store (`versions/_store/`). A switch swaps those
files in place, so tools need no version flag:

| Tracked | Today for `en` |
|---|---|
| `game_data/romfs/` changed RomFS files | 842 (807 packs, 29 BCH map labels, 6 fonts) |
| `game_data/packs/`, `game_data/arcs/` changed / new members | ~3,250 |
| `game_assets/` converted from them: tables, layouts, textures, models, fonts, text banks | ~2,700 |
| `asm/` disassembly files, plus `asm/pad/*_tail.s` (page padding holding the code caves) | 26 |
| `mod/romfs`, `mod/code` (your mod workspace) | per version |

`original/` is never touched. It stays the retail reference for the exporter and the hashes.

The patched executable is `versions/en/code/code.decompressed.bin`. `python -m tools.build`
checks the active version: on `en` it must rebuild that file bit for bit from `asm/`. The
compressed `.code` is checked only for retail, because the patch compresses with its own tool.

### Mod workspaces belong to a version

Edits are made against one version's bytes, so `mod/romfs` and `mod/code` are stashed in
`versions/<name>/mod/` when you switch away and restored when you switch back. An English mod
and a retail mod can exist side by side. `mod/mod.json` is shared.

### Exporting

`python -m tools.export_mod` on `en` ships the translation's changed RomFS files and its
`code.bin` together with your own edits (your files win). The result is a complete English game
plus your mod. On `original` the export is unchanged.

## Changed native code

Each import compares the patched executable with the retail one and writes
`versions/en/code_changes.json`:

- **functions** the patch edits (`modified`), and those that now branch into patch code
  (`hook`), with the retail and patched disassembly;
- **code caves**: new code in the free page padding after `.text` (`0x0072403C-0x00725000`),
  named after the translation module that owns them (`EN_wordwrap_00724A00`,
  `EN_autofit_00724C00`, `EN_grammar_code_00724380`, `EN_namefix_00724DC0`, …);
- **data runs** in `.rodata`/`.data` (moved or rewritten strings, tables), with a text preview
  where they hold UTF-16 text.

Names come from the project's function catalogue. Explanations come from the translation
repository, read at import time, so they follow the patch as it changes:

- the code-cave map in `docs/AGENT_GUIDE.md`;
- `codefix.INSTRUCTIONS` (one reason per patched instruction);
- every line of the guide or a `dq11tool` module docstring that names an address in the
  function.

In DQXI Studio's **Code** section, patched functions are marked **●** in the list. The
**patched (N)** filter shows only those, and code caves are listed as functions of their own.
A patched function shows:

- **Readable / Raw Ghidra**: the decompiled C. This is the *retail* code; the panel says so.
- **Assembly**: the instructions as they are now (`mod/code/code.bin` if you edited them, else
  the active version).
- **Patch diff**: retail and patched instructions side by side, with changed lines coloured.
- **Edit assembly**: an editable listing. **Assemble & save to mod** writes it into
  `mod/code/code.bin`. **Revert to …** puts the version's bytes back.

The same works on the command line:

```powershell
python -m tools.code_edit show 0x00724A00 > wordwrap.s     # edit the file
python -m tools.code_edit apply 0x00724A00 --asm wordwrap.s
python -m tools.code_edit list                             # what mod/code changes
python -m tools.code_edit revert 0x00724A00
```

Rules the assembler enforces:

- the new code must fit in the function or cave (`--fill nop` clears a shorter tail);
- only ARMv6K/VFPv2 instructions, or a real Old 3DS crashes;
- branch targets are absolute addresses (`bl #0x724a00`).

`mod/code/edits.json` remembers which version's code the edits were made on. After a re-import
that changed the executable, `apply` refuses until you revert or redo them.

## When the translation changes

1. Rebuild the patch in the translation repository
   (`python -m dq11tool.patchfile workspace --site docs/patch`).
2. Run `python -m tools.game_version import en`, or click **Update** in the Game menu.

The import switches to `original`, reads the patch and checks every source file against your
retail extraction. It then derives everything again and switches back to `en` if that was
active. Files the new patch no longer changes simply return to retail. An import takes about two
minutes. A switch takes about 40 seconds.

Other sources work too: `--from <file>` accepts a `.dq11patch`, a LayeredFS zip or folder
(`luma/titles/<title id>/romfs` + `code.bin`/`code.ips`), or a patched `.3ds` (slow). The
default source is configured in `versions/sources.json`. New versions get a new name, for
example `import beta --from DQXI_EN_beta.dq11patch`.

## Safety

- A switch first checks every tracked file. If one was changed by hand since the last switch,
  it stops and lists them (`--force` overwrites). Put edits in `mod/` instead.
- An interrupted switch is recorded in `versions/active.json`. Run the same `use` command again
  to finish it.
- `DQXI_GAME_VERSION=<name>` overrides which version the Python tools *think* is active. It
  does not move files, so use it only for read-only checks.

## Known limits

- The readable and Ghidra C is decompiled from retail code. For patched functions, read the
  Assembly or Patch diff view. A Ghidra run on the patched executable is not part of the import.
- `game_assets/maps/` is not regenerated when a patch changes level data (the English patch
  does not). The import warns if it ever does.
- The patch writes its English text as new strings, repoints the game to them, and leaves the
  replaced Japanese strings in the BXON files (about 51,000). The text tool leaves those out of
  the text banks:
  - strings nothing points at;
  - strings whose retail pointer the patch moved away (all that still points there is the
    string block's own header).

  Retail banks are unchanged by this. On `en`, 3 of about 53,900 lines are still Japanese,
  because the game really uses them. The raw `.bxon` files still contain the dead strings.
- The asm files of a patched version are fresh disassembly. Hand comments in the changed asm
  files are not carried over (they are kept in the retail version).
