//! Export & Play: turn the `mod/` workspace into something a real 3DS can run,
//! boot it in this project's own Azahar, and undo individual files.
//!
//! Why this panel shells out to Python instead of reimplementing the exporter:
//! `tools/export_mod.py` is the *validated* path (RomFS IVFC hashes, ExeFS
//! superblock, NCSD partition table, Luma folder, `code.ips`). A second Rust
//! implementation would be a second, unverified exporter. This panel is the
//! driver, the pre-flight check and the human-readable log - not another
//! implementation.
//!
//! The emulator side is the same story: `python -m tools.emu boot` installs the
//! LayeredFS overlay, presses START at the end of the opening movie and reports
//! title / crash / hang with a screenshot. We run exactly that command so the
//! result here is the same result `docs/TESTING_EMULATOR.md` documents.

use std::io::{BufRead, BufReader, Read};
use std::path::{Path, PathBuf};
use std::process::{Command, Stdio};
use std::sync::mpsc::{channel, Receiver, Sender, TryRecvError};
use std::time::{Duration, Instant, SystemTime, UNIX_EPOCH};

use eframe::egui;
use serde::{Deserialize, Serialize};

use crate::app::ViewerApp;
use crate::theme;
use crate::utils::{human_size, project_root};

/// Program ID of the retail cartridge (`original/ncch0_header.bin` at 0x118).
/// Used only as a fallback; the exporter's own report is preferred.
const TITLE_ID_FALLBACK: &str = "0004000000199200";
/// Uncompressed `.text+.rodata+.data` size; the ExHeader declares it, so a
/// different size would produce a cartridge whose code region no longer fits.
const CODE_SIZE: u64 = 7_090_176;

// ---------------------------------------------------------------------------
// persisted settings
// ---------------------------------------------------------------------------
#[derive(Clone, Serialize, Deserialize)]
#[serde(default)]
pub struct Settings {
    /// `luma`, `3ds` or `cia` (fakesigned, installs on custom firmware via FBI).
    pub target: String,
    /// Relative to the project root unless absolute.
    pub out_dir: String,
    /// SD card root, e.g. `E:\`. Used by "Copy to SD".
    pub sd_card: String,
    /// Stop as soon as the title screen is live and show the screenshot.
    pub smoke: bool,
    /// A name from `third_party/emutest/saves/`, or "" for a clean boot.
    pub save: String,
    /// Real seconds to wait for the title screen (the game runs 10-20x).
    pub seconds: f64,
    /// `vulkan`, `opengl` or `software`; Vulkan is fastest but has known
    /// Azahar-side bugs in this game, so OpenGL is offered as a fallback.
    pub gpu: String,
    /// Also run the slow whole-tree asset validators (~85 s on this machine).
    pub deep_assets: bool,
    /// For the `.3ds` target: build/validate `romfs.bin` only (fast check).
    pub no_rom: bool,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            target: "luma".into(),
            out_dir: "out".into(),
            sd_card: String::new(),
            smoke: true,
            save: String::new(),
            seconds: 120.0,
            gpu: "opengl".into(), // Vulkan crashes Azahar at boot on some drivers
            deep_assets: false,
            no_rom: false,
        }
    }
}

impl Settings {
    fn path(root: &Path) -> PathBuf {
        root.join("editor_projects").join("playtest_settings.json")
    }

    fn load(root: &Path) -> Self {
        std::fs::read_to_string(Self::path(root))
            .ok()
            .and_then(|text| serde_json::from_str(&text).ok())
            .unwrap_or_default()
    }

    fn save(&self, root: &Path) {
        let path = Self::path(root);
        if let Some(parent) = path.parent() {
            let _ = std::fs::create_dir_all(parent);
        }
        if let Ok(text) = serde_json::to_string_pretty(self) {
            let _ = std::fs::write(path, text);
        }
    }

    fn out_path(&self, root: &Path) -> PathBuf {
        let p = PathBuf::from(self.out_dir.trim());
        if p.is_absolute() { p } else { root.join(p) }
    }
}

// ---------------------------------------------------------------------------
// background jobs
// ---------------------------------------------------------------------------
pub enum JobMsg {
    Line(String),
    Checks(Vec<CheckRow>),
    Screenshot(PathBuf),
    Verdict(serde_json::Value),
    Finished { ok: bool, summary: String },
}

#[derive(Clone, Copy, PartialEq, Eq)]
pub enum JobKind {
    Export,
    Play,
    Checks,
    CopyToSd,
    StopEmulator,
}

impl JobKind {
    fn label(self) -> &'static str {
        match self {
            JobKind::Export => "Export",
            JobKind::Play => "Play",
            JobKind::Checks => "Pre-flight checks",
            JobKind::CopyToSd => "Copy to SD",
            JobKind::StopEmulator => "Stop emulator",
        }
    }
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum CheckLevel {
    Ok,
    Warn,
    Error,
}

pub struct CheckRow {
    pub level: CheckLevel,
    pub label: String,
    pub detail: String,
}

#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum ChangeKind {
    Modified,
    Added,
    Unchanged,
    Code,
}

pub struct ChangeRow {
    pub rel: String,
    pub kind: ChangeKind,
    pub mod_path: PathBuf,
    pub mod_size: u64,
    pub original_size: Option<u64>,
    pub original: Option<PathBuf>,
    pub note: String,
}

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    ExportPlay,
    Changes,
    Settings,
}

impl Tab {
    fn label(self) -> &'static str {
        match self {
            Tab::ExportPlay => "Export & Play",
            Tab::Changes => "Changes",
            Tab::Settings => "Settings",
        }
    }
}

/// A button in the panel that needs `&mut ViewerApp` (filesystem + settings),
/// collected while the panel itself is mutably borrowed, then applied after the
/// draw. This keeps every egui closure's borrow short and obvious.
enum Action {
    Export,
    Play,
    Checks,
    CopyToSd,
    StopEmulator,
    StopAndRescan,
    Revert(usize),
}

pub struct PlaytestPanel {
    tab: Tab,
    settings: Settings,
    last_save_error: Option<String>,
    log: Vec<String>,
    job: Option<Receiver<JobMsg>>,
    job_kind: Option<JobKind>,
    job_started: Option<Instant>,
    running: bool,
    summary: String,
    summary_bad: bool,
    checks: Vec<CheckRow>,
    changes: Vec<ChangeRow>,
    changes_scanned: bool,
    pending_revert: Option<usize>,
    saves: Vec<String>,
    saves_scanned: bool,
    screenshot: Option<PathBuf>,
    verdict: Option<serde_json::Value>,
    screenshot_note: Option<String>,
}

impl Default for PlaytestPanel {
    fn default() -> Self {
        let root = project_root();
        Self {
            tab: Tab::ExportPlay,
            settings: Settings::load(&root),
            last_save_error: None,
            log: vec!["Ready. Export writes the chosen target; Play exports Luma and boots it.".into()],
            job: None,
            job_kind: None,
            job_started: None,
            running: false,
            summary: String::new(),
            summary_bad: false,
            checks: Vec::new(),
            changes: Vec::new(),
            changes_scanned: false,
            pending_revert: None,
            saves: Vec::new(),
            saves_scanned: false,
            screenshot: None,
            verdict: None,
            screenshot_note: None,
        }
    }
}

impl PlaytestPanel {
    /// F5: forget transient results; the user's settings stay put.
    pub fn reset(&mut self) {
        if self.running {
            return;
        }
        self.log.clear();
        self.log.push("Refreshed.".into());
        self.checks.clear();
        self.changes.clear();
        self.changes_scanned = false;
        self.pending_revert = None;
        self.saves.clear();
        self.saves_scanned = false;
        self.screenshot = None;
        self.verdict = None;
        self.screenshot_note = None;
        self.summary.clear();
        self.summary_bad = false;
    }

    pub fn summary(&self) -> String {
        if self.running {
            return match self.job_kind {
                Some(kind) => format!("{} running\u{2026}", kind.label()),
                None => "working\u{2026}".into(),
            };
        }
        if self.changes_scanned {
            let changed = self
                .changes
                .iter()
                .filter(|r| matches!(r.kind, ChangeKind::Modified | ChangeKind::Added | ChangeKind::Code))
                .count();
            return format!("{changed} changed file(s) in the mod workspace");
        }
        "export & play".into()
    }

    /// Toolbar "Export": show the panel and start the validated export.
    pub fn open_export(&mut self, root: &Path) {
        self.tab = Tab::ExportPlay;
        self.start_export(root, false);
    }

    /// Toolbar "Play": show the panel, export Luma, boot Azahar.
    pub fn open_play(&mut self, root: &Path) {
        self.tab = Tab::ExportPlay;
        self.start_export(root, true);
    }

