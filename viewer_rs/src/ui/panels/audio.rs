//! Audio browser: WAV streams with waveform + playback, plus BCSAR archives.

use eframe::egui;

use crate::app::ViewerApp;
use crate::theme;
use crate::utils::{human_size, waveform_peaks, WavInfo};

#[derive(Clone, Copy, PartialEq, Eq)]
enum SortKey {
    Name,
    Length,
    Size,
}

pub struct AudioPanel {
    pub query: String,
    pub kind: Option<String>,
    sort: SortKey,
    sort_desc: bool,
    list: Vec<usize>,
    selected: Option<usize>,
    dirty: bool,
    request: Option<String>,
    info: Option<WavInfo>,
    peaks: Option<(Vec<f32>, Vec<f32>)>,
    playing: Option<std::path::PathBuf>,
    position_ms: u64,
    length_ms: u64,
    archive_selected: Option<usize>,
}

impl Default for AudioPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            kind: Some("OST".into()),
            sort: SortKey::Name,
            sort_desc: false,
            list: Vec::new(),
            selected: None,
            dirty: true,
            request: None,
            info: None,
            peaks: None,
            playing: None,
            position_ms: 0,
            length_ms: 0,
            archive_selected: None,
        }
    }
}

impl AudioPanel {
    pub fn request(&mut self, query: &str) {
        self.request = Some(query.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.kind = Some("OST".into());
        self.sort = SortKey::Name;
        self.sort_desc = false;
        self.dirty = true;
    }

    fn sort_list(&mut self, audio: &crate::data::audio::AudioIndex) {
        let desc = self.sort_desc;
        self.list.sort_by(|a, b| {
            let sa = &audio.streams[*a];
            let sb = &audio.streams[*b];
            let ord = match self.sort {
                SortKey::Name => sa.name.to_lowercase().cmp(&sb.name.to_lowercase()),
                SortKey::Length => sa.duration.total_cmp(&sb.duration),
                SortKey::Size => sa.size.cmp(&sb.size),
            };
            if desc { ord.reverse() } else { ord }
        });
    }
}

#[cfg(windows)]
mod winsound {
    use std::os::windows::ffi::OsStrExt;
    use std::path::Path;

    #[link(name = "winmm")]
    unsafe extern "system" {
        fn mciSendStringW(
            command: *const u16,
            ret: *mut u16,
            ret_len: u32,
            hwnd: *mut u8,
        ) -> u32;
    }

    const ALIAS: &str = "dqxi_audio";

    fn wide(text: &str) -> Vec<u16> {
        text.encode_utf16().chain(std::iter::once(0)).collect()
    }

    fn send(command: &str) -> Result<String, String> {
        let cmd = wide(command);
        let mut buf = vec![0u16; 1024];
        let rc = unsafe {
            mciSendStringW(cmd.as_ptr(), buf.as_mut_ptr(), buf.len() as u32, std::ptr::null_mut())
        };
        if rc != 0 {
            return Err(format!("MCI error {rc}"));
        }
        let end = buf.iter().position(|c| *c == 0).unwrap_or(buf.len());
        Ok(String::from_utf16_lossy(&buf[..end]).trim().to_string())
    }

    pub fn play(path: &Path) -> bool {
        let _ = send(&format!("close {ALIAS}"));
        let quoted = path.to_string_lossy().replace('"', "");
        if send(&format!("open \"{quoted}\" type waveaudio alias {ALIAS}")).is_err() {
            return false;
        }
        let _ = send(&format!("set {ALIAS} time format milliseconds"));
        send(&format!("play {ALIAS}")).is_ok()
    }

    pub fn stop() {
        let _ = send(&format!("stop {ALIAS}"));
        let _ = send(&format!("close {ALIAS}"));
    }

    pub fn seek(ms: u64) {
        let _ = send(&format!("seek {ALIAS} to {ms}"));
    }

    pub fn pause() {
        let _ = send(&format!("pause {ALIAS}"));
    }

    pub fn resume() {
        let _ = send(&format!("play {ALIAS}"));
    }

    pub fn position() -> u64 {
        send(&format!("status {ALIAS} position"))
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(0)
    }

