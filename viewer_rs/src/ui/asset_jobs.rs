//! Shared background runner for the asset `Export…` / `Replace…` workflows.
//!
//! Every family (textures, models, audio, layouts, maps) shells out to
//! `tools/asset_replace.py` instead of re-implementing BFLIM/BCH/BCSTM/BFLYT
//! encoding in Rust. That keeps one validated implementation of each format
//! (the same one the tests and the command line use) and means a new 3DS format
//! detail only has to be fixed in one place.
//!
//! The Python tool prints one JSON object as its last line; this job parses it
//! and exposes `preview`, `staged`, `warnings` and `error` to the panel.

use std::path::{Path, PathBuf};
use std::sync::mpsc::{channel, Receiver, TryRecvError};

use eframe::egui;
use serde_json::Value;

#[derive(Default)]
pub struct AssetJob {
    rx: Option<Receiver<Result<Value, String>>>,
    pub running: bool,
    /// One-line result for the panel (also copied to the status bar by callers).
    pub message: String,
    pub warnings: Vec<String>,
    pub error: Option<String>,
    pub result: Option<Value>,
}

impl AssetJob {
    pub fn is_running(&self) -> bool {
        self.running
    }

    /// Starts `python tools/asset_replace.py <args…> --json` on a worker thread.
    pub fn start(&mut self, root: &Path, args: Vec<String>) {
        if self.running {
            return;
        }
        let root = root.to_path_buf();
        let (tx, rx) = channel();
        self.rx = Some(rx);
        self.running = true;
        self.message = "running…".into();
        self.warnings.clear();
        self.error = None;
        self.result = None;
        std::thread::spawn(move || {
            let tool = root.join("tools").join("asset_replace.py");
            let output = std::process::Command::new("python")
                .arg(&tool)
                .args(&args)
                .arg("--json")
                .current_dir(&root)
                .output();
            let job = match output {
                Ok(output) => {
                    let stdout = String::from_utf8_lossy(&output.stdout).into_owned();
                    let stderr = String::from_utf8_lossy(&output.stderr).into_owned();
                    // The JSON result is always the last line beginning with '{'.
                    let parsed = stdout
                        .lines()
                        .rev()
                        .find(|line| line.trim_start().starts_with('{'))
                        .and_then(|line| serde_json::from_str::<Value>(line).ok());
                    match parsed {
                        Some(value) => Ok(value),
                        None => Err(format!(
                            "the asset tool produced no result ({}).\n{}\n{}",
                            output.status,
                            stdout.trim(),
                            stderr.trim()
                        )),
                    }
                }
                Err(err) => Err(format!(
                    "could not run python ({err}). Check that Python 3 is on PATH, then retry."
                )),
            };
            let _ = tx.send(job);
        });
    }

    /// Polls the worker. Returns true when a result arrived this frame.
    pub fn poll(&mut self) -> bool {
        let Some(rx) = &self.rx else { return false };
        match rx.try_recv() {
            Ok(Ok(value)) => {
                self.running = false;
                self.rx = None;
                let ok = value.get("ok").and_then(Value::as_bool).unwrap_or(false);
                self.warnings = value
                    .get("warnings")
                    .and_then(Value::as_array)
                    .map(|items| items.iter().filter_map(|v| v.as_str().map(str::to_owned)).collect())
                    .unwrap_or_default();
                if ok {
                    self.message = success_message(&value);
                    self.error = None;
                } else {
                    self.error = Some(
                        value
                            .get("error")
                            .and_then(Value::as_str)
                            .unwrap_or("the asset tool reported a failure")
                            .to_string(),
                    );
                    self.message = "failed".into();
                }
                self.result = Some(value);
                true
            }
            Ok(Err(message)) => {
                self.running = false;
                self.rx = None;
                self.result = None;
                self.error = Some(message.clone());
                self.message = "failed".into();
                true
            }
            Err(TryRecvError::Empty) => false,
            Err(TryRecvError::Disconnected) => {
                self.running = false;
                self.rx = None;
                self.error = Some("the asset worker stopped unexpectedly".into());
                true
            }
        }
    }

    pub fn preview_path(&self, root: &Path) -> Option<PathBuf> {
        let value = self.result.as_ref()?.get("preview")?.as_str()?;
        Some(absolute(root, value))
    }

    pub fn staged_path(&self) -> Option<String> {
        let staged = self.result.as_ref()?.get("staged")?;
        staged
            .get("mod_file")
            .and_then(Value::as_str)
            .map(str::to_owned)
    }

    /// True when the last result was a successful replace (as opposed to export/inspect).
    pub fn replaced(&self) -> bool {
        self.result
            .as_ref()
            .and_then(|v| v.get("action"))
            .and_then(Value::as_str)
            == Some("replace")
    }
}