    fn begin_job(&mut self, kind: JobKind, first: String) -> Option<Sender<JobMsg>> {
        if self.running || self.job.is_some() {
            return None;
        }
        let (tx, rx) = channel();
        self.job = Some(rx);
        self.job_kind = Some(kind);
        self.job_started = Some(Instant::now());
        self.running = true;
        self.summary.clear();
        self.summary_bad = false;
        // Never leave the previous run's title screenshot next to a new export.
        if matches!(kind, JobKind::Export | JobKind::Play) {
            self.screenshot = None;
            self.verdict = None;
            self.screenshot_note = None;
        }
        self.log.clear();
        self.log.push(first);
        Some(tx)
    }

    pub fn start_export(&mut self, root: &Path, play_after: bool) {
        let kind = if play_after { JobKind::Play } else { JobKind::Export };
        let target = if play_after {
            "luma".to_string()
        } else {
            self.settings.target.clone()
        };
        let Some(tx) = self.begin_job(kind, format!("{}{} \u{2014} validating the mod workspace\u{2026}",
            kind.label(), if play_after { " (exports Luma, then boots Azahar)" } else { "" })) else {
            return;
        };
        let root = root.to_path_buf();
        let settings = self.settings.clone();
        std::thread::spawn(move || {
            run_export_job(root, settings, target, play_after, tx);
        });
    }

    pub fn start_checks(&mut self, root: &Path) {
        let Some(tx) = self.begin_job(JobKind::Checks, "Running the pre-flight checks\u{2026}".into())
        else {
            return;
        };
        let root = root.to_path_buf();
        let settings = self.settings.clone();
        std::thread::spawn(move || {
            let _ = tx.send(JobMsg::Line("Checking the mod workspace against the retail RomFS\u{2026}".into()));
            let rows = validate_workspace(&root, &settings, &tx);
            let errors = rows.iter().filter(|r| r.level == CheckLevel::Error).count();
            let _ = tx.send(JobMsg::Checks(rows));
            let _ = tx.send(JobMsg::Finished {
                ok: errors == 0,
                summary: if errors == 0 {
                    "Checks passed. Export would not be blocked.".into()
                } else {
                    format!("{errors} error(s) would block an export.")
                },
            });
        });
    }

    pub fn start_copy_to_sd(&mut self, root: &Path) {
        let sd = self.settings.sd_card.trim().to_string();
        if sd.is_empty() {
            self.summary = "Set the SD card path in Settings first.".into();
            self.summary_bad = true;
            return;
        }
        let Some(tx) = self.begin_job(JobKind::CopyToSd, format!("Copying the Luma folder to {sd}\u{2026}"))
        else {
            return;
        };
        let root = root.to_path_buf();
        let settings = self.settings.clone();
        std::thread::spawn(move || copy_to_sd_job(root, settings, sd, tx));
    }

    pub fn start_stop_emulator(&mut self, root: &Path) {
        let Some(tx) = self.begin_job(JobKind::StopEmulator, "Asking the emulator session to stop\u{2026}".into())
        else {
            return;
        };
        let root = root.to_path_buf();
        std::thread::spawn(move || {
            let args = vec!["-u".to_string(), "-m".to_string(), "tools.emu".to_string(),
                "ctl".to_string(), "stop".to_string()];
            let _ = tx.send(JobMsg::Line(format!("python {}", args.join(" "))));
            let _ = run_streaming(&root, "python", &args, &tx);
            // `ctl stop` only knows the session it wrote itself. A boot that the
            // harness lost track of (or a crashed run) leaves a real azahar.exe
            // holding the user dir and the fixed RPC port, and the next Play then
            // fails with "emulator exited during boot". The harness solves this
            // with the same path-matched kill; mirror it here, and only for this
            // project's own emulator binary.
            let exe = root.join("third_party/emutest/azahar/azahar.exe");
            let quoted = exe.display().to_string().replace('\'', "''");
            let script = format!(
                "Get-Process azahar -ErrorAction SilentlyContinue | Where-Object {{ $_.Path -eq '{quoted}' }} | Stop-Process -Force"
            );
            let _ = tx.send(JobMsg::Line(format!("$ powershell -NoProfile -Command \"{script}\"")));
            let ps_args = vec!["-NoProfile".to_string(), "-Command".to_string(), script];
            let result = run_streaming(&root, "powershell", &ps_args, &tx);
            let ok = result.is_ok();
            let _ = tx.send(JobMsg::Finished {
                ok,
                summary: if ok {
                    "Stopped the project's Azahar (the ctl session and any leftover boot).".into()
                } else {
                    format!("could not stop Azahar: {}", result.err().unwrap_or_default())
                },
            });
        });
    }

    fn poll(&mut self, ui: &egui::Ui) {
        let mut finished: Option<(bool, String)> = None;
        if let Some(rx) = &self.job {
            loop {
                match rx.try_recv() {
                    Ok(JobMsg::Line(line)) => {
                        self.log.push(line);
                        if self.log.len() > 1500 {
                            self.log.remove(0);
                        }
                    }
                    Ok(JobMsg::Checks(rows)) => self.checks = rows,
                    Ok(JobMsg::Screenshot(path)) => self.screenshot = Some(path),
                    Ok(JobMsg::Verdict(value)) => self.verdict = Some(value),
                    Ok(JobMsg::Finished { ok, summary }) => {
                        finished = Some((ok, summary));
                        break;
                    }
                    Err(TryRecvError::Empty) => break,
                    Err(TryRecvError::Disconnected) => {
                        finished = Some((false, "the background job stopped without a result".into()));
                        break;
                    }
                }
            }
        }
        if let Some((ok, summary)) = finished {
            self.running = false;
            self.job = None;
            self.job_kind = None;
            self.summary = summary;
            self.summary_bad = !ok;
            // A finished job usually changed the mod workspace or the log files.
            self.changes_scanned = false;
        }
        if self.running {
            ui.ctx().request_repaint_after(Duration::from_millis(120));
        }
    }

    fn save_settings(&mut self, root: &Path) {
        self.settings.save(root);
        self.last_save_error = None;
    }

    fn revert(&mut self, root: &Path, index: usize) {
        let Some(row) = self.changes.get(index) else { return };
        let path = row.mod_path.clone();
        let rel = row.rel.clone();
        match std::fs::remove_file(&path) {
            Ok(()) => {
                prune_empty_dirs(root, path.parent());
                self.log.push(format!("Reverted {rel}: the override was deleted, the retail file applies again."));
                self.summary = format!("Reverted {rel}");
                self.summary_bad = false;
            }
            Err(err) => {
                self.log.push(format!("ERROR: could not revert {}: {err}", path.display()));
                self.summary = format!("Could not revert {rel}: {err}");
                self.summary_bad = true;
            }
        }
        self.pending_revert = None;
        self.changes = scan_changes(root);
        self.changes_scanned = true;
    }

