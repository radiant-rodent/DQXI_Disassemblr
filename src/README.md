# Reconstructed Subsystems (`src/`)

These files are the **clean, hand-oriented C view** of important subsystems. They are not
compiled into the retail binary today; the bit-matching assembly in `asm/` remains canonical.
Use this tree when you want to understand a subsystem without reading Ghidra artifacts.

| File | Address / subsystem | State |
|---|---|---|
| `src/init.c` | `0x00100024` CRT BSS clear | verified sample |
| `src/memory/heaps.c` | `0x00102EF8`, `0x0055E808`, `0x0055E928`, `0x006F1C9C` | reconstructed |
| `src/hid/pad.c` | `0x0011AD3C` HID pad reader | reconstructed |
| `src/save/restoration.c` | `0x005EF33C`–`0x005EF474` save code | reconstructed |
| `src/ui/textbox.c` | `0x0053F344`, `0x00614CF0` text buffers/messages | reconstructed |
| `src/battle/damage.c` | battle damage formula | reconstructed |
| `src/battle/state.c`, `turn.c` | battle flow | reconstructed |
| `src/field/map.c`, `entity.c`, `trigger.c` | field world/collision | reconstructed |
| `src/audio/stream.c`, `voice.c`, `sound_effects.c` | audio playback | reconstructed |
| `src/graphics/display.c`, `pica.c` | GSP/PICA display setup | reconstructed |
| `src/kernel/svc.c`, `sync.c`, `memory.c` | CTR kernel services | reconstructed |

## Important caveat

A reconstructed file is a readable model, not a claim that the exact original compiler output
has been reproduced. The corresponding address and the disassembly in `asm/` are the source of
truth. When a struct offset or constant disagrees with the disassembly, fix the C and update the
documentation.

## Compile check

The files are written in portable C with `include/` headers and can be syntax-checked on the host:

```powershell
gcc -fsyntax-only -Iinclude src\memory\heaps.c
```

Full ARMv6K rebuilding is tracked in `docs/CODE.md`.
