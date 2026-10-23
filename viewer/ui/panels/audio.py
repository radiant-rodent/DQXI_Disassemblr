"""Audio browser: WAV streams with waveform display and playback."""

from __future__ import annotations

import time
import tkinter as tk
from tkinter import ttk

from ... import theme, utils
from ...render import waveform as wf
from ..widgets import KVTable, Panel, button, dim, search_entry

try:
    import winsound
except Exception:  # pragma: no cover - non-Windows fallback
    winsound = None


class AudioPanel(Panel):
    key = "audio"
    title = "Audio"
    icon = "\u266b"

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)
        self._streams: list = []
        self._current = None
        self._playing: str | None = None
        self._play_start = 0.0
        self._duration = 0.0
        self._debounce = utils.debounced(self, 200, lambda: self._refresh())

        split = ttk.PanedWindow(self, orient="horizontal")
        split.grid(row=0, column=0, sticky="nsew")

        left = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(left, weight=1)
        left.columnconfigure(0, weight=1)
        left.rowconfigure(4, weight=3)
        left.rowconfigure(7, weight=2)

        ttk.Label(left, text="Music streams", style="H2.TLabel").grid(row=0, column=0, sticky="w")
        bar = ttk.Frame(left, style="Panel.TFrame")
        bar.grid(row=1, column=0, sticky="ew", pady=6)
        self.entry = search_entry(bar, width=18, placeholder="Search streams\u2026")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<KeyRelease>", lambda e: self._debounce())

        self.tree = ttk.Treeview(left, columns=("dur", "size"), selectmode="browse")
        self.tree.heading("#0", text="Stream")
        self.tree.heading("dur", text="Length")
        self.tree.heading("size", text="WAV")
        self.tree.column("#0", width=190)
        self.tree.column("dur", width=60, stretch=False)
        self.tree.column("size", width=70, anchor="e", stretch=False)
        vbar = ttk.Scrollbar(left, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vbar.set)
        self.tree.grid(row=4, column=0, sticky="nsew")
        vbar.grid(row=4, column=1, sticky="ns")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.stream_count = dim(left, "")
        self.stream_count.grid(row=5, column=0, sticky="w", pady=(4, 8))

        ttk.Label(left, text="Sound archives (BCSAR)", style="H2.TLabel").grid(row=6, column=0, sticky="w")
        self.arch_tree = ttk.Treeview(left, columns=("files", "size"), selectmode="browse")
        self.arch_tree.heading("#0", text="Archive")
        self.arch_tree.heading("files", text="Sections")
        self.arch_tree.heading("size", text="Bytes")
        self.arch_tree.column("#0", width=190)
        self.arch_tree.column("files", width=70, anchor="e", stretch=False)
        self.arch_tree.column("size", width=80, anchor="e", stretch=False)
        va = ttk.Scrollbar(left, orient="vertical", command=self.arch_tree.yview)
        self.arch_tree.configure(yscrollcommand=va.set)
        self.arch_tree.grid(row=7, column=0, sticky="nsew")
        va.grid(row=7, column=1, sticky="ns")
        self.arch_tree.bind("<<TreeviewSelect>>", self._on_archive)

        right = ttk.Frame(split, style="Panel.TFrame", padding=(10, 10))
        split.add(right, weight=3)
        right.columnconfigure(0, weight=1)
        right.rowconfigure(3, weight=1)

        head = ttk.Frame(right, style="Panel.TFrame")
        head.grid(row=0, column=0, sticky="ew")
        self.name_label = ttk.Label(head, text="Select a stream", style="H2.TLabel")
        self.name_label.pack(anchor="w")
        self.info_label = dim(head, "")
        self.info_label.pack(anchor="w")

        controls = ttk.Frame(right, style="Panel.TFrame")
        controls.grid(row=1, column=0, sticky="ew", pady=(8, 4))
        self.play_btn = button(controls, "\u25b6  Play", self._play, style="Accent.TButton")
        self.play_btn.pack(side="left")
        button(controls, "\u25a0  Stop", self._stop).pack(side="left", padx=6)
        button(controls, "Open externally", self._open_external).pack(side="left", padx=6)
        button(controls, "Reveal file", self._reveal).pack(side="left")
        if winsound is None:
            dim(controls, "  (playback unavailable on this platform)").pack(side="left", padx=8)

        self.canvas = tk.Canvas(right, bg=theme.BG_INPUT, highlightthickness=1,
                                highlightbackground=theme.BORDER, height=260)
        self.canvas.grid(row=3, column=0, sticky="nsew")
        self.canvas.bind("<Configure>", lambda e: self._draw_wave())

        self.meta = KVTable(right, height=5, key_width=120)
        self.meta.grid(row=4, column=0, sticky="ew", pady=(8, 0))

        self._archive_label = dim(right, "")
        self._archive_label.grid(row=5, column=0, sticky="w", pady=(6, 0))

    # ------------------------------------------------------------------
    def first_show(self) -> None:
        self._refresh()

    def set_filter(self, query: str | None = None) -> None:
        if query is not None:
            self.entry.set_value(query)  # type: ignore[attr-defined]
        self._refresh()

    def summary(self) -> str:
        return f"{len(self._streams):,} streams"

    def on_hide(self) -> None:
        self._stop()

    # ------------------------------------------------------------------
    def _refresh(self) -> None:
        index = self.app.audio.ensure()
        query = self.entry.get_value().strip()  # type: ignore[attr-defined]
        self._streams = index.search_streams(query)
        self.tree.delete(*self.tree.get_children())
        for stream in self._streams:
            self.tree.insert("", "end", iid=stream.name, text=stream.name,
                             values=(stream.duration_text, utils.human_size(stream.size_bytes)))
        self.stream_count.configure(text=f"{len(self._streams):,} streams")
        self.arch_tree.delete(*self.arch_tree.get_children())
        for archive in index.archives:
            self.arch_tree.insert("", "end", iid=archive.name, text=archive.name,
                                  values=(len(archive.sections), utils.human_size(archive.total_bytes)))
        self.status(f"{len(self._streams)} streams \u00b7 {len(index.archives)} archives")

    def _on_select(self, _event=None) -> None:
        sel = self.tree.selection()
        if not sel:
            return
        name = sel[0]
        stream = next((s for s in self._streams if s.name == name), None)
        if stream is None:
            return
        self._current = stream
        self._stop()
        info = stream.info()
        self.name_label.configure(text=stream.name)
        rate = info.get("rate") or 0
        ch = info.get("channels") or 0
        width = info.get("width") or 0
        self.info_label.configure(
            text=f"{stream.duration_text}  \u00b7  {rate:,} Hz  \u00b7  {ch} ch"
                 f"  \u00b7  {width * 8}-bit  \u00b7  {utils.human_size(stream.size_bytes)}")
        self.meta.set_rows([
            ("source", str(stream.path)),
            ("duration", f"{info.get('duration', 0):.2f} s"),
            ("frames", f"{info.get('frames', 0):,}"),
            ("sample rate", f"{rate:,} Hz"),
            ("channels", {1: "mono", 2: "stereo"}.get(ch, str(ch))),
        ])
        self._duration = float(info.get("duration") or 0.0)
        self._draw_wave()
        self.status(f"{stream.name}  \u00b7  {stream.duration_text}")

    def _on_archive(self, _event=None) -> None:
        sel = self.arch_tree.selection()
        if not sel:
            return
        archive = next((a for a in self.app.audio.archives if a.name == sel[0]), None)
        if archive is None:
            return
        manifest = archive.manifest
        bits = [f"{archive.name}: {len(archive.sections)} sections, "
                f"{utils.human_size(archive.total_bytes)}"]
        if manifest:
            bits.append(f"raw archive size {utils.human_size(manifest.get('size_bytes'))}"
                        if manifest.get("size_bytes") else "")
            bits.append(f"{manifest.get('extracted_elements', '?')} elements")
        section_lines = ", ".join(f"{n} ({utils.human_size(s)})" for n, s in archive.sections[:6])
        self._archive_label.configure(text="  \u00b7  ".join(b for b in bits if b))
        self.status(f"{archive.name}  \u00b7  {section_lines}")

    # ------------------------------------------------------------------
    def _draw_wave(self) -> None:
        c = self.canvas
        c.delete("all")
        cw = max(10, c.winfo_width())
        ch = max(10, c.winfo_height())
        mid = ch / 2
        if self._current is None:
            c.create_text(cw / 2, mid, text="Select a stream to see its waveform",
                          fill=theme.TEXT_FAINT, font=theme.F_BASE)
            return
        buckets = max(100, min(2000, int(cw - 8)))
        mins, maxs, info = wf.peaks(self._current.path, buckets)
        c.create_line(4, mid, cw - 4, mid, fill=theme.BORDER)
        scale = (ch * 0.42)
        step = (cw - 8) / max(1, len(mins))
        color = theme.INFO
        for i in range(len(mins)):
            x = 4 + i * step
            y0 = mid - float(maxs[i]) * scale
            y1 = mid - float(mins[i]) * scale
            if y1 - y0 < 1:
                y0, y1 = mid - 0.5, mid + 0.5
            c.create_line(x, y0, x, y1, fill=color)
        # time ruler
        dur = info.get("duration") or 0.0
        if dur:
            for frac in (0.0, 0.25, 0.5, 0.75, 1.0):
                x = 4 + frac * (cw - 8)
                c.create_line(x, ch - 16, x, ch - 10, fill=theme.BORDER_LIGHT)
                c.create_text(x, ch - 8, anchor="n", text=_fmt_time(dur * frac),
                              fill=theme.TEXT_FAINT, font=theme.F_TINY)
        if info.get("error"):
            c.create_text(cw / 2, 18, text=f"decode issue: {info['error']}",
                          fill=theme.WARN, font=theme.F_TINY)

    def _tick(self) -> None:
        if not self._playing:
            return
        elapsed = time.time() - self._play_start
        c = self.canvas
        c.delete("cursor")
        cw = max(10, c.winfo_width())
        ch = max(10, c.winfo_height())
        if self._duration > 0:
            x = 4 + min(1.0, elapsed / self._duration) * (cw - 8)
            c.create_line(x, 0, x, ch - 14, fill=theme.ACCENT, width=2, tags="cursor")
        if elapsed > self._duration + 0.4:
            self._stop()
            return
        self.after(150, self._tick)

    # ------------------------------------------------------------------
    def _play(self) -> None:
        if self._current is None:
            return
        if winsound is None:
            self.status("Playback is not available on this platform")
            return
        self._stop()
        try:
            winsound.PlaySound(str(self._current.path),
                               winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT)
        except Exception as exc:
            self.status(f"Playback failed: {exc}")
            return
        self._playing = str(self._current.path)
        self._play_start = time.time()
        self.play_btn.configure(text="\u25b6  Playing\u2026")
        self._tick()

    def _stop(self) -> None:
        if winsound is not None:
            try:
                winsound.PlaySound(None, winsound.SND_PURGE)
            except Exception:
                pass
        self._playing = None
        self.canvas.delete("cursor")
        try:
            self.play_btn.configure(text="\u25b6  Play")
        except tk.TclError:
            pass

    def _open_external(self) -> None:
        if self._current:
            utils.open_external(self._current.path)

    def _reveal(self) -> None:
        if self._current:
            utils.reveal_in_explorer(self._current.path)


def _fmt_time(seconds: float) -> str:
    m, s = divmod(int(round(seconds)), 60)
    return f"{m}:{s:02d}"