    // -- drawing ---------------------------------------------------------
    fn draw_header(&mut self, ui: &mut egui::Ui, root: &Path) {
        ui.label(theme::heading("Export & Play"));
        ui.label(theme::faint_label(
            "Turn the mod workspace into a Luma folder / .3ds / .cia, then boot it in the project's \
             own Azahar. The pre-flight checks run first; errors block the export.",
        ));
        ui.add_space(3.0);
        ui.horizontal(|ui| {
            for tab in [Tab::ExportPlay, Tab::Changes, Tab::Settings] {
                let selected = self.tab == tab;
                let label = if tab == Tab::Changes && self.changes_scanned {
                    let dirty = self
                        .changes
                        .iter()
                        .filter(|r| !matches!(r.kind, ChangeKind::Unchanged))
                        .count();
                    format!("{} ({dirty})", tab.label())
                } else {
                    tab.label().to_string()
                };
                if ui.selectable_label(selected, label).clicked() {
                    self.tab = tab;
                }
            }
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui
                    .button("\u{1f4c2} Mod folder")
                    .on_hover_text(root.join("mod").display().to_string())
                    .clicked()
                {
                    let _ = std::process::Command::new("explorer").arg(root.join("mod")).spawn();
                }
                if ui
                    .button("\u{1f4c2} Output folder")
                    .on_hover_text(self.settings.out_path(root).display().to_string())
                    .clicked()
                {
                    let _ = std::process::Command::new("explorer").arg(self.settings.out_path(root)).spawn();
                }
            });
        });
    }

    fn draw_export_tab(&mut self, ui: &mut egui::Ui, root: &Path, action: &mut Option<Action>) {
        let busy = self.running;

        egui::Frame::new()
            .fill(theme::BG_PANEL)
            .inner_margin(egui::Margin::same(10))
            .show(ui, |ui| {
                egui::Grid::new("playtest_targets")
                    .num_columns(3)
                    .spacing([12.0, 6.0])
                    .show(ui, |ui| {
                        ui.label(theme::faint_label("Target"));
                        egui::ComboBox::from_id_salt("playtest_target")
                            .selected_text(target_label(&self.settings.target))
                            .width(250.0)
                            .show_ui(ui, |ui| {
                                for (id, label) in [
                                    ("luma", "Luma LayeredFS folder \u{2014} recommended"),
                                    ("3ds", "Rebuilt .3ds image \u{2014} 4 GiB"),
                                    ("cia", "Installable CIA \u{2014} fakesigned, CFW only"),
                                ] {
                                    ui.selectable_value(&mut self.settings.target, id.to_string(), label);
                                }
                            });
                        ui.label(theme::faint_label(match self.settings.target.as_str() {
                            "3ds" => "Full NCSD rebuild: slower, needs ~4 GiB free",
                            "cia" => "Built from the same .3ds; ~2.7 GB and a few minutes",
                            _ => "Changed RomFS files only; best for CFW consoles",
                        }));
                        ui.end_row();

                        ui.label(theme::faint_label("Output folder"));
                        ui.add(
                            egui::TextEdit::singleline(&mut self.settings.out_dir)
                                .desired_width(320.0)
                                .hint_text("out"),
                        );
                        ui.label(theme::faint_label(self.settings.out_path(root).display().to_string()));
                        ui.end_row();

                        ui.label(theme::faint_label("Save state"));
                        egui::ComboBox::from_id_salt("playtest_save")
                            .selected_text(if self.settings.save.is_empty() {
                                "clean boot (no save)".to_string()
                            } else {
                                self.settings.save.clone()
                            })
                            .width(250.0)
                            .show_ui(ui, |ui| {
                                if ui
                                    .selectable_value(&mut self.settings.save, String::new(), "clean boot (no save)")
                                    .clicked()
                                {
                                    self.saves_scanned = false;
                                }
                                for name in &self.saves {
                                    ui.selectable_value(&mut self.settings.save, name.clone(), name);
                                }
                            });
                        if ui
                            .button("Refresh")
                            .on_hover_text("re-scan third_party/emutest/saves")
                            .clicked()
                        {
                            self.saves_scanned = false;
                        }
                        ui.end_row();

                        ui.label(theme::faint_label("Options"));
                        ui.horizontal(|ui| {
                            ui.checkbox(&mut self.settings.smoke, "Title-screen smoke test")
                                .on_hover_text(
                                    "Boot to the title menu, take a screenshot and close the emulator. \
                                     Off = leave Azahar running at the title screen so you can play.",
                                );
                            ui.checkbox(&mut self.settings.deep_assets, "Deep asset validators (+85 s)")
                                .on_hover_text(
                                    "Also verify every exported model's texture references against the \
                                     BCH manifest. The fast per-family sample runs either way.",
                                );
                            ui.add_enabled_ui(self.settings.target == "3ds", |ui| {
                                ui.checkbox(&mut self.settings.no_rom, "romfs.bin only")
                                    .on_hover_text("Skip the 4 GiB image rebuild; still validates the RomFS.");
                            });
                        });
                        ui.end_row();

                        ui.label(theme::faint_label("Emulator"));
                        ui.horizontal(|ui| {
                            egui::ComboBox::from_id_salt("playtest_gpu")
                                .selected_text(&self.settings.gpu)
                                .width(110.0)
                                .show_ui(ui, |ui| {
                                    for gpu in ["vulkan", "opengl", "software"] {
                                        ui.selectable_value(&mut self.settings.gpu, gpu.to_string(), gpu);
                                    }
                                });
                            ui.label(theme::faint_label("timeout"));
                            ui.add(
                                egui::DragValue::new(&mut self.settings.seconds)
                                    .range(30.0..=900.0)
                                    .speed(5.0)
                                    .suffix(" s"),
                            )
                            .on_hover_text("Real seconds to wait for the title screen (the game runs 10-20x).");
                            ui.label(theme::faint_label(
                                "Vulkan is fastest; use OpenGL if a 2-way battle/shop misbehaves.",
                            ));
                        });
                        ui.end_row();
                    });

                ui.add_space(4.0);
                ui.horizontal(|ui| {
                    let export = ui.add_enabled(
                        !busy,
                        egui::Button::new(format!("Export {}", target_short(&self.settings.target))),
                    );
                    if export.on_hover_text("Run the checks, then tools/export_mod.py").clicked() {
                        *action = Some(Action::Export);
                    }
                    let play = ui.add_enabled(
                        !busy,
                        theme::filled_button("\u{25b6} Play", theme::ACCENT),
                    );
                    if play
                        .on_hover_text(
                            "Validate \u{2192} export Luma \u{2192} boot Azahar with that overlay installed",
                        )
                        .clicked()
                    {
                        *action = Some(Action::Play);
                    }
                    if ui
                        .add_enabled(!busy, egui::Button::new("Run checks"))
                        .on_hover_text("Do everything but write the export")
                        .clicked()
                    {
                        *action = Some(Action::Checks);
                    }
                    if ui
                        .add_enabled(!busy, egui::Button::new("Stop emulator"))
                        .on_hover_text("python -m tools.emu ctl stop")
                        .clicked()
                    {
                        *action = Some(Action::StopEmulator);
                    }
                    if busy {
                        let elapsed = self
                            .job_started
                            .map(|t| t.elapsed().as_secs())
                            .unwrap_or(0);
                        ui.spinner();
                        ui.label(theme::dim_label(format!(
                            "{} \u{2014} {elapsed}s",
                            self.job_kind.map(JobKind::label).unwrap_or("working")
                        )));
                    }
                });
            });

        if !self.summary.is_empty() {
            ui.label(
                egui::RichText::new(&self.summary)
                    .color(if self.summary_bad { theme::ERR } else { theme::OK })
                    .size(12.5),
            );
        }

        // Pre-flight results.
        if !self.checks.is_empty() {
            ui.add_space(4.0);
            ui.label(theme::heading("Pre-flight checks"));
            egui::Grid::new("playtest_checks")
                .num_columns(3)
                .spacing([10.0, 3.0])
                .striped(true)
                .show(ui, |ui| {
                    for row in &self.checks {
                        let (tag, color) = match row.level {
                            CheckLevel::Ok => ("OK", theme::OK),
                            CheckLevel::Warn => ("WARN", theme::WARN),
                            CheckLevel::Error => ("ERROR", theme::ERR),
                        };
                        ui.label(egui::RichText::new(tag).color(color).monospace().size(11.0));
                        ui.label(theme::dim_label(&row.label));
                        ui.label(theme::faint_label(&row.detail));
                        ui.end_row();
                    }
                });
        }

        // Verdict (the boot report JSON).
        if let Some(value) = &self.verdict {
            let outcome = value
                .get("outcome")
                .and_then(|v| v.as_str())
                .unwrap_or("(no verdict)");
            let game = value.get("game_seconds").and_then(|v| v.as_f64());
            let real = value.get("real_seconds").and_then(|v| v.as_f64());
            let basis = value.get("basis").and_then(|v| v.as_str()).unwrap_or("");
            let color = if outcome == "title" { theme::OK } else { theme::ERR };
            ui.add_space(4.0);
            ui.horizontal(|ui| {
                ui.label(theme::heading("Last boot"));
                ui.label(egui::RichText::new(outcome.to_uppercase()).color(color).strong());
                if let Some(game) = game {
                    ui.label(theme::faint_label(format!(
                        "game t={game:.1}s{}",
                        real.map(|r| format!(", {r:.1}s real")).unwrap_or_default()
                    )));
                }
                if !basis.is_empty() {
                    ui.label(theme::faint_label(basis));
                }
            });
        }

        // Screenshot from the smoke test (drawn by `show` after this tab).
        if let Some(note) = &self.screenshot_note {
            ui.label(egui::RichText::new(note).color(theme::WARN).size(11.5));
        }

        // Live log.
        ui.add_space(4.0);
        ui.horizontal(|ui| {
            ui.label(theme::heading("Log"));
            ui.label(theme::faint_label(
                "tools/export_mod.py \u{b7} python -m tools.emu boot",
            ));
            if !busy {
                ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                    if ui.button("Copy").clicked() {
                        ui.ctx().copy_text(self.log.join("\n"));
                    }
                });
            }
        });
        egui::Frame::new()
            .fill(theme::BG_INPUT)
            .inner_margin(egui::Margin::same(6))
            .show(ui, |ui| {
                egui::ScrollArea::vertical()
                    .id_salt("playtest_log")
                    .stick_to_bottom(true)
                    .auto_shrink([false, true])
                    .max_height(260.0)
                    .show(ui, |ui| {
                        if self.log.is_empty() {
                            ui.label(theme::faint_label("(nothing yet)"));
                        }
                        for line in self.log.iter().rev().take(600).rev() {
                            ui.label(egui::RichText::new(line).monospace().size(11.5).color(log_color(line)));
                        }
                    });
            });
    }

    fn draw_changes_tab(&mut self, ui: &mut egui::Ui, root: &Path, action: &mut Option<Action>) {
        if !self.changes_scanned {
            self.changes = scan_changes(root);
            self.changes_scanned = true;
            self.pending_revert = None;
        }
        let changed = self
            .changes
            .iter()
            .filter(|r| !matches!(r.kind, ChangeKind::Unchanged))
            .count();
        let total: u64 = self
            .changes
            .iter()
            .filter(|r| !matches!(r.kind, ChangeKind::Unchanged))
            .map(|r| r.mod_size)
            .sum();
        ui.horizontal(|ui| {
            ui.label(theme::heading("Changes"));
            ui.label(theme::faint_label(format!(
                "{changed} changed / {} file(s) in the workspace \u{b7} {}",
                self.changes.len(),
                human_size(total)
            )));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                if ui.button("Rescan").clicked() {
                    *action = Some(Action::StopAndRescan);
                }
                if ui
                    .button("Open mod folder")
                    .on_hover_text("mod/ (the overrides, not the retail files)")
                    .clicked()
                {
                    let _ = std::process::Command::new("explorer").arg(root.join("mod")).spawn();
                }
            });
        });
        ui.label(theme::faint_label(
            "Revert deletes the override; the retail file applies again. Existing RomFS files \
             may change size; a new path is only mounted by the full-image targets (.3ds/.cia), \
             not by Luma LayeredFS.",
        ));
        ui.separator();

        if self.changes.is_empty() {
            ui.label(theme::dim_label(
                "The mod workspace is empty. With no changes the exporter reproduces the retail \
                 cartridge byte for byte \u{2014} that is the honest baseline.",
            ));
            return;
        }

        let pending = self.pending_revert;
        let mut revert_clicked: Option<usize> = None;
        let mut cancel_clicked = false;
        let row_count = self.changes.len();
        use egui_extras::{Column, TableBuilder};
        TableBuilder::new(ui)
            .id_salt("playtest_changes_table")
            .striped(true)
            .resizable(true)
            .auto_shrink([false, false])
            .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
            .column(Column::exact(86.0))
            .column(Column::remainder().at_least(240.0).clip(true))
            .column(Column::exact(80.0))
            .column(Column::exact(80.0))
            .column(Column::exact(196.0))
            .header(22.0, |mut header| {
                for title in ["State", "File", "Size", "Retail", "Action"] {
                    header.col(|ui| {
                        ui.label(theme::faint_label(title));
                    });
                }
            })
            .body(|body| {
                body.rows(24.0, row_count, |mut row| {
                    let index = row.index();
                    let item = &self.changes[index];
                    row.col(|ui| {
                        let (tag, color) = match item.kind {
                            ChangeKind::Modified => ("MODIFIED", theme::WARN),
                            ChangeKind::Added => ("ADDED", theme::ERR),
                            ChangeKind::Unchanged => ("identical", theme::TEXT_FAINT),
                            ChangeKind::Code => ("CODE", theme::INFO),
                        };
                        ui.label(egui::RichText::new(tag).color(color).monospace().size(11.0));
                    });
                    row.col(|ui| {
                        let name = ui.label(theme::mono(&item.rel));
                        if !item.note.is_empty() {
                            name.on_hover_text(&item.note);
                        }
                    });
                    row.col(|ui| {
                        ui.label(theme::faint_label(human_size(item.mod_size)));
                    });
                    row.col(|ui| {
                        let retail = ui.label(theme::faint_label(
                            item.original_size
                                .map(human_size)
                                .unwrap_or_else(|| "\u{2014}".into()),
                        ));
                        if let Some(original) = &item.original {
                            retail.on_hover_text(original.display().to_string());
                        }
                    });
                    row.col(|ui| {
                        if matches!(item.kind, ChangeKind::Unchanged) {
                            ui.label(theme::faint_label("no override"));
                        } else if pending == Some(index) {
                            if ui
                                .button(egui::RichText::new("Delete override").color(theme::ERR))
                                .clicked()
                            {
                                revert_clicked = Some(index);
                            }
                            if ui.button("Cancel").clicked() {
                                cancel_clicked = true;
                            }
                        } else if ui
                            .button("Revert")
                            .on_hover_text("delete this file from mod/ so the retail file applies")
                            .clicked()
                        {
                            revert_clicked = Some(index);
                        }
                    });
                });
            });
        if cancel_clicked {
            self.pending_revert = None;
        }
        if let Some(index) = revert_clicked {
            if pending == Some(index) {
                *action = Some(Action::Revert(index));
            } else {
                self.pending_revert = Some(index);
            }
        }
    }

    fn draw_settings_tab(&mut self, ui: &mut egui::Ui, root: &Path, action: &mut Option<Action>) {
        ui.label(theme::heading("Real 3DS / 2DS"));
        ui.label(theme::faint_label(
            "Copy out/luma to the SD card root, then enable \u{201c}Enable game patching\u{201d} in \
             Luma3DS (hold SELECT at boot). Only the changed files are copied.",
        ));
        ui.horizontal(|ui| {
            ui.label(theme::faint_label("SD card root"));
            ui.add(
                egui::TextEdit::singleline(&mut self.settings.sd_card)
                    .desired_width(360.0)
                    .hint_text(r"E:\  (the folder that contains Nintendo 3DS / luma)"),
            )
            .on_hover_text("Saved in editor_projects/playtest_settings.json");
            if ui.button("Open").clicked() {
                if !self.settings.sd_card.trim().is_empty() {
                    let _ = std::process::Command::new("explorer")
                        .arg(self.settings.sd_card.trim())
                        .spawn();
                }
            }
            if ui
                .add_enabled(!self.running, egui::Button::new("Copy to SD"))
                .on_hover_text("copy out/luma/titles/<TitleID> to <SD>/luma/titles/<TitleID>")
                .clicked()
            {
                *action = Some(Action::CopyToSd);
            }
        });
        let sd = self.settings.sd_card.trim();
        if sd.is_empty() {
            ui.label(theme::faint_label(
                "No SD path yet. This is only needed to test on hardware; the emulator uses out/luma directly.",
            ));
        } else {
            let dest = PathBuf::from(sd).join("luma/titles").join(title_id(root));
            ui.label(theme::faint_label(format!("Will copy to {}", dest.display())));
            if !Path::new(sd).is_dir() {
                ui.label(egui::RichText::new("That path does not exist right now.").color(theme::WARN).size(11.5));
            }
        }

        ui.add_space(8.0);
        ui.label(theme::heading("Paths"));
        egui::Grid::new("playtest_paths")
            .num_columns(2)
            .spacing([12.0, 3.0])
            .striped(true)
            .show(ui, |ui| {
                let rows = [
                    ("Project", root.display().to_string()),
                    ("Mod workspace", root.join("mod").display().to_string()),
                    ("Output", self.settings.out_path(root).display().to_string()),
                    ("ROM", root.join("build").join("DQXI.3ds").display().to_string()),
                    (
                        "Azahar",
                        root.join("third_party/emutest/azahar/azahar.exe").display().to_string(),
                    ),
                    (
                        "Game saves",
                        root.join("third_party/emutest/saves").display().to_string(),
                    ),
                    (
                        "Screenshots / reports",
                        root.join("third_party/emutest/runs/playtest").display().to_string(),
                    ),
                ];
                for (key, value) in rows {
                    ui.label(theme::faint_label(key));
                    ui.label(theme::mono(value));
                    ui.end_row();
                }
            });

        ui.add_space(8.0);
        ui.label(theme::heading("How Play works here"));
        for line in [
            "1. The pre-flight check validates every changed RomFS path against game_data/romfs, \
             parses every changed PACK, checks mod/code/code.bin for ARMv6K/VFPv2-only instructions, \
             and (optionally) runs the asset validators. Errors block the export.",
            "2. Play always exports the Luma target, because that is what Azahar's LayeredFS can \
             install; the other targets are for hardware and for the record.",
            "3. \u{201c}Title-screen smoke test\u{201d} boots, presses START at the end of the opening \
             movie, screenshots the title menu and closes the emulator. With it off, Azahar is left \
             running at the title screen so you can play; \u{201c}Stop emulator\u{201d} closes it.",
            "4. Save states are portable in-game saves in third_party/emutest/saves, not Azahar UI \
             snapshots: emulator states are tied to one Azahar build and contain the old heap.",
        ] {
            ui.label(theme::faint_label(line));
        }
        if let Some(err) = &self.last_save_error {
            ui.label(egui::RichText::new(err).color(theme::ERR).size(11.5));
        }
    }
}

