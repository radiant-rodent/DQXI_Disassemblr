//! "Open in my editor": the paths of the user's own image / audio / 3D programs.
//!
//! The viewer does not edit pictures or sounds itself. The user points it at the program they
//! like (Paint.NET, GIMP, Photoshop, Audacity, Blender, ...) once, and the Assets browsers hand
//! files to it. Paths are saved in `editor_projects/external_editors.json`.

use std::path::{Path, PathBuf};
use std::sync::Mutex;

use eframe::egui;
use serde::{Deserialize, Serialize};

use crate::theme;

#[derive(Clone, Default, Serialize, Deserialize)]
#[serde(default)]
struct Editors {
    image: String,
    audio: String,
    model: String,
}

static STATE: Mutex<Option<Editors>> = Mutex::new(None);
/// Result of a "Browse..." dialog running on its own thread: (kind, chosen exe).
static BROWSED: Mutex<Option<(String, String)>> = Mutex::new(None);

fn file(root: &Path) -> PathBuf {
    root.join("editor_projects").join("external_editors.json")
}

fn with<R>(root: &Path, f: impl FnOnce(&mut Editors) -> R) -> R {
    let mut guard = STATE.lock().unwrap_or_else(|e| e.into_inner());
    let editors = guard.get_or_insert_with(|| {
        std::fs::read_to_string(file(root))
            .ok()
            .and_then(|t| serde_json::from_str(&t).ok())
            .unwrap_or_default()
    });
    f(editors)
}

fn slot<'a>(e: &'a mut Editors, kind: &str) -> &'a mut String {
    match kind {
        "audio" => &mut e.audio,
        "model" => &mut e.model,
        _ => &mut e.image,
    }
}

fn save(root: &Path) {
    let text = with(root, |e| serde_json::to_string_pretty(e).unwrap_or_default());
    let path = file(root);
    if let Some(parent) = path.parent() {
        let _ = std::fs::create_dir_all(parent);
    }
    let _ = std::fs::write(path, text);
}

pub fn configured(root: &Path, kind: &str) -> String {
    with(root, |e| slot(e, kind).clone())
}

/// Starts `file` in the user's editor for `kind`. `Err` says what to fix.
pub fn launch(root: &Path, kind: &str, file: &Path) -> Result<(), String> {
    let exe = configured(root, kind);
    if exe.trim().is_empty() {
        return Err("no editor chosen yet".into());
    }
    let exe = exe.trim().trim_matches('"').to_string();
    if !Path::new(&exe).is_file() {
        return Err(format!("editor not found: {exe}"));
    }
    std::process::Command::new(&exe)
        .arg(file)
        .spawn()
        .map(|_| ())
        .map_err(|e| format!("could not start {exe}: {e}"))
}

fn browse(kind: &str, ctx: egui::Context) {
    let kind = kind.to_string();
    std::thread::spawn(move || {
        let script = "Add-Type -AssemblyName System.Windows.Forms; \
            $d = New-Object System.Windows.Forms.OpenFileDialog; \
            $d.Filter = 'Programs (*.exe)|*.exe|All files (*.*)|*.*'; \
            $d.Title = 'Choose your editor'; \
            if ($d.ShowDialog() -eq 'OK') { $d.FileName }";
        let mut cmd = std::process::Command::new("powershell");
        cmd.args(["-NoProfile", "-STA", "-Command", script]);
        #[cfg(windows)]
        {
            use std::os::windows::process::CommandExt;
            cmd.creation_flags(0x0800_0000); // no console window
        }
        if let Ok(out) = cmd.output() {
            let chosen = String::from_utf8_lossy(&out.stdout).trim().to_string();
            if !chosen.is_empty() {
                *BROWSED.lock().unwrap_or_else(|e| e.into_inner()) = Some((kind, chosen));
                ctx.request_repaint();
            }
        }
    });
}

/// Draws the "Edit in <program>" button and a small settings toggle. Returns true when the user
/// clicked Edit and an editor is set - the caller prepares the file and calls [`launch`].
/// With no editor chosen yet the button opens the chooser instead.
pub fn row(ui: &mut egui::Ui, root: &Path, kind: &str, noun: &str) -> bool {
    if let Some((k, exe)) = BROWSED.lock().unwrap_or_else(|e| e.into_inner()).take() {
        with(root, |e| *slot(e, &k) = exe);
        save(root);
    }
    let open_id = ui.make_persistent_id(("external_editor_setup", kind));
    let mut open: bool = ui.data(|d| d.get_temp(open_id)).unwrap_or(false);
    let exe = configured(root, kind);
    let name = Path::new(exe.trim().trim_matches('"'))
        .file_stem()
        .map(|s| s.to_string_lossy().into_owned())
        .unwrap_or_default();
    let mut edit = false;
    ui.horizontal(|ui| {
        let label = if name.is_empty() {
            format!("Edit in {noun}\u{2026}")
        } else {
            format!("Edit in {name}")
        };
        let tip = if name.is_empty() {
            format!("Choose the program you use for this ({noun}) first")
        } else {
            format!("Open a working copy in {exe}")
        };
        if ui.button(label).on_hover_text(tip).clicked() {
            if name.is_empty() {
                open = true;
            } else {
                edit = true;
            }
        }
        if ui.small_button("Set editor").on_hover_text("Choose which program opens these files").clicked() {
            open = !open;
        }
    });
    if open {
        let mut text = exe.clone();
        ui.horizontal(|ui| {
            ui.add(
                egui::TextEdit::singleline(&mut text)
                    .hint_text(format!("path to your {noun} (.exe)"))
                    .desired_width(ui.available_width() - 150.0),
            );
            if ui.button("Browse\u{2026}").clicked() {
                browse(kind, ui.ctx().clone());
            }
            if ui.button("Done").clicked() {
                open = false;
            }
        });
        if text != exe {
            with(root, |e| *slot(e, kind) = text);
            save(root);
        }
        ui.label(theme::faint_label(
            "Set up once - e.g. Paint.NET, GIMP or Photoshop. The viewer only hands the file over.",
        ));
    }
    ui.data_mut(|d| d.insert_temp(open_id, open));
    edit
}