    pub fn length() -> u64 {
        send(&format!("status {ALIAS} length"))
            .ok()
            .and_then(|s| s.parse().ok())
            .unwrap_or(0)
    }
}

#[cfg(not(windows))]
mod winsound {
    use std::path::Path;
    pub fn play(_path: &Path) -> bool {
        false
    }
    pub fn stop() {}
    pub fn seek(_ms: u64) {}
    pub fn pause() {}
    pub fn resume() {}
    pub fn position() -> u64 {
        0
    }
    pub fn length() -> u64 {
        0
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.audio.ready) {
        ui.label(theme::dim_label("indexing audio\u{2026}"));
        return;
    }
    if let Some(query) = app.panels.audio.request.take() {
        app.panels.audio.query = query;
        app.panels.audio.dirty = true;
    }
    if app.panels.audio.dirty {
        if let Some(data) = app.data.as_deref() {
            let panel = &mut app.panels.audio;
            panel.list = data.audio.search_streams(&panel.query, panel.kind.as_deref());
            panel.sort_list(&data.audio);
            panel.dirty = false;
            if let Some(name) = panel.request.take() {
                if let Some(index) = panel
                    .list
                    .iter()
                    .copied()
                    .find(|i| data.audio.streams[*i].name == name)
                    .or_else(|| data.audio.streams.iter().position(|s| s.name == name))
                {
                    panel.selected = Some(index);
                }
            }
        }
    }