// ---------------------------------------------------------------------------
// entry point
// ---------------------------------------------------------------------------
pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    app.panels.playtest.poll(ui);

    let root = app.dirs.root.clone();
    // The save picker has to be filled before the combo is drawn; scanning is
    // one directory listing, so it is cheap enough to do on the UI thread.
    if app.panels.playtest.tab == Tab::ExportPlay && !app.panels.playtest.saves_scanned {
        app.panels.playtest.saves = scan_saves(&root);
        app.panels.playtest.saves_scanned = true;
    }

    let before = serde_json::to_string(&app.panels.playtest.settings).unwrap_or_default();
    let mut action: Option<Action> = None;
    let mut show_screenshot = false;

    {
        let panel = &mut app.panels.playtest;
        panel.draw_header(ui, &root);
        ui.separator();
        match panel.tab {
            Tab::ExportPlay => {
                panel.draw_export_tab(ui, &root, &mut action);
                show_screenshot = panel.screenshot.is_some();
            }
            Tab::Changes => panel.draw_changes_tab(ui, &root, &mut action),
            Tab::Settings => panel.draw_settings_tab(ui, &root, &mut action),
        }
    }

    // Settings are persisted only when something actually changed, so typing in
    // the output folder does not write a file on every frame.
    let after = serde_json::to_string(&app.panels.playtest.settings).unwrap_or_default();
    if before != after {
        app.panels.playtest.save_settings(&root);
    }

    match action {
        Some(Action::Export) => app.panels.playtest.start_export(&root, false),
        Some(Action::Play) => app.panels.playtest.start_export(&root, true),
        Some(Action::Checks) => app.panels.playtest.start_checks(&root),
        Some(Action::CopyToSd) => app.panels.playtest.start_copy_to_sd(&root),
        Some(Action::StopEmulator) => app.panels.playtest.start_stop_emulator(&root),
        Some(Action::StopAndRescan) => {
            app.panels.playtest.changes = scan_changes(&root);
            app.panels.playtest.changes_scanned = true;
            app.panels.playtest.pending_revert = None;
        }
        Some(Action::Revert(index)) => app.panels.playtest.revert(&root, index),
        None => {}
    }

    if show_screenshot {
        draw_screenshot(app, ui);
    }
}

