//! Global search across every catalogue.

use eframe::egui;

use crate::app::{Section, ViewerApp};
use crate::theme;
use crate::utils::{elide, human_count, human_size};

const PER_SCOPE: usize = 80;

#[derive(Clone, Copy, PartialEq, Eq)]
enum Scope {
    All,
    Areas,
    Textures,
    Models,
    Layouts,
    Scripts,
    Tables,
    Audio,
    Code,
    Dialogues,
}

const SCOPES: [Scope; 10] = [
    Scope::All,
    Scope::Areas,
    Scope::Textures,
    Scope::Models,
    Scope::Layouts,
    Scope::Scripts,
    Scope::Tables,
    Scope::Audio,
    Scope::Code,
    Scope::Dialogues,
];

impl Scope {
    fn label(self) -> &'static str {
        match self {
            Scope::All => "Everything",
            Scope::Areas => "Map areas",
            Scope::Textures => "Textures",
            Scope::Models => "Models",
            Scope::Layouts => "Layouts",
            Scope::Scripts => "Scripts",
            Scope::Tables => "Tables",
            Scope::Audio => "Audio",
            Scope::Code => "Code",
            Scope::Dialogues => "Dialogues",
        }
    }
}

enum Jump {
    Area(String),
    Texture(String),
    Model(String),
    Layout(String),
    Script(String),
    Table(String),
    Audio(String),
    Code(String),
    Dialogue { query: String },
}

struct Hit {
    scope: &'static str,
    label: String,
    detail: String,
    jump: Jump,
}

pub struct SearchPanel {
    pub query: String,
    scope: Scope,
    hits: Vec<Hit>,
    totals: Vec<(&'static str, usize)>,
    elapsed_ms: f32,
    pub dirty: bool,
    request: Option<String>,
}

impl Default for SearchPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            scope: Scope::All,
            hits: Vec::new(),
            totals: Vec::new(),
            elapsed_ms: 0.0,
            dirty: false,
            request: None,
        }
    }
}

impl SearchPanel {
    pub fn request(&mut self, query: &str) {
        self.query = query.to_string();
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.hits.clear();
        self.totals.clear();
        self.dirty = true;
    }

    pub fn summary(&self) -> String {
        if self.hits.is_empty() {
            "no search yet".into()
        } else {
            let total: usize = self.totals.iter().map(|(_, n)| *n).sum();
            format!("{} matches \u{b7} {:.0} ms", human_count(total), self.elapsed_ms)
        }
    }

