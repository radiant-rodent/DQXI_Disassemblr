"""Audio index (game_audio/streams/*.wav + game_audio/archives/<proj>/)."""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path

from .. import utils


@dataclass
class Stream:
    name: str
    path: Path
    size_bytes: int
    _info: dict | None = field(default=None, repr=False)

    def info(self) -> dict:
        if self._info is None:
            info = {"channels": None, "rate": None, "frames": None, "width": None,
                    "duration": None}
            try:
                with wave.open(str(self.path), "rb") as w:
                    info["channels"] = w.getnchannels()
                    info["rate"] = w.getframerate()
                    info["frames"] = w.getnframes()
                    info["width"] = w.getsampwidth()
                    if info["rate"]:
                        info["duration"] = info["frames"] / float(info["rate"])
            except Exception as exc:
                info["error"] = str(exc)
            self._info = info
        return self._info

    @property
    def duration_text(self) -> str:
        d = self.info().get("duration")
        if not d:
            return "-"
        m, s = divmod(int(round(d)), 60)
        return f"{m}:{s:02d}"


@dataclass
class Archive:
    name: str
    path: Path
    manifest: dict = field(default_factory=dict)
    sections: list[tuple[str, int]] = field(default_factory=list)
    total_bytes: int = 0


class AudioIndex:
    def __init__(self) -> None:
        self.streams: list[Stream] = []
        self.archives: list[Archive] = []
        self.ready = False

    def ensure(self) -> "AudioIndex":
        if self.ready:
            return self
        root = utils.AUDIO_DIR
        streams: list[Stream] = []
        archives: list[Archive] = []
        if root.exists():
            streams_dir = root / "streams"
            if streams_dir.exists():
                for wav in sorted(streams_dir.rglob("*.wav"), key=lambda p: p.name.lower()):
                    try:
                        size = wav.stat().st_size
                    except OSError:
                        size = 0
                    streams.append(Stream(name=wav.stem, path=wav, size_bytes=size))
            arch_dir = root / "archives"
            if arch_dir.exists():
                for proj in sorted(arch_dir.iterdir(), key=lambda p: p.name.lower()):
                    if not proj.is_dir():
                        continue
                    manifest = {}
                    mfile = proj / "manifest.json"
                    if mfile.exists():
                        try:
                            manifest = json.loads(mfile.read_text(encoding="utf-8"))
                        except Exception:
                            manifest = {}
                    sections = []
                    total = 0
                    for f in sorted(proj.iterdir()):
                        if f.is_file() and f.name != "manifest.json":
                            try:
                                size = f.stat().st_size
                            except OSError:
                                size = 0
                            sections.append((f.name, size))
                            total += size
                    archives.append(Archive(name=proj.name, path=proj, manifest=manifest,
                                            sections=sections, total_bytes=total))
        self.streams = streams
        self.archives = archives
        self.ready = True
        return self

    def search_streams(self, query: str = "") -> list[Stream]:
        self.ensure()
        q = (query or "").strip().lower()
        if not q:
            return list(self.streams)
        return [s for s in self.streams if q in s.name.lower()]