fn draw_screenshot(app: &mut ViewerApp, ui: &mut egui::Ui) {
    let Some(path) = app.panels.playtest.screenshot.clone() else { return };
    ui.add_space(6.0);
    ui.label(theme::heading("Title-screen screenshot"));
    ui.label(theme::faint_label(path.display().to_string()));
    if !path.is_file() {
        ui.label(
            egui::RichText::new("The run did not produce a screenshot (see the log above).")
                .color(theme::WARN)
                .size(11.5),
        );
        return;
    }
    let ctx = ui.ctx().clone();
    let texture = app.preview.get(&ctx, &app.pool, &path);
    match texture {
        Some(handle) => {
            let native = handle.size_vec2();
            let scale = (640.0 / native.x.max(1.0)).min(1.0);
            ui.add(crate::ui::image_widget(&handle, native * scale));
            ui.label(theme::faint_label(
                "Captured by python -m tools.emu boot. The JSON report is next to the PNG.",
            ));
        }
        None => {
            ui.label(theme::faint_label("loading the screenshot\u{2026}"));
            ctx.request_repaint_after(Duration::from_millis(150));
        }
    }
}

// ---------------------------------------------------------------------------
// jobs
// ---------------------------------------------------------------------------
fn run_export_job(root: PathBuf, settings: Settings, target: String, play_after: bool, tx: Sender<JobMsg>) {
    // 1. Pre-flight validation. Errors stop everything before a single byte is
    //    written; warnings (e.g. a missing mod.json) do not.
    let rows = validate_workspace(&root, &settings, &tx);
    let errors = rows.iter().filter(|r| r.level == CheckLevel::Error).count();
    let _ = tx.send(JobMsg::Checks(rows));
    if errors > 0 {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!(
                "Export blocked: {errors} pre-flight error(s). Nothing was written; fix them and try again."
            ),
        });
        return;
    }

    // 2. Export. `python -u` keeps the log live while the child runs.
    let out = settings.out_path(&root);
    let mut args = vec![
        "-u".to_string(),
        "tools/export_mod.py".to_string(),
        "--target".to_string(),
        target.clone(),
        "--mod".to_string(),
        root.join("mod").display().to_string(),
        "--out".to_string(),
        out.display().to_string(),
    ];
    if settings.no_rom && matches!(target.as_str(), "3ds" | "all") {
        args.push("--no-rom".to_string());
    }
    let _ = tx.send(JobMsg::Line(format!("$ python {}", args.join(" "))));
    let export_code = match run_streaming(&root, "python", &args, &tx) {
        Ok(code) => code,
        Err(err) => {
            let _ = tx.send(JobMsg::Finished { ok: false, summary: err });
            return;
        }
    };
    let report = read_json(&out.join("EXPORT_REPORT.json"));
    let report_ok = report
        .as_ref()
        .and_then(|v| v.get("ok"))
        .and_then(|v| v.as_bool())
        .unwrap_or(false);

    if !play_after {
        let ok = export_code == 0 && report_ok;
        let summary = if ok {
            format!("Export OK \u{2014} {}. Report: {}", target, out.join("EXPORT_REPORT.json").display())
        } else {
            format!(
                "Export failed (exit {export_code}). The log above and {} say why; nothing else was changed.",
                out.join("EXPORT_REPORT.json").display()
            )
        };
        let _ = tx.send(JobMsg::Finished { ok, summary });
        return;
    }

    if export_code != 0 || !report_ok {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!(
                "Play stopped: the Luma export failed (exit {export_code}), so booting would test the \
                 wrong files."
            ),
        });
        return;
    }

    // 3. Boot the project's Azahar with the overlay that was just written.
    let rom = root.join("build").join("DQXI.3ds");
    if !rom.is_file() {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!("Play stopped: {} is missing. Run the project build first.", rom.display()),
        });
        return;
    }
    if !settings.save.is_empty()
        && !root.join("third_party/emutest/saves").join(&settings.save).is_dir()
    {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!(
                "Play stopped: save state '{}' is not in third_party/emutest/saves. Pick another one.",
                settings.save
            ),
        });
        return;
    }
    let stamp = SystemTime::now()
        .duration_since(UNIX_EPOCH)
        .map(|d| d.as_secs())
        .unwrap_or(0);
    let shot = root
        .join("third_party/emutest/runs/playtest")
        .join(format!("play-{stamp}.png"));
    if let Some(parent) = shot.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let mut args = vec![
        "-u".to_string(),
        "-m".to_string(),
        "tools.emu".to_string(),
        "boot".to_string(),
        rom.display().to_string(),
        "--mod".to_string(),
        out.join("luma").display().to_string(),
        "--seconds".to_string(),
        format!("{}", settings.seconds.max(30.0)),
        "--shot".to_string(),
        shot.display().to_string(),
        "--gpu".to_string(),
        settings.gpu.clone(),
    ];
    if !settings.save.is_empty() {
        args.push("--save".to_string());
        args.push(settings.save.clone());
    }
    if !settings.smoke {
        args.push("--keep-open".to_string());
    }
    let _ = tx.send(JobMsg::Line(format!("$ python {}", args.join(" "))));
    let boot_code = match run_streaming(&root, "python", &args, &tx) {
        Ok(code) => code,
        Err(err) => {
            let _ = tx.send(JobMsg::Finished { ok: false, summary: err });
            return;
        }
    };

    if shot.is_file() {
        let _ = tx.send(JobMsg::Screenshot(shot.clone()));
        if let Some(report) = read_json(&shot.with_extension("json")) {
            let _ = tx.send(JobMsg::Verdict(report));
        }
    } else {
        let _ = tx.send(JobMsg::Line(format!(
            "no screenshot at {} (the emulator stopped before it could take one)",
            shot.display()
        )));
    }

    let (ok, what) = match boot_code {
        0 => (true, "title screen reached"),
        1 => (false, "CRASH \u{2014} see the screenshot and the log"),
        2 => (false, "HANG \u{2014} no title within the time limit"),
        3 => (false, "ERROR \u{2014} emulator/ROM/save missing"),
        _ => (false, "emulator finished with an unexpected status"),
    };
    let summary = if ok && settings.smoke {
        "Play OK: title screen reached and the emulator was closed. Screenshot below.".to_string()
    } else if ok {
        "Play OK: Azahar is running at the title screen. Use Stop emulator (or close its window) when done.".to_string()
    } else {
        format!("{what} (exit {boot_code}).")
    };
    let _ = tx.send(JobMsg::Finished { ok, summary });
}