fn success_message(value: &Value) -> String {
    let action = value.get("action").and_then(Value::as_str).unwrap_or("done");
    if let Some(staged) = value.get("staged").and_then(|s| s.get("mod_file")).and_then(Value::as_str) {
        return format!("{action} OK · staged {staged}");
    }
    if let Some(preview) = value.get("preview").and_then(Value::as_str) {
        return format!("{action} OK · preview {preview}");
    }
    if let Some(exported) = value.get("exported").and_then(Value::as_str) {
        return format!("{action} OK · {exported}");
    }
    if let Some(exported) = value.get("exported_dir").and_then(Value::as_str) {
        return format!("{action} OK · {exported}");
    }
    format!("{action} OK")
}

fn absolute(root: &Path, path: &str) -> PathBuf {
    let candidate = PathBuf::from(path);
    if candidate.is_absolute() {
        candidate
    } else {
        root.join(candidate)
    }
}

/// State shared by a panel's Export/Replace controls.
#[derive(Default)]
pub struct AssetTools {
    /// File the modder edited (absolute, or relative to the project root).
    pub import_path: String,
    /// Where `Export…` writes; empty means `build/exports`.
    pub export_dir: String,
    /// Allow the tool to scale a differently sized PNG (off: refuse + explain).
    pub resize: bool,
    pub job: AssetJob,
    /// Mirrors of the job's last result, kept on the panel for compact call sites.
    pub message: String,
    pub error: Option<String>,
}

impl AssetTools {
    pub fn start_export(&mut self, root: &Path, family: &str, asset: &str) {
        let dir = if self.export_dir.trim().is_empty() {
            "build/exports".to_string()
        } else {
            self.export_dir.trim().to_string()
        };
        self.job.start(
            root,
            vec![
                "export".into(),
                "--family".into(),
                family.into(),
                "--asset".into(),
                asset.into(),
                "--out".into(),
                dir,
            ],
        );
    }

    pub fn start_replace(
        &mut self,
        root: &Path,
        family: &str,
        asset: &str,
        extra: Vec<String>,
        stage: bool,
    ) {
        if self.import_path.trim().is_empty() {
            self.job.error = Some("choose the edited file first (paste its path)".into());
            return;
        }
        let mut args = vec![
            "replace".to_string(),
            "--family".into(),
            family.into(),
            "--asset".into(),
            asset.into(),
            "--file".into(),
            self.import_path.trim().into(),
            "--preview".into(),
        ];
        if self.resize {
            args.push("--allow-resize".into());
        }
        args.extend(extra);
        if stage {
            args.push("--stage".into());
        }
        self.job.start(root, args);
    }

    /// Where the encoded preview was written (project-relative result → absolute).
    pub fn preview_path(&self, root: &Path) -> Option<PathBuf> {
        self.job.preview_path(root)
    }

    /// Draws the shared status/warning block. Returns true on a fresh result.
    pub fn show_status(&mut self, ui: &mut egui::Ui, root: &Path) -> bool {
        let fresh = self.job.poll();
        self.message = self.job.message.clone();
        self.error = self.job.error.clone();
        if self.job.running {
            ui.horizontal(|ui| {
                ui.spinner();
                ui.label(crate::theme::dim_label(self.job.message.clone()));
            });
            ui.ctx().request_repaint_after(std::time::Duration::from_millis(120));
        } else if let Some(error) = &self.job.error {
            ui.colored_label(crate::theme::ERR, format!("✖ {error}"));
        } else if !self.job.message.is_empty() && self.job.message != "running…" {
            ui.label(crate::theme::dim_label(self.job.message.replace(root.to_string_lossy().as_ref(), "")));
        }
        for warning in &self.job.warnings {
            ui.label(egui::RichText::new(format!("⚠ {warning}")).color(crate::theme::WARN).size(11.5));
        }
        if self.job.staged_path().is_some() {
            ui.label(crate::theme::faint_label(
                "Staged in mod/romfs. Export it with Export & Play (Luma LayeredFS).",
            ));
        }
        fresh
    }
}

/// Loads an encoded preview image into the texture cache under a unique key so
/// repeated replacements refresh immediately (files keep the same path).
pub fn load_preview(
    ctx: &egui::Context,
    path: &Path,
    version: u64,
    tag: &str,
) -> Option<egui::TextureHandle> {
    let image = crate::utils::decode_image(path, None).ok()?;
    let key = format!("asset-preview::{tag}::{version}");
    Some(ctx.load_texture(key, image, egui::TextureOptions::LINEAR))
}