    fn run(&mut self, data: Option<&crate::app::Data>) {
        let Some(data) = data else { return };
        let started = std::time::Instant::now();
        let query = self.query.trim().to_string();
        let lower = query.to_lowercase();
        self.hits.clear();
        self.totals.clear();
        if query.is_empty() {
            return;
        }
        let wanted = |scope: Scope| self.scope == Scope::All || self.scope == scope;

        if wanted(Scope::Areas) {
            let matches: Vec<&String> = data
                .areas
                .areas
                .iter()
                .filter(|a| a.to_lowercase().contains(&lower))
                .collect();
            self.totals.push(("Areas", matches.len()));
            for area in matches.iter().take(PER_SCOPE) {
                let dossier = data.areas.dossier(area);
                self.hits.push(Hit {
                    scope: "areas",
                    label: (*area).clone(),
                    detail: format!(
                        "{} assets \u{b7} {} textures \u{b7} {} models \u{b7} {} scripts",
                        dossier.asset_count(),
                        dossier.textures.len(),
                        dossier.models.len(),
                        dossier.scripts.len()
                    ),
                    jump: Jump::Area((*area).clone()),
                });
            }
        }
        if wanted(Scope::Textures) {
            let found = data.textures.search(&query, None, None);
            self.totals.push(("Textures", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let tex = &data.textures.items[*index];
                self.hits.push(Hit {
                    scope: "textures",
                    label: tex.name.clone(),
                    detail: format!("{}  \u{b7}  {}  \u{b7}  {}", tex.pack, tex.dims(), human_size(tex.size)),
                    jump: Jump::Texture(tex.name.clone()),
                });
            }
        }
        if wanted(Scope::Models) {
            let found = data.models.search(&query, None);
            self.totals.push(("Models", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let model = &data.models.items[*index];
                self.hits.push(Hit {
                    scope: "models",
                    label: model.name.clone(),
                    detail: format!("{}  \u{b7}  {}", model.category, human_size(model.size)),
                    jump: Jump::Model(model.name.clone()),
                });
            }
        }
        if wanted(Scope::Layouts) {
            let found = data.layouts.search(&query, None, None);
            self.totals.push(("Layouts", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let layout = &data.layouts.items[*index];
                self.hits.push(Hit {
                    scope: "layouts",
                    label: layout.stem.clone(),
                    detail: format!("{}  \u{b7}  {}  \u{b7}  {}", layout.pack, layout.kind, human_size(layout.size)),
                    jump: Jump::Layout(layout.stem.clone()),
                });
            }
        }
        if wanted(Scope::Scripts) {
            let found = data.scripts.search(&query);
            self.totals.push(("Scripts", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let script = &data.scripts.items[*index];
                self.hits.push(Hit {
                    scope: "scripts",
                    label: script.area.clone(),
                    detail: human_size(script.size),
                    jump: Jump::Script(script.area.clone()),
                });
            }
        }
        if wanted(Scope::Tables) {
            let found = data.tables.search(&query, None);
            self.totals.push(("Tables", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let table = &data.tables.items[*index];
                self.hits.push(Hit {
                    scope: "tables",
                    label: table.name.clone(),
                    detail: format!("{}  \u{b7}  {}", table.category, human_size(table.size)),
                    jump: Jump::Table(table.name.clone()),
                });
            }
        }
        if wanted(Scope::Audio) {
            let found = data.audio.search_streams(&query, None);
            self.totals.push(("Audio", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let stream = &data.audio.streams[*index];
                self.hits.push(Hit {
                    scope: "audio",
                    label: stream.name.clone(),
                    detail: human_size(stream.size),
                    jump: Jump::Audio(stream.name.clone()),
                });
            }
        }
        if wanted(Scope::Code) {
            let found = data.code.search(&query, None, 200_000);
            self.totals.push(("Code", found.len()));
            for index in found.iter().take(PER_SCOPE) {
                let func = &data.code.functions[*index];
                self.hits.push(Hit {
                    scope: "code",
                    label: func.name.clone(),
                    detail: format!("{}  \u{b7}  {} bytes  \u{b7}  {}", func.addr_hex(), func.size, func.mode),
                    jump: Jump::Code(func.addr_hex()),
                });
            }
        }
        if wanted(Scope::Dialogues) && data.dialogues.path.exists() {
            let mut db = crate::data::dialogues::DialogueDb::new(data.dialogues.path.clone());
            let rows = db.search_sources(&query, None, None, None, 0, PER_SCOPE);
            let total = db.count_sources(&query, None, None, None);
            self.totals.push(("Dialogues", total));
            for row in rows {
                let jp = row.jp.split_whitespace().collect::<Vec<_>>().join(" ");
                self.hits.push(Hit {
                    scope: "dialogues",
                    label: format!("#{}", row.id),
                    detail: format!("{}  \u{b7}  {}", row.status_text(), elide(&jp, 90)),
                    jump: Jump::Dialogue { query: row.jp.clone() },
                });
            }
        }
        self.elapsed_ms = started.elapsed().as_secs_f32() * 1000.0;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if app.panels.search.dirty {
        let data = app.data.as_deref();
        let panel = &mut app.panels.search;
        panel.dirty = false;
        panel.run(data);
    }
    ui.horizontal(|ui| {
        ui.label(theme::heading("Search"));
        ui.label(theme::faint_label(app.panels.search.summary()));
    });
    ui.horizontal(|ui| {
        let changed = ui
            .add(
                egui::TextEdit::singleline(&mut app.panels.search.query)
                    .hint_text("Search everything\u{2026}")
                    .desired_width(420.0),
            )
            .changed();
        if changed {
            app.panels.search.dirty = true;
        }
        let scope = app.panels.search.scope;
        egui::ComboBox::from_id_salt("search_scope")
            .selected_text(scope.label())
            .width(140.0)
            .show_ui(ui, |ui| {
                for option in SCOPES {
                    if ui.selectable_label(app.panels.search.scope == option, option.label()).clicked() {
                        app.panels.search.scope = option;
                        app.panels.search.dirty = true;
                    }
                }
            });
        if ui.button("Search").clicked() {
            app.panels.search.dirty = true;
        }
        let totals = app.panels.search.totals.clone();
        if !totals.is_empty() {
            ui.label(theme::faint_label(
                totals
                    .iter()
                    .map(|(scope, count)| format!("{scope} {}", human_count(*count)))
                    .collect::<Vec<_>>()
                    .join("  \u{b7}  "),
            ));
        }
    });
    ui.separator();

    let mut jump: Option<Jump> = None;
    let hits = &app.panels.search.hits;
    if hits.is_empty() {
        ui.label(theme::faint_label("Type a query to search every catalogue at once."));
        return;
    }
    let mut index = 0usize;
    egui::ScrollArea::vertical()
        .id_salt("search_results")
        .auto_shrink([false, false])
        .show(ui, |ui| {
            let mut current_scope = "";
            for hit in hits.iter() {
                if hit.scope != current_scope {
                    current_scope = hit.scope;
                    let total = app
                        .panels
                        .search
                        .totals
                        .iter()
                        .find(|(name, _)| name.to_lowercase().starts_with(current_scope))
                        .map(|(_, count)| *count)
                        .unwrap_or(0);
                    ui.add_space(6.0);
                    ui.label(
                        egui::RichText::new(format!(
                            "{}  \u{b7}  {} matches",
                            scope_title(current_scope),
                            human_count(total)
                        ))
                        .color(theme::TEXT_DIM)
                        .strong(),
                    );
                }
                let text = egui::RichText::new(format!(
                    "{:<34}  {}",
                    elide(&hit.label, 34),
                    hit.detail
                ))
                .size(12.0)
                .color(theme::TEXT);
                let response = ui.selectable_label(false, text);
                if response.clicked() {
                    index = hits.iter().position(|h| std::ptr::eq(h, hit)).unwrap_or(0);
                }
                if response.double_clicked() {
                    jump = Some(clone_jump(&hit.jump));
                }
            }
            let _ = index;
        });
    if let Some(jump) = jump {
        apply_jump(app, jump);
    }
}

fn clone_jump(jump: &Jump) -> Jump {
    match jump {
        Jump::Area(v) => Jump::Area(v.clone()),
        Jump::Texture(v) => Jump::Texture(v.clone()),
        Jump::Model(v) => Jump::Model(v.clone()),
        Jump::Layout(v) => Jump::Layout(v.clone()),
        Jump::Script(v) => Jump::Script(v.clone()),
        Jump::Table(v) => Jump::Table(v.clone()),
        Jump::Audio(v) => Jump::Audio(v.clone()),
        Jump::Code(v) => Jump::Code(v.clone()),
        Jump::Dialogue { query } => Jump::Dialogue { query: query.clone() },
    }
}

fn apply_jump(app: &mut ViewerApp, jump: Jump) {
    match jump {
        Jump::Area(area) => app.open_area(&area),
        Jump::Texture(name) => app.open_textures(&name, None),
        Jump::Model(name) => app.open_model(&name),
        Jump::Layout(stem) => app.open_layout(&stem),
        Jump::Script(area) => app.open_scripts(&area),
        Jump::Table(name) => app.open_tables(&name),
        Jump::Audio(name) => app.open_audio(&name),
        Jump::Code(addr) => app.open_code(&addr),
        Jump::Dialogue { query } => {
            let snippet: String = query.chars().take(48).collect();
            app.open_dialogues(&snippet, None);
        }
    }
}

fn scope_title(scope: &str) -> &'static str {
    match scope {
        "areas" => "Map areas",
        "textures" => "Textures",
        "models" => "Models",
        "layouts" => "Layouts",
        "scripts" => "Scripts",
        "tables" => "Tables",
        "audio" => "Audio",
        "code" => "Code",
        _ => "Dialogues",
    }
}

pub fn _unused(_: Section) {}