fn copy_to_sd_job(root: PathBuf, settings: Settings, sd: String, tx: Sender<JobMsg>) {
    let sd_root = PathBuf::from(sd.trim());
    if !sd_root.is_dir() {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!("SD path {} does not exist.", sd_root.display()),
        });
        return;
    }
    if same_path(&sd_root, &root) {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: "The SD path is the project folder; refusing to copy into the project.".into(),
        });
        return;
    }
    let title = title_id(&root);
    let out = settings.out_path(&root);
    let src = out.join("luma").join("titles").join(&title);
    if !src.is_dir() {
        let _ = tx.send(JobMsg::Finished {
            ok: false,
            summary: format!("{} does not exist. Run Export (Luma) first.", src.display()),
        });
        return;
    }
    let dest = sd_root.join("luma").join("titles").join(&title);
    let _ = tx.send(JobMsg::Line(format!("source:      {}", src.display())));
    let _ = tx.send(JobMsg::Line(format!("destination: {}", dest.display())));
    if dest.exists() {
        let _ = tx.send(JobMsg::Line(
            "removing the previous copy so no stale override survives".into(),
        ));
        if let Err(err) = std::fs::remove_dir_all(&dest) {
            let _ = tx.send(JobMsg::Finished {
                ok: false,
                summary: format!("could not clear {}: {err}", dest.display()),
            });
            return;
        }
    }
    let mut files = Vec::new();
    collect_files(&src, &mut files);
    let mut copied = 0usize;
    let mut bytes = 0u64;
    for path in &files {
        let Some(rel) = path.strip_prefix(&src).ok() else { continue };
        let target = dest.join(rel);
        if let Some(parent) = target.parent() {
            if let Err(err) = std::fs::create_dir_all(parent) {
                let _ = tx.send(JobMsg::Finished {
                    ok: false,
                    summary: format!("could not create {}: {err}", parent.display()),
                });
                return;
            }
        }
        match std::fs::copy(path, &target) {
            Ok(size) => {
                copied += 1;
                bytes += size;
                if copied <= 20 || copied % 50 == 0 {
                    let _ = tx.send(JobMsg::Line(format!(
                        "  {} ({})",
                        relative_slash(&src, path),
                        human_size(size)
                    )));
                }
            }
            Err(err) => {
                let _ = tx.send(JobMsg::Finished {
                    ok: false,
                    summary: format!("copy failed at {}: {err}", path.display()),
                });
                return;
            }
        }
    }
    let _ = tx.send(JobMsg::Finished {
        ok: true,
        summary: format!(
            "Copied {copied} file(s), {} to {}. Enable \u{201c}Enable game patching\u{201d} in Luma3DS.",
            human_size(bytes),
            dest.display()
        ),
    });
}

// ---------------------------------------------------------------------------
// validation
// ---------------------------------------------------------------------------
fn validate_workspace(root: &Path, settings: &Settings, tx: &Sender<JobMsg>) -> Vec<CheckRow> {
    let mut rows: Vec<CheckRow> = Vec::new();
    let mut add = |level: CheckLevel, label: &str, detail: String| {
        let _ = tx.send(JobMsg::Line(format!(
            "  [{}] {label}: {detail}",
            match level {
                CheckLevel::Ok => "ok",
                CheckLevel::Warn => "warn",
                CheckLevel::Error => "error",
            }
        )));
        rows.push(CheckRow {
            level,
            label: label.to_string(),
            detail,
        });
    };

    let mod_dir = root.join("mod");
    if !mod_dir.is_dir() {
        add(
            CheckLevel::Warn,
            "mod workspace",
            "mod/ is missing; an export reproduces the retail cartridge".into(),
        );
        return rows;
    }

    // --- mod.json (metadata; its absence is not an error) -----------------
    let meta_path = mod_dir.join("mod.json");
    if meta_path.is_file() {
        match std::fs::read_to_string(&meta_path)
            .map_err(|e| e.to_string())
            .and_then(|text| serde_json::from_str::<serde_json::Value>(&text).map_err(|e| e.to_string()))
        {
            Ok(value) => {
                let name = value.get("name").and_then(|v| v.as_str()).unwrap_or("");
                let version = value.get("version").and_then(|v| v.as_str()).unwrap_or("");
                add(
                    CheckLevel::Ok,
                    "mod.json",
                    if name.is_empty() {
                        "valid JSON (no name yet)".into()
                    } else {
                        format!("{name} {version}")
                    },
                );
            }
            Err(err) => add(CheckLevel::Error, "mod.json", format!("invalid JSON: {err}")),
        }
    } else {
        add(
            CheckLevel::Warn,
            "mod.json",
            "missing; the export works but the report has no mod name/author".into(),
        );
    }

    // --- RomFS overrides ---------------------------------------------------
    let romfs = mod_dir.join("romfs");
    let retail = root.join("game_data").join("romfs");
    let mut files = Vec::new();
    collect_files(&romfs, &mut files);
    files.sort();
    if files.is_empty() {
        add(
            CheckLevel::Warn,
            "romfs overrides",
            "none; the export is the retail game".into(),
        );
    }
    let mut pack_files: Vec<PathBuf> = Vec::new();
    let mut changed = 0usize;
    for path in &files {
        let rel = relative_slash(&romfs, path);
        let original = retail.join(&rel);
        let size = path.metadata().map(|m| m.len()).unwrap_or(0);
        if !original.is_file() {
            add(
                CheckLevel::Warn,
                &format!("romfs/{rel}"),
                format!(
                    "{} is a new RomFS path. The 3ds/cia targets rebuild the directory tables \
                     and add it; Luma LayeredFS cannot mount new paths, so a Luma export skips it.",
                    human_size(size)
                ),
            );
            continue;
        }
        let original_size = original.metadata().map(|m| m.len()).unwrap_or(0);
        if files_equal(path, &original) {
            add(
                CheckLevel::Warn,
                &format!("romfs/{rel}"),
                format!("identical to retail ({}); the override changes nothing", human_size(size)),
            );
            continue;
        }
        changed += 1;
        add(
            CheckLevel::Ok,
            &format!("romfs/{rel}"),
            format!("{} (retail {})", human_size(size), human_size(original_size)),
        );
        let magic = read_magic(path);
        let is_pack = magic
            .as_deref()
            .map(|m| m == b"PACK" || m == b"PACA")
            .unwrap_or(false);
        if is_pack {
            pack_files.push(path.clone());
        } else {
            add(
                CheckLevel::Warn,
                &format!("romfs/{rel}"),
                "not a PACK/PACA file; the RomFS usually holds packs, so double-check the path".into(),
            );
        }
    }
    if !files.is_empty() {
        add(
            CheckLevel::Ok,
            "romfs changes",
            format!("{changed} of {} file(s) differ from retail", files.len()),
        );
    }

    // --- PACK structure of every changed pack ------------------------------
    if !pack_files.is_empty() {
        let script = r#"
import sys
from pathlib import Path
sys.path.insert(0, '.')
from tools.pack import Pack
bad = 0
for name in sys.argv[1:]:
    try:
        data = Path(name).read_bytes()
        p = Pack.parse(data)
        if not p.entries:
            print(f'{name}: PACK has no members'); bad = 1
    except Exception as exc:
        print(f'{name}: {exc}'); bad = 1
print(f'{len(sys.argv) - 1} PACK file(s) parsed')
raise SystemExit(1 if bad else 0)
"#;
        let mut args = vec!["-u".to_string(), "-c".to_string(), script.to_string()];
        args.extend(pack_files.iter().map(|p| p.display().to_string()));
        let _ = tx.send(JobMsg::Line("  parsing the changed PACK archives\u{2026}".into()));
        match run_capture(root, "python", &args) {
            Ok(output) if output.status.success() => add(
                CheckLevel::Ok,
                "PACK structure",
                last_line(&output_text(&output)),
            ),
            Ok(output) => add(
                CheckLevel::Error,
                "PACK structure",
                last_line(&output_text(&output)),
            ),
            Err(err) => add(CheckLevel::Error, "PACK structure", err),
        }
    }

    // --- native code -------------------------------------------------------
    let code = mod_dir.join("code").join("code.bin");
    if code.is_file() {
        let size = code.metadata().map(|m| m.len()).unwrap_or(0);
        if size != CODE_SIZE {
            add(
                CheckLevel::Error,
                "code/code.bin",
                format!(
                    "{size} bytes, expected {CODE_SIZE}. The ExHeader code-set size is not rewritten, \
                     so a different size cannot be shipped."
                ),
            );
        } else {
            add(CheckLevel::Ok, "code/code.bin", format!("{} bytes", human_size(size)));
            let _ = tx.send(JobMsg::Line(
                "  checking changed instructions for ARMv6K/VFPv2 compatibility\u{2026}".into(),
            ));
            let args = vec!["-u".to_string(), "tools/check_armv6k.py".to_string()];
            match run_capture(root, "python", &args) {
                Ok(output) if output.status.success() => add(
                    CheckLevel::Ok,
                    "ARMv6K/VFPv2",
                    last_line(&output_text(&output)),
                ),
                Ok(output) => add(
                    CheckLevel::Error,
                    "ARMv6K/VFPv2",
                    format!(
                        "{} \u{2014} a real 3DS/2DS would fault (Azahar would not)",
                        last_line(&output_text(&output))
                    ),
                ),
                Err(err) => add(CheckLevel::Error, "ARMv6K/VFPv2", err),
            }
        }
    }

    // --- optional whole-tree asset validators ------------------------------
    if settings.deep_assets {
        for (label, script, extra) in [
            (
                "Asset validators",
                "tools/verify_assets.py",
                vec!["--sample", "20"],
            ),
            ("Model textures", "tools/verify_model_textures.py", vec![]),
        ] {
            let _ = tx.send(JobMsg::Line(format!("  running {script}\u{2026}")));
            let mut args = vec!["-u".to_string(), script.to_string()];
            args.extend(extra.iter().map(|s| s.to_string()));
            match run_capture(root, "python", &args) {
                Ok(output) if output.status.success() => {
                    add(CheckLevel::Ok, label, last_line(&output_text(&output)))
                }
                Ok(output) => add(CheckLevel::Error, label, last_line(&output_text(&output))),
                Err(err) => add(CheckLevel::Error, label, err),
            }
        }
    }

    rows
}

