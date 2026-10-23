#!/usr/bin/env python3
"""Generate the OST/jingle catalog from the converted WAV tree.

This scans `game_assets/audio/romfs/sound/str` for the 155 BGM tracks and 37 ME
jingles, reads their WAV headers, and writes `game_assets/audio/AUDIO_CATALOG.md`
plus a machine-readable `ost.json`.

Usage:
    python tools/audio_catalog.py
"""
from __future__ import annotations

import json
import wave
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIO = ROOT / "game_assets" / "audio"
STR = AUDIO / "romfs" / "sound" / "str"


def info(path: Path) -> dict:
    try:
        with wave.open(str(path), "rb") as w:
            frames = w.getnframes()
            rate = w.getframerate()
            return {
                "name": path.stem.replace(".dspadpcm", ""),
                "path": str(path.relative_to(ROOT)),
                "duration": frames / rate if rate else 0.0,
                "seconds": round(frames / rate, 2) if rate else 0.0,
                "rate": rate,
                "channels": w.getnchannels(),
                "frames": frames,
                "size": path.stat().st_size,
            }
    except Exception as exc:
        return {"name": path.stem, "path": str(path), "error": str(exc)}


def fmt(seconds: float) -> str:
    m, s = divmod(seconds, 60)
    return f"{int(m)}:{s:04.1f}"


def main() -> int:
    tracks = [info(p) for p in sorted(STR.glob("*.wav"))]
    bgm = [t for t in tracks if t["name"].startswith("BGM")]
    me = [t for t in tracks if t["name"].startswith("ME")]
    # Keep a stable, discoverable catalog even if a track's header is malformed.
    (AUDIO / "ost.json").write_text(json.dumps({"bgm": bgm, "jingles": me}, indent=2), encoding="utf-8")
    lines = [
        "# Dragon Quest XI (3DS) — OST & Audio Catalog",
        "",
        "All tracks are decoded from the retail BCSTM streams to 16-bit PCM WAV.",
        "",
        f"- BGM tracks: **{len(bgm)}**",
        f"- ME jingles: **{len(me)}**",
        f"- Total WAV files in the audio tree: **{len(list(AUDIO.rglob('*.wav')))}**",
        "",
        "Use the **Audio** section of the viewer. The **OST** filter shows the soundtrack; **Jingles**",
        "shows the short ME cues; **Voices/SFX** contains cutscene/voice streams.",
        "",
        "## Music (BGM)",
        "",
        "| Track | Duration | Rate | Channels | File |",
        "|---|---:|---:|---:|---|",
    ]
    for t in bgm:
        if "error" in t:
            lines.append(f"| `{t['name']}` | error | - | - | `{t['path']}` |")
        else:
            lines.append(
                f"| `{t['name']}` | {fmt(t['duration'])} | {t['rate']} Hz | {t['channels']} | `{t['path']}` |"
            )
    lines += ["", "## Jingles (ME)", "", "| Track | Duration | Rate | Channels | File |", "|---|---:|---:|---:|---|"]
    for t in me:
        if "error" in t:
            lines.append(f"| `{t['name']}` | error | - | - | `{t['path']}` |")
        else:
            lines.append(
                f"| `{t['name']}` | {fmt(t['duration'])} | {t['rate']} Hz | {t['channels']} | `{t['path']}` |"
            )
    (AUDIO / "AUDIO_CATALOG.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {AUDIO / 'AUDIO_CATALOG.md'}: {len(bgm)} BGM, {len(me)} jingles")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