    egui::Panel::left("audio_list")
        .exact_size(320.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Audio library"));
            let counts = app
                .data
                .as_deref()
                .map(|d| {
                    vec![
                        ("OST", d.audio.kind_count("OST")),
                        ("Jingles", d.audio.kind_count("Jingle")),
                        ("Voices/SFX", d.audio.kind_count("Voice/SFX")),
                        ("All", d.audio.streams.len()),
                    ]
                })
                .unwrap_or_default();
            ui.horizontal_wrapped(|ui| {
                for (label, count) in counts {
                    let selected = match label {
                        "OST" => app.panels.audio.kind.as_deref() == Some("OST"),
                        "Jingles" => app.panels.audio.kind.as_deref() == Some("Jingle"),
                        "Voices/SFX" => app.panels.audio.kind.as_deref() == Some("Voice/SFX"),
                        _ => app.panels.audio.kind.is_none(),
                    };
                    if ui.selectable_label(selected, format!("{label} ({count})")).clicked() {
                        app.panels.audio.kind = match label {
                            "OST" => Some("OST".into()),
                            "Jingles" => Some("Jingle".into()),
                            "Voices/SFX" => Some("Voice/SFX".into()),
                            _ => None,
                        };
                        app.panels.audio.dirty = true;
                    }
                }
            });
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.audio.query)
                        .hint_text("Search streams\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.audio.dirty = true;
            }
            ui.label(theme::faint_label(format!("{} streams", app.panels.audio.list.len())));
            ui.horizontal(|ui| {
                egui::ComboBox::from_id_salt("audio_sort")
                    .selected_text(match app.panels.audio.sort {
                        SortKey::Name => "Sort: name",
                        SortKey::Length => "Sort: length",
                        SortKey::Size => "Sort: size",
                    })
                    .show_ui(ui, |ui| {
                        for (key, label) in [(SortKey::Name, "Name"), (SortKey::Length, "Length"), (SortKey::Size, "Size")] {
                            if ui.selectable_label(app.panels.audio.sort == key, label).clicked() {
                                app.panels.audio.sort = key;
                                app.panels.audio.dirty = true;
                            }
                        }
                    });
                if ui.button(if app.panels.audio.sort_desc { "Descending" } else { "Ascending" }).clicked() {
                    app.panels.audio.sort_desc = !app.panels.audio.sort_desc;
                    app.panels.audio.dirty = true;
                }
            });
            let list = app.panels.audio.list.clone();
            let selected = app.panels.audio.selected;
            let mut clicked = None;
            let height = (ui.available_height() * 0.55).max(120.0);
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("audio_scroll")
                .striped(true)
                .resizable(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .max_scroll_height(height)
                .column(Column::remainder().at_least(90.0))
                .column(Column::exact(60.0))
                .column(Column::exact(80.0))
                .header(20.0, |mut header| {
                    for (key, title) in [(SortKey::Name, "Stream"), (SortKey::Length, "Length"), (SortKey::Size, "WAV")] {
                        header.col(|ui| {
                            let arrow = if app.panels.audio.sort == key {
                                if app.panels.audio.sort_desc { " v" } else { " ^" }
                            } else {
                                ""
                            };
                            if ui.add(egui::Button::new(theme::faint_label(format!("{title}{arrow}"))).frame(false)).clicked() {
                                if app.panels.audio.sort == key {
                                    app.panels.audio.sort_desc = !app.panels.audio.sort_desc;
                                } else {
                                    app.panels.audio.sort = key;
                                    app.panels.audio.sort_desc = false;
                                }
                                app.panels.audio.dirty = true;
                            }
                        });
                    }
                })
                .body(|body| {
                    body.rows(18.0, list.len(), |mut row| {
                        let index = list[row.index()];
                        let Some(stream) = app.data.as_deref().and_then(|d| d.audio.streams.get(index))
                        else {
                            return;
                        };
                        row.set_selected(selected == Some(index));
                        row.col(|ui| {
                            ui.label(egui::RichText::new(stream.name.clone()).size(12.0));
                        });
                        row.col(|ui| {
                            ui.label(theme::dim_label(stream.duration_text()));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(human_size(stream.size)));
                        });
                        if row.response().clicked() {
                            clicked = Some(index);
                        }
                    });
                });
            if let Some(index) = clicked {
                app.panels.audio.selected = Some(index);
                if let Some(stream) = app.data.as_deref().and_then(|d| d.audio.streams.get(index)).cloned() {
                    app.panels.audio.info = Some(stream.info());
                    app.panels.audio.peaks = Some(waveform_peaks(&stream.path, 900));
                    app.panels.audio.position_ms = 0;
                    app.panels.audio.length_ms = app.panels.audio.info.as_ref().map(|i| (i.duration() * 1000.0) as u64).unwrap_or(0);
                }
            }
            ui.separator();
            ui.label(theme::heading("Sound archives (BCSAR)"));
            let archives: Vec<(String, usize, u64)> = app
                .data
                .as_deref()
                .map(|d| {
                    d.audio
                        .archives
                        .iter()
                        .map(|a| (a.name.clone(), a.sections.len(), a.total_bytes))
                        .collect()
                })
                .unwrap_or_default();
            let mut archive_clicked = None;
            egui::ScrollArea::vertical()
                .id_salt("archive_scroll")
                .auto_shrink([false, false])
                .show_rows(ui, 17.0, archives.len(), |ui, range| {
                    for row in range {
                        let (name, sections, total) = &archives[row];
                        let text = egui::RichText::new(format!(
                            "{:<24} {:>4} {:>10}",
                            crate::utils::elide(name, 24),
                            sections,
                            human_size(*total)
                        ))
                        .monospace()
                        .size(11.0);
                        if ui.selectable_label(app.panels.audio.archive_selected == Some(row), text).clicked() {
                            archive_clicked = Some(row);
                        }
                    }
                });
            if let Some(row) = archive_clicked {
                app.panels.audio.archive_selected = Some(row);
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            if let Some(row) = app.panels.audio.archive_selected {
                if let Some(archive) = app.data.as_deref().and_then(|d| d.audio.archives.get(row)) {
                    ui.label(theme::heading(archive.name.clone()));
                    ui.label(theme::dim_label(format!(
                        "{} sections  \u{b7}  {}",
                        archive.sections.len(),
                        human_size(archive.total_bytes)
                    )));
                    ui.separator();
                    for (name, size) in &archive.sections {
                        ui.label(theme::mono(format!("{name:<40} {:>10}", human_size(*size))));
                    }
                    return;
                }
            }
            let Some(index) = app.panels.audio.selected else {
                ui.label(theme::faint_label("Select a stream to see its waveform."));
                return;
            };
            let Some(stream) = app.data.as_deref().and_then(|d| d.audio.streams.get(index)) else {
                return;
            };
            let name = stream.name.clone();
            let path = stream.path.clone();
            let size = stream.size;
            let info = app.panels.audio.info.clone().unwrap_or_default();
            ui.horizontal(|ui| {
                ui.label(theme::heading(name.clone()));
                ui.label(theme::dim_label(format!(
                    "{}  \u{b7}  {} Hz  \u{b7}  {} ch  \u{b7}  {}-bit  \u{b7}  {}",
                    info.duration_text(),
                    info.rate,
                    info.channels,
                    info.width,
                    human_size(size)
                )));
            });
            ui.horizontal(|ui| {
                let playing = app.panels.audio.playing.as_deref() == Some(path.as_path());
                if ui.button(if playing { "\u{25b6} Playing\u{2026}" } else { "\u{25b6} Play" }).clicked() {
                    if winsound::play(&path) {
                        app.panels.audio.playing = Some(path.clone());
                        app.panels.audio.length_ms = winsound::length().max(app.panels.audio.length_ms);
                        app.panels.audio.position_ms = 0;
                        app.status = format!("playing {name}");
                    } else {
                        app.status = "playback failed".into();
                    }
                }
                if ui.button("\u{25a0} Stop").clicked() {
                    winsound::stop();
                    app.panels.audio.playing = None;
                    app.panels.audio.position_ms = 0;
                }
                if ui.button("\u{23ee} -10s").clicked() {
                    let pos = app.panels.audio.position_ms.saturating_sub(10_000);
                    winsound::seek(pos);
                    app.panels.audio.position_ms = pos;
                    if app.panels.audio.playing.is_some() {
                        winsound::resume();
                    }
                }
                if ui.button("\u{23ed} +10s").clicked() {
                    let max = app.panels.audio.length_ms.max(1);
                    let pos = (app.panels.audio.position_ms + 10_000).min(max);
                    winsound::seek(pos);
                    app.panels.audio.position_ms = pos;
                    if app.panels.audio.playing.is_some() {
                        winsound::resume();
                    }
                }
                if ui.button("Open externally").clicked() {
                    let _ = std::process::Command::new("cmd")
                        .args(["/C", "start", ""])
                        .arg(&path)
                        .spawn();
                }
                if ui.button("Copy path").clicked() {
                    ui.ctx().copy_text(path.to_string_lossy().into_owned());
                }
            });
            let length_ms = app.panels.audio.length_ms.max(1);
            let mut pos = app.panels.audio.position_ms.min(length_ms);
            ui.horizontal(|ui| {
                ui.label(theme::faint_label(format!("{:02}:{:02}", pos / 60_000, (pos / 1000) % 60)));
                if ui
                    .add(
                        egui::Slider::new(&mut pos, 0..=length_ms)
                            .show_value(false)
                            .text("seek"),
                    )
                    .changed()
                {
                    winsound::seek(pos);
                    app.panels.audio.position_ms = pos;
                    if app.panels.audio.playing.is_some() {
                        winsound::resume();
                    }
                }
                ui.label(theme::faint_label(format!("{:02}:{:02}", length_ms / 60_000, (length_ms / 1000) % 60)));
            });
            if app.panels.audio.playing.is_some() {
                // keep the clock and playhead moving without mouse input
                ui.ctx().request_repaint_after(std::time::Duration::from_millis(100));
                let live = winsound::position();
                if live > 0 {
                    app.panels.audio.position_ms = live;
                    if app.panels.audio.length_ms > 0 && live + 250 >= app.panels.audio.length_ms {
                        app.panels.audio.playing = None;
                    }
                }
            }
            ui.add_space(6.0);
            let (mins, maxs) = app
                .panels
                .audio
                .peaks
                .clone()
                .unwrap_or_else(|| (Vec::new(), Vec::new()));
            let remaining = egui::vec2(ui.available_width(), (ui.available_height() - 130.0).max(160.0));
            let length_ms = app.panels.audio.length_ms.max(1);
            let playhead = Some(app.panels.audio.position_ms as f32 / length_ms as f32);
            let response = ui
                .allocate_ui(remaining, |ui| crate::ui::waveform(ui, &mins, &maxs, info.duration(), playhead))
                .inner
                .on_hover_text("click or drag to jump to that point");
            if let Some(fraction) = crate::ui::waveform_seek_fraction(&response) {
                let pos = (fraction * length_ms as f32) as u64;
                winsound::seek(pos);
                app.panels.audio.position_ms = pos;
                if app.panels.audio.playing.is_some() {
                    winsound::resume();
                }
            }
            ui.separator();
            let rows: Vec<(&str, String)> = vec![
                ("source", path.to_string_lossy().into_owned()),
                ("duration", format!("{:.2} s", info.duration())),
                ("frames", info.frames.to_string()),
                ("sample rate", format!("{} Hz", info.rate)),
                (
                    "channels",
                    match info.channels {
                        1 => "mono".to_string(),
                        2 => "stereo".to_string(),
                        other => other.to_string(),
                    },
                ),
            ];
            crate::ui::kv_rows(ui, &rows);
        });
}