// ---------------------------------------------------------------------------
// changes vs. the retail files
// ---------------------------------------------------------------------------
pub fn scan_changes(root: &Path) -> Vec<ChangeRow> {
    let mod_dir = root.join("mod");
    let romfs = mod_dir.join("romfs");
    let retail = root.join("game_data").join("romfs");
    let mut files = Vec::new();
    collect_files(&romfs, &mut files);
    files.sort();

    let mut rows = Vec::new();
    for path in files {
        let rel = relative_slash(&romfs, &path);
        let original = retail.join(&rel);
        let mod_size = path.metadata().map(|m| m.len()).unwrap_or(0);
        let (kind, original_size, note) = if !original.is_file() {
            (
                ChangeKind::Added,
                None,
                "new RomFS path; added by the 3ds/cia targets, not mounted by Luma LayeredFS"
                    .to_string(),
            )
        } else {
            let original_size = original.metadata().map(|m| m.len()).unwrap_or(0);
            if files_equal(&path, &original) {
                (ChangeKind::Unchanged, Some(original_size), "same bytes as retail".to_string())
            } else {
                (
                    ChangeKind::Modified,
                    Some(original_size),
                    "replaces the retail file in the LayeredFS folder".to_string(),
                )
            }
        };
        rows.push(ChangeRow {
            rel: format!("romfs/{rel}"),
            kind,
            mod_path: path,
            mod_size,
            original_size,
            original: original.is_file().then_some(original),
            note,
        });
    }

    let code = mod_dir.join("code").join("code.bin");
    if code.is_file() {
        let original = root.join("original/exefs/code.decompressed.bin");
        let mod_size = code.metadata().map(|m| m.len()).unwrap_or(0);
        let original_size = original.metadata().ok().map(|m| m.len());
        let kind = if original.is_file() && files_equal(&code, &original) {
            ChangeKind::Unchanged
        } else {
            ChangeKind::Code
        };
        rows.push(ChangeRow {
            rel: "code/code.bin".into(),
            kind,
            mod_path: code,
            mod_size,
            original_size,
            original: original.is_file().then_some(original),
            note: "native executable; Luma gets a small code.ips diff of this file".into(),
        });
    }

    rows
}

// ---------------------------------------------------------------------------
// small helpers
// ---------------------------------------------------------------------------
fn title_id(root: &Path) -> String {
    read_json(&root.join("out/EXPORT_REPORT.json"))
        .and_then(|v| v.get("title_id").and_then(|x| x.as_str()).map(str::to_string))
        .filter(|s| !s.is_empty())
        .unwrap_or_else(|| TITLE_ID_FALLBACK.to_string())
}

fn target_label(id: &str) -> &'static str {
    match id {
        "3ds" => "Rebuilt .3ds image",
        "cia" => "Installable CIA (CFW)",
        _ => "Luma LayeredFS folder",
    }
}

fn target_short(id: &str) -> &'static str {
    match id {
        "3ds" => ".3ds",
        "cia" => "CIA",
        _ => "Luma",
    }
}
fn scan_saves(root: &Path) -> Vec<String> {
    let dir = root.join("third_party/emutest/saves");
    let Ok(entries) = std::fs::read_dir(dir) else { return Vec::new() };
    let mut names: Vec<String> = entries
        .flatten()
        .filter(|e| e.file_type().map(|t| t.is_dir()).unwrap_or(false))
        .filter_map(|e| e.file_name().into_string().ok())
        .collect();
    names.sort();
    names
}

fn read_json(path: &Path) -> Option<serde_json::Value> {
    std::fs::read_to_string(path)
        .ok()
        .and_then(|text| serde_json::from_str(&text).ok())
}

fn collect_files(dir: &Path, out: &mut Vec<PathBuf>) {
    let Ok(entries) = std::fs::read_dir(dir) else { return };
    for entry in entries.flatten() {
        let path = entry.path();
        match entry.file_type() {
            Ok(kind) if kind.is_dir() => collect_files(&path, out),
            Ok(kind) if kind.is_file() => out.push(path),
            _ => {}
        }
    }
}

fn relative_slash(base: &Path, path: &Path) -> String {
    path.strip_prefix(base)
        .map(|p| p.to_string_lossy().replace('\\', "/"))
        .unwrap_or_else(|_| path.to_string_lossy().into_owned())
}

/// Streaming comparison: a modded movie or pack can be tens of MB, and the
/// Changes tab must not allocate two copies of it.
fn files_equal(a: &Path, b: &Path) -> bool {
    let (Ok(mut fa), Ok(mut fb)) = (std::fs::File::open(a), std::fs::File::open(b)) else {
        return false;
    };
    let (Ok(ma), Ok(mb)) = (fa.metadata(), fb.metadata()) else { return false };
    if ma.len() != mb.len() {
        return false;
    }
    let mut ba = vec![0u8; 1024 * 1024];
    let mut bb = vec![0u8; 1024 * 1024];
    loop {
        let na = match fa.read(&mut ba) {
            Ok(n) => n,
            Err(_) => return false,
        };
        if na == 0 {
            return true;
        }
        let mut read_b = 0usize;
        while read_b < na {
            match fb.read(&mut bb[read_b..na]) {
                Ok(0) => return false,
                Ok(n) => read_b += n,
                Err(_) => return false,
            }
        }
        if ba[..na] != bb[..na] {
            return false;
        }
    }
}

fn read_magic(path: &Path) -> Option<Vec<u8>> {
    let mut file = std::fs::File::open(path).ok()?;
    let mut magic = [0u8; 4];
    file.read_exact(&mut magic).ok()?;
    Some(magic.to_vec())
}

fn prune_empty_dirs(root: &Path, start: Option<&Path>) {
    let stop = root.join("mod").join("romfs");
    let mut current = start.map(|p| p.to_path_buf());
    while let Some(dir) = current {
        if dir == stop || !dir.starts_with(&stop) {
            break;
        }
        if std::fs::remove_dir(&dir).is_err() {
            break;
        }
        current = dir.parent().map(|p| p.to_path_buf());
    }
}

fn same_path(a: &Path, b: &Path) -> bool {
    match (a.canonicalize(), b.canonicalize()) {
        (Ok(a), Ok(b)) => a == b,
        _ => a == b,
    }
}

fn output_text(output: &std::process::Output) -> String {
    let mut text = String::from_utf8_lossy(&output.stdout).into_owned();
    let err = String::from_utf8_lossy(&output.stderr);
    if !err.trim().is_empty() {
        if !text.ends_with('\n') && !text.is_empty() {
            text.push('\n');
        }
        text.push_str(err.trim());
    }
    text
}

fn last_line(text: &str) -> String {
    text.lines()
        .rev()
        .map(str::trim)
        .find(|line| !line.is_empty())
        .unwrap_or("(no output)")
        .to_string()
}

fn log_color(line: &str) -> egui::Color32 {
    let upper = line.to_ascii_uppercase();
    if upper.contains("ERROR") || upper.contains("CRASH:") || upper.contains("FAILED") {
        theme::ERR
    } else if upper.contains("HANG:") || upper.contains("BLOCKED") || upper.contains("WARN") {
        theme::WARN
    } else if upper.contains("EXPORT OK") || upper.contains("TITLE-SCREEN REACHED") {
        theme::OK
    } else {
        theme::MONO
    }
}

fn run_capture(root: &Path, program: &str, args: &[String]) -> Result<std::process::Output, String> {
    Command::new(program)
        .args(args)
        .current_dir(root)
        .output()
        .map_err(|e| format!("could not run {program}: {e}"))
}

/// Run a child and forward both pipes line by line, so a four-minute export or
/// boot shows progress instead of freezing the window.
fn run_streaming(
    root: &Path,
    program: &str,
    args: &[String],
    tx: &Sender<JobMsg>,
) -> Result<i32, String> {
    let mut child = Command::new(program)
        .args(args)
        .current_dir(root)
        .stdout(Stdio::piped())
        .stderr(Stdio::piped())
        .spawn()
        .map_err(|e| format!("could not start {program}: {e}"))?;
    let stdout = child.stdout.take();
    let stderr = child.stderr.take();
    let out_tx = tx.clone();
    let err_tx = tx.clone();
    let status = std::thread::scope(|scope| {
        let h_out = stdout.map(|pipe| scope.spawn(move || pump(pipe, out_tx)));
        let h_err = stderr.map(|pipe| scope.spawn(move || pump(pipe, err_tx)));
        let status = child.wait();
        if let Some(handle) = h_out {
            let _ = handle.join();
        }
        if let Some(handle) = h_err {
            let _ = handle.join();
        }
        status
    })
    .map_err(|e| format!("waiting for {program} failed: {e}"))?;
    Ok(status.code().unwrap_or(-1))
}

fn pump<R: Read + Send>(pipe: R, tx: Sender<JobMsg>) {
    for line in BufReader::new(pipe).lines() {
        match line {
            Ok(line) => {
                if tx.send(JobMsg::Line(line)).is_err() {
                    break;
                }
            }
            Err(_) => break,
        }
    }
}

// ---------------------------------------------------------------------------
// tests (pure filesystem helpers; no UI, emulator or Python needed)
// ---------------------------------------------------------------------------
#[cfg(test)]
mod tests {
    use super::*;

    fn scratch(name: &str) -> PathBuf {
        let path = std::env::temp_dir().join(format!(
            "dqxi_playtest_{name}_{}_{}",
            std::process::id(),
            SystemTime::now()
                .duration_since(UNIX_EPOCH)
                .map(|d| d.as_nanos())
                .unwrap_or(0)
        ));
        let _ = std::fs::remove_dir_all(&path);
        std::fs::create_dir_all(&path).expect("create scratch");
        path
    }

    #[test]
    fn files_equal_streams_and_detects_a_difference() {
        let dir = scratch("equal");
        let a = dir.join("a.bin");
        let b = dir.join("b.bin");
        let big: Vec<u8> = (0..(3 * 1024 * 1024 + 7)).map(|i| (i % 251) as u8).collect();
        std::fs::write(&a, &big).unwrap();
        std::fs::write(&b, &big).unwrap();
        assert!(files_equal(&a, &b));
        let mut changed = big.clone();
        changed[2 * 1024 * 1024 + 3] ^= 0xFF;
        std::fs::write(&b, &changed).unwrap();
        assert!(!files_equal(&a, &b));
        std::fs::write(&b, b"short").unwrap();
        assert!(!files_equal(&a, &b));
        let _ = std::fs::remove_dir_all(&dir);
    }

    #[test]
    fn scan_changes_classifies_modified_identical_and_added() {
        let root = scratch("changes");
        let retail = root.join("game_data/romfs");
        let romfs = root.join("mod/romfs");
        std::fs::create_dir_all(retail.join("level3d")).unwrap();
        std::fs::create_dir_all(romfs.join("level3d")).unwrap();
        std::fs::write(retail.join("level3d/b001.pack"), b"retail-pack").unwrap();
        std::fs::write(romfs.join("level3d/b001.pack"), b"modded-pack").unwrap();
        std::fs::write(retail.join("same.pack"), b"same").unwrap();
        std::fs::write(romfs.join("same.pack"), b"same").unwrap();
        std::fs::write(romfs.join("level3d/new.pack"), b"new").unwrap();

        let rows = scan_changes(&root);
        let find = |rel: &str| rows.iter().find(|r| r.rel == rel).expect(rel);
        assert_eq!(find("romfs/level3d/b001.pack").kind, ChangeKind::Modified);
        assert_eq!(find("romfs/same.pack").kind, ChangeKind::Unchanged);
        assert_eq!(find("romfs/level3d/new.pack").kind, ChangeKind::Added);
        assert_eq!(find("romfs/level3d/b001.pack").original_size, Some(11));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn scan_changes_marks_native_code() {
        let root = scratch("code");
        std::fs::create_dir_all(root.join("mod/code")).unwrap();
        std::fs::create_dir_all(root.join("original/exefs")).unwrap();
        std::fs::write(root.join("original/exefs/code.decompressed.bin"), b"retail").unwrap();
        std::fs::write(root.join("mod/code/code.bin"), b"patched").unwrap();
        let rows = scan_changes(&root);
        let row = rows.iter().find(|r| r.rel == "code/code.bin").expect("code row");
        assert_eq!(row.kind, ChangeKind::Code);
        assert_eq!(row.mod_size, 7);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn title_id_comes_from_the_export_report() {
        let root = scratch("title");
        std::fs::create_dir_all(root.join("out")).unwrap();
        assert_eq!(title_id(&root), TITLE_ID_FALLBACK);
        std::fs::write(
            root.join("out/EXPORT_REPORT.json"),
            r#"{"title_id":"0004000000123400","ok":true}"#,
        )
        .unwrap();
        assert_eq!(title_id(&root), "0004000000123400");
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn settings_round_trip_and_defaults() {
        let root = scratch("settings");
        let mut settings = Settings::load(&root);
        assert_eq!(settings.target, "luma");
        assert!(settings.smoke);
        settings.target = "3ds".into();
        settings.sd_card = r"E:\".into();
        settings.deep_assets = true;
        settings.save(&root);
        let again = Settings::load(&root);
        assert_eq!(again.target, "3ds");
        assert_eq!(again.sd_card, r"E:\");
        assert!(again.deep_assets);
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn relative_paths_use_forward_slashes_and_are_stable() {
        let base = Path::new(r"C:\project\mod\romfs");
        let file = Path::new(r"C:\project\mod\romfs\level3d\b001.pack");
        assert_eq!(relative_slash(base, file), "level3d/b001.pack");
    }

    #[test]
    fn last_line_skips_trailing_blank_lines() {
        assert_eq!(last_line("first\n\nsecond\n\n"), "second");
        assert_eq!(last_line(""), "(no output)");
    }

    #[test]
    fn labels_are_human_readable() {
        assert_eq!(target_short("luma"), "Luma");
        assert_eq!(target_short("3ds"), ".3ds");
        assert_eq!(target_short("cia"), "CIA");
    }

    #[test]
    fn validation_flags_an_added_romfs_path_and_accepts_a_replacement() {
        let root = scratch("validate");
        std::fs::create_dir_all(root.join("game_data/romfs")).unwrap();
        std::fs::create_dir_all(root.join("mod/romfs")).unwrap();
        std::fs::write(root.join("game_data/romfs/there.bxon"), b"retail").unwrap();
        std::fs::write(root.join("mod/romfs/there.bxon"), b"modded").unwrap();
        std::fs::write(root.join("mod/romfs/not_there.bxon"), b"new").unwrap();
        std::fs::write(root.join("mod/mod.json"), b"{ not json").unwrap();

        let (tx, _rx) = channel();
        let settings = Settings::default();
        let rows = validate_workspace(&root, &settings, &tx);
        let added = rows
            .iter()
            .find(|r| r.label == "romfs/not_there.bxon")
            .expect("added path row");
        // A new path is legal for the 3ds/cia targets (the RomFS tables are rebuilt);
        // it is only the Luma target that cannot mount it.
        assert_eq!(added.level, CheckLevel::Warn);
        assert!(added.detail.contains("new RomFS path"));
        let ok = rows
            .iter()
            .find(|r| r.label == "romfs/there.bxon")
            .expect("replacement row");
        assert_eq!(ok.level, CheckLevel::Ok);
        let meta = rows.iter().find(|r| r.label == "mod.json").expect("meta row");
        assert_eq!(meta.level, CheckLevel::Error);
        assert!(rows.iter().any(|r| r.level == CheckLevel::Error));
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn revert_deletes_the_override_and_updates_the_list() {
        let root = scratch("revert");
        std::fs::create_dir_all(root.join("game_data/romfs/level3d")).unwrap();
        std::fs::create_dir_all(root.join("mod/romfs/level3d")).unwrap();
        std::fs::write(root.join("game_data/romfs/level3d/b001.pack"), b"retail").unwrap();
        std::fs::write(root.join("mod/romfs/level3d/b001.pack"), b"modded").unwrap();

        let mut panel = PlaytestPanel::default();
        panel.changes = scan_changes(&root);
        assert_eq!(panel.changes.len(), 1);
        panel.revert(&root, 0);
        assert!(!root.join("mod/romfs/level3d/b001.pack").exists());
        assert!(panel.changes.is_empty());
        let _ = std::fs::remove_dir_all(&root);
    }

    #[test]
    fn copy_to_sd_copies_the_title_folder_and_replaces_an_old_copy() {
        let root = scratch("copy_root");
        let sd = scratch("copy_sd");
        let title = TITLE_ID_FALLBACK;
        let luma = root.join("out/luma/titles").join(title);
        std::fs::create_dir_all(luma.join("romfs")).unwrap();
        std::fs::write(luma.join("romfs/thing.pack"), b"payload").unwrap();
        let old = sd.join("luma/titles").join(title).join("stale.pack");
        std::fs::create_dir_all(old.parent().unwrap()).unwrap();
        std::fs::write(&old, b"old").unwrap();

        let settings = Settings::default();
        let (tx, rx) = channel();
        copy_to_sd_job(root.clone(), settings, sd.display().to_string(), tx);
        let mut ok = false;
        while let Ok(message) = rx.try_recv() {
            if let JobMsg::Finished { ok: finished, .. } = message {
                ok = finished;
            }
        }
        assert!(ok, "copy reported success");
        assert!(sd.join("luma/titles").join(title).join("romfs/thing.pack").is_file());
        assert!(!old.exists(), "the previous copy was cleared");
        let _ = std::fs::remove_dir_all(&root);
        let _ = std::fs::remove_dir_all(&sd);
    }
}

