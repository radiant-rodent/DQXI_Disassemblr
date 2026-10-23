//! Application shell: sidebar navigation, header search, status bar, boot.

use std::sync::mpsc::{channel, Receiver, Sender};
use std::sync::{Arc, Mutex};

use eframe::egui;
use eframe::egui_glow::CallbackFn;

use crate::data::areas::AreaIndex;
use crate::data::audio::AudioIndex;
use crate::data::code::CodeIndex;
use crate::data::dialogues::DialogueDb;
use crate::data::layouts::LayoutIndex;
use crate::data::models::ModelIndex;
use crate::data::scripts::ScriptIndex;
use crate::data::tables::TableIndex;
use crate::data::textures::TextureIndex;
use crate::render::gpu::GlRenderer;
use crate::theme;
use crate::ui::panels;
use crate::utils::{human_count, Dirs, ImageCache, Pool};

pub const VERSION: &str = "2.0.0-rust";

// ---------------------------------------------------------------------------
// data bundle
// ---------------------------------------------------------------------------
pub struct Data {
    pub textures: TextureIndex,
    pub models: ModelIndex,
    pub layouts: LayoutIndex,
    pub scripts: ScriptIndex,
    pub tables: TableIndex,
    pub audio: AudioIndex,
    pub code: CodeIndex,
    pub areas: AreaIndex,
    pub dialogues: DialogueDb,
}

/// One finished index, sent from the boot threads to the UI as soon as it is built.
pub enum BootMsg {
    Textures(TextureIndex),
    Models(ModelIndex),
    Layouts(LayoutIndex),
    Scripts(ScriptIndex),
    Tables(TableIndex),
    Audio(AudioIndex),
    Areas(AreaIndex),
    Failed(String),
}

/// Indexes built in the background: the six asset families plus map areas.
pub const BOOT_STEPS: usize = 7;

impl Data {
    /// Empty indexes; the UI is usable immediately and each section fills in
    /// as its index arrives (see [`Data::spawn_indexers`]).
    fn empty(dirs: &Dirs) -> Data {
        Data {
            textures: TextureIndex::default(),
            models: ModelIndex::default(),
            layouts: LayoutIndex::default(),
            scripts: ScriptIndex::default(),
            tables: TableIndex::default(),
            audio: AudioIndex::default(),
            // Code is large and only needed when the Code section is opened.
            code: CodeIndex::default(),
            areas: AreaIndex::default(),
            dialogues: DialogueDb::new(dirs.dialogue_db.clone()),
        }
    }

    /// Builds every index on its own thread and streams each one to the UI the
    /// moment it is done. Map areas cross-reference all the others, so they are
    /// built last from the boot thread's own copies.
    fn spawn_indexers(dirs: Dirs, tx: Sender<BootMsg>) {
        std::thread::Builder::new()
            .name("dqxi-boot".into())
            .spawn(move || {
                let (textures, models, layouts, scripts, audio) = std::thread::scope(|s| {
                    let textures = s.spawn(|| {
                        let mut index = TextureIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Textures(index.clone()));
                        index
                    });
                    let models = s.spawn(|| {
                        let mut index = ModelIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Models(index.clone()));
                        index
                    });
                    let layouts = s.spawn(|| {
                        let mut index = LayoutIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Layouts(index.clone()));
                        index
                    });
                    let scripts = s.spawn(|| {
                        let mut index = ScriptIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Scripts(index.clone()));
                        index
                    });
                    s.spawn(|| {
                        let mut index = TableIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Tables(index));
                    });
                    let audio = s.spawn(|| {
                        let mut index = AudioIndex::default();
                        index.ensure(&dirs);
                        let _ = tx.send(BootMsg::Audio(index.clone()));
                        index
                    });
                    (
                        textures.join().unwrap_or_default(),
                        models.join().unwrap_or_default(),
                        layouts.join().unwrap_or_default(),
                        scripts.join().unwrap_or_default(),
                        audio.join().unwrap_or_default(),
                    )
                });
                let mut dialogues = DialogueDb::new(dirs.dialogue_db.clone());
                let mut areas = AreaIndex::default();
                areas.ensure(&dirs, &textures, &scripts, &audio, &layouts, &models, &mut dialogues);
                let _ = tx.send(BootMsg::Areas(areas));
            })
            .expect("boot thread");
    }

    pub fn summary(&mut self) -> String {
        let mut bits = vec![
            format!("{} textures", human_count(self.textures.items.len())),
            format!("{} models", human_count(self.models.items.len())),
            format!("{} layout files", human_count(self.layouts.items.len())),
            format!("{} scripts", human_count(self.scripts.items.len())),
        ];
        bits.push(format!("{} tables", human_count(self.tables.items.len())));
        bits.push(format!("{} streams", human_count(self.audio.streams.len())));
        bits.push(format!("{} funcs", human_count(self.code.functions.len())));
        if self.dialogues.available() {
            let stats = self.dialogues.stats();
            bits.push(format!("{} dialogues", human_count(stats.sources)));
        }
        bits.push(format!("{} areas", human_count(self.areas.areas.len())));
        bits.join("  \u{b7}  ")
    }
}

// ---------------------------------------------------------------------------
// sections
// ---------------------------------------------------------------------------
#[derive(Clone, Copy, PartialEq, Eq, Debug)]
pub enum Section {
    Overview,
    Search,
    Textures,
    Models,
    Layouts,
    Scripts,
    Tables,
    Audio,
    Code,
    Dialogues,
    Maps,
    Editor,
}

pub const SECTIONS: [Section; 12] = [
    Section::Overview,
    Section::Search,
    Section::Textures,
    Section::Models,
    Section::Layouts,
    Section::Scripts,
    Section::Tables,
    Section::Audio,
    Section::Code,
    Section::Dialogues,
    Section::Maps,
    Section::Editor,
];

impl Section {
    pub fn title(self) -> &'static str {
        match self {
            Section::Overview => "Overview",
            Section::Search => "Search",
            Section::Textures => "Textures",
            Section::Models => "Models",
            Section::Layouts => "Layouts",
            Section::Scripts => "Scripts",
            Section::Tables => "Tables",
            Section::Audio => "Audio",
            Section::Code => "Code",
            Section::Dialogues => "Dialogues",
            Section::Maps => "Maps",
            Section::Editor => "Level Editor",
        }
    }

    /// Draws the section's icon as vector shapes centred on `c` (about 14 px).
    /// Painted rather than typed: the egui fonts lack most symbol glyphs, which
    /// rendered as boxes.
    pub fn paint_icon(self, painter: &egui::Painter, c: egui::Pos2, color: egui::Color32) {
        use egui::{pos2, vec2, Rect, Shape, Stroke, StrokeKind};
        let stroke = Stroke::new(1.4, color);
        let r = |x0: f32, y0: f32, x1: f32, y1: f32| Rect::from_min_max(pos2(c.x + x0, c.y + y0), pos2(c.x + x1, c.y + y1));
        let line = |pts: &[(f32, f32)]| {
            Shape::line(pts.iter().map(|(x, y)| pos2(c.x + x, c.y + y)).collect(), stroke)
        };
        match self {
            Section::Overview => {
                for (x, y) in [(-6.0, -6.0), (1.0, -6.0), (-6.0, 1.0), (1.0, 1.0)] {
                    painter.rect_filled(r(x, y, x + 5.0, y + 5.0), 1.0, color);
                }
            }
            Section::Search => {
                painter.circle_stroke(pos2(c.x - 1.5, c.y - 1.5), 4.5, stroke);
                painter.add(line(&[(1.8, 1.8), (6.0, 6.0)]));
            }
            Section::Textures => {
                painter.rect_stroke(r(-6.5, -5.5, 6.5, 5.5), 1.5, stroke, StrokeKind::Inside);
                painter.add(line(&[(-5.0, 4.0), (-1.5, -0.5), (1.0, 2.0), (3.0, 0.0), (5.0, 4.0)]));
                painter.circle_filled(pos2(c.x + 2.5, c.y - 2.5), 1.2, color);
            }
            Section::Models => {
                // isometric cube
                painter.add(line(&[(0.0, -6.5), (6.0, -3.0), (6.0, 3.5), (0.0, 7.0), (-6.0, 3.5), (-6.0, -3.0), (0.0, -6.5)]));
                painter.add(line(&[(-6.0, -3.0), (0.0, 0.5), (6.0, -3.0)]));
                painter.add(line(&[(0.0, 0.5), (0.0, 7.0)]));
            }
            Section::Layouts => {
                painter.rect_stroke(r(-6.5, -6.0, 6.5, 6.0), 1.5, stroke, StrokeKind::Inside);
                painter.rect_filled(r(-4.5, -4.0, 4.5, -1.5), 0.5, color);
                painter.rect_filled(r(-4.5, 0.5, -0.5, 4.0), 0.5, color);
                painter.rect_filled(r(1.0, 0.5, 4.5, 4.0), 0.5, color);
            }
            Section::Scripts => {
                // page with text lines
                painter.add(line(&[(-5.0, -6.5), (2.0, -6.5), (5.0, -3.5), (5.0, 6.5), (-5.0, 6.5), (-5.0, -6.5)]));
                for y in [-2.5, 0.5, 3.5] {
                    painter.add(line(&[(-3.0, y), (3.0, y)]));
                }
            }
            Section::Tables => {
                painter.rect_stroke(r(-6.5, -5.5, 6.5, 5.5), 1.0, stroke, StrokeKind::Inside);
                painter.add(line(&[(-6.5, -1.8), (6.5, -1.8)]));
                painter.add(line(&[(-6.5, 1.8), (6.5, 1.8)]));
                painter.add(line(&[(-1.5, -5.5), (-1.5, 5.5)]));
            }
            Section::Audio => {
                painter.circle_filled(pos2(c.x - 3.5, c.y + 4.0), 2.4, color);
                painter.circle_filled(pos2(c.x + 4.0, c.y + 2.5), 2.4, color);
                painter.add(line(&[(-1.3, 4.0), (-1.3, -5.5), (6.2, -7.0), (6.2, 2.5)]));
            }
            Section::Code => {
                painter.add(line(&[(-2.5, -5.0), (-6.5, 0.0), (-2.5, 5.0)]));
                painter.add(line(&[(2.5, -5.0), (6.5, 0.0), (2.5, 5.0)]));
                painter.add(line(&[(1.0, -6.0), (-1.0, 6.0)]));
            }
            Section::Dialogues => {
                painter.rect_stroke(r(-6.5, -6.0, 6.5, 2.5), 3.0, stroke, StrokeKind::Inside);
                painter.add(Shape::convex_polygon(
                    vec![pos2(c.x - 3.5, c.y + 2.0), pos2(c.x + 0.5, c.y + 2.0), pos2(c.x - 3.5, c.y + 6.5)],
                    color,
                    Stroke::NONE,
                ));
            }
            Section::Maps => {
                // folded map
                painter.add(line(&[(-6.5, -4.5), (-2.0, -6.5), (2.0, -4.5), (6.5, -6.5), (6.5, 4.5), (2.0, 6.5), (-2.0, 4.5), (-6.5, 6.5), (-6.5, -4.5)]));
                painter.add(line(&[(-2.0, -6.5), (-2.0, 4.5)]));
                painter.add(line(&[(2.0, -4.5), (2.0, 6.5)]));
            }
            Section::Editor => {
                // pencil
                let body = [(-4.5, 6.5), (-6.5, 4.5), (3.0, -5.0), (5.0, -3.0)];
                painter.add(Shape::convex_polygon(
                    body.iter().map(|(x, y)| pos2(c.x + x, c.y + y)).collect(),
                    egui::Color32::TRANSPARENT,
                    stroke,
                ));
                painter.add(line(&[(-6.5, 4.5), (-7.0, 7.0), (-4.5, 6.5)]));
                painter.add(line(&[(1.5, -3.5), (3.5, -1.5)]));
                let _ = vec2(0.0, 0.0);
            }
        }
    }
}

// ---------------------------------------------------------------------------
// application
// ---------------------------------------------------------------------------
pub struct ViewerApp {
    pub dirs: Dirs,
    pub pool: Pool,
    pub thumbs: ImageCache,
    pub preview: ImageCache,
    pub layout_tex: ImageCache,
    pub data: Option<Box<Data>>,
    pub boot_rx: Receiver<BootMsg>,
    pub boot_step: (usize, &'static str),
    pub boot_error: Option<String>,
    pub panels: panels::Panels,
    pub section: Section,
    pub status: String,
    pub search_text: String,
    pub renderer: Arc<Mutex<GlRenderer>>,
    pub renderer_error: Option<String>,
    pub focus_search: bool,
}

impl ViewerApp {
    pub fn new(cc: &eframe::CreationContext<'_>) -> Self {
        theme::apply(&cc.egui_ctx);
        let dirs = Dirs::detect();
        let gl = cc
            .gl
            .clone()
            .expect("the DQXI Explorer & Editor needs the glow (OpenGL) backend");
        let renderer = GlRenderer::new(gl).expect("failed to initialise the OpenGL renderer");
        let (tx, boot_rx) = channel();
        Data::spawn_indexers(dirs.clone(), tx);
        let data = Some(Box::new(Data::empty(&dirs)));
        let thumbs = ImageCache::new(Some(176), 700, Some(dirs.thumbs.clone()));
        let section = match std::env::var("DQXI_START_SECTION").unwrap_or_default().as_str() {
            "search" => Section::Search,
            "textures" => Section::Textures,
            "models" => Section::Models,
            "layouts" => Section::Layouts,
            "scripts" => Section::Scripts,
            "tables" => Section::Tables,
            "audio" => Section::Audio,
            "code" => Section::Code,
            "dialogues" => Section::Dialogues,
            "maps" => Section::Maps,
            "editor" => Section::Editor,
            _ => Section::Overview,
        };
        let start_query = std::env::var("DQXI_START_QUERY").unwrap_or_default();
        let mut panels = panels::Panels::new();
        if !start_query.is_empty() {
            match section {
                Section::Models => panels.models.request(&start_query),
                Section::Textures => panels.textures.request(&start_query, None),
                Section::Layouts => panels.layouts.request(&start_query),
                Section::Scripts => panels.scripts.request(&start_query),
                Section::Tables => panels.tables.request(&start_query),
                Section::Audio => panels.audio.request(&start_query),
                Section::Code => panels.code.request(&start_query),
                Section::Dialogues => panels.dialogues.request(&start_query, None),
                Section::Maps => panels.maps.request(&start_query),
                Section::Editor => {}
                _ => panels.search.request(&start_query),
            }
        }
        Self {
            thumbs,
            preview: ImageCache::new(None, 8, None),
            layout_tex: ImageCache::new(Some(512), 240, None),
            dirs,
            pool: Pool::new(6),
            data,
            boot_rx,
            boot_step: (0, "starting"),
            boot_error: None,
            panels,
            section,
            status: "Ready \u{2014} building indexes in the background\u{2026}".into(),
            search_text: String::new(),
            renderer: Arc::new(Mutex::new(renderer)),
            renderer_error: None,
            focus_search: section == Section::Overview,
        }
    }

    pub fn data(&self) -> Option<&Data> {
        self.data.as_deref()
    }

    pub fn data_mut(&mut self) -> Option<&mut Data> {
        self.data.as_mut().map(|d| d.as_mut())
    }

    pub fn poll_boot(&mut self) {
        loop {
            let msg = match self.boot_rx.try_recv() {
                Ok(msg) => msg,
                Err(std::sync::mpsc::TryRecvError::Empty) => break,
                Err(std::sync::mpsc::TryRecvError::Disconnected) => {
                    if self.boot_step.0 < BOOT_STEPS && self.boot_error.is_none() {
                        self.boot_error = Some("indexer stopped unexpectedly".into());
                    }
                    break;
                }
            };
            let Some(data) = self.data.as_deref_mut() else { break };
            let label = match msg {
                BootMsg::Textures(index) => {
                    data.textures = index;
                    "textures"
                }
                BootMsg::Models(index) => {
                    data.models = index;
                    "models"
                }
                BootMsg::Layouts(index) => {
                    data.layouts = index;
                    "layouts"
                }
                BootMsg::Scripts(index) => {
                    data.scripts = index;
                    "scripts"
                }
                BootMsg::Tables(index) => {
                    data.tables = index;
                    "tables"
                }
                BootMsg::Audio(index) => {
                    data.audio = index;
                    "audio"
                }
                BootMsg::Areas(index) => {
                    data.areas = index;
                    "map areas"
                }
                BootMsg::Failed(e) => {
                    self.boot_error = Some(e);
                    continue;
                }
            };
            self.boot_step = (self.boot_step.0 + 1, label);
            // global search results may now include the new family
            self.panels.search.dirty = true;
            if self.booted() {
                self.status = "Ready".into();
            }
        }
    }

    /// True once every background index has arrived.
    pub fn booted(&self) -> bool {
        self.boot_step.0 >= BOOT_STEPS
    }

    fn boot_label(&mut self) -> String {
        if let Some(err) = &self.boot_error {
            return format!("indexing failed: {err}");
        }
        if self.booted() {
            if let Some(data) = self.data.as_deref_mut() {
                return data.summary();
            }
        }
        let (step, label) = self.boot_step;
        if step == 0 {
            return format!("indexing\u{2026}  (0 / {BOOT_STEPS})");
        }
        format!("indexed {label}\u{2026}  ({step} / {BOOT_STEPS})")
    }

    // -- navigation ------------------------------------------------------
    pub fn go(&mut self, section: Section) {
        self.section = section;
    }

    pub fn open_textures(&mut self, query: &str, pack: Option<&str>) {
        self.panels.textures.request(query, pack);
        self.section = Section::Textures;
    }

    pub fn open_model(&mut self, name: &str) {
        self.panels.models.request(name);
        self.section = Section::Models;
    }

    pub fn open_layout(&mut self, query: &str) {
        self.panels.layouts.request(query);
        self.section = Section::Layouts;
    }

    pub fn open_scripts(&mut self, query: &str) {
        self.panels.scripts.request(query);
        self.section = Section::Scripts;
    }

    pub fn open_tables(&mut self, query: &str) {
        self.panels.tables.request(query);
        self.section = Section::Tables;
    }

    pub fn open_audio(&mut self, query: &str) {
        self.panels.audio.request(query);
        self.section = Section::Audio;
    }

    pub fn open_code(&mut self, query: &str) {
        self.panels.code.request(query);
        self.section = Section::Code;
    }

    pub fn open_dialogues(&mut self, query: &str, file: Option<&str>) {
        self.panels.dialogues.request(query, file);
        self.section = Section::Dialogues;
    }

    pub fn open_area(&mut self, area: &str) {
        self.panels.maps.request(area);
        self.section = Section::Maps;
    }

    pub fn open_search(&mut self, query: &str) {
        self.panels.search.request(query);
        self.section = Section::Search;
    }

    // -- rendering -------------------------------------------------------
    fn header(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.vertical(|ui| {
                ui.label(
                    egui::RichText::new("DQXI Explorer & Editor")
                        .color(theme::ACCENT)
                        .size(16.0)
                        .strong(),
                );
                ui.label(theme::faint_label("Dragon Quest XI (3DS) \u{b7} project browser and level editor"));
            });
            ui.add_space(14.0);
            let entry = ui.add(
                egui::TextEdit::singleline(&mut self.search_text)
                    .hint_text("Search everything\u{2026}  (Ctrl+F)")
                    .desired_width(f32::INFINITY),
            );
            if self.focus_search {
                entry.request_focus();
                self.focus_search = false;
            }
            if entry.lost_focus() && ui.input(|i| i.key_pressed(egui::Key::Enter)) {
                let query = self.search_text.clone();
                self.open_search(&query);
            }
            if ui.button("Search").clicked() {
                let query = self.search_text.clone();
                self.open_search(&query);
            }
            if ui.button("Project folder").clicked() {
                let _ = std::process::Command::new("explorer")
                    .arg(&self.dirs.root)
                    .spawn();
            }
        });
    }

    fn sidebar(&mut self, ui: &mut egui::Ui) {
        ui.add_space(6.0);
        ui.label(
            egui::RichText::new("DQXI")
                .color(theme::ACCENT)
                .size(22.0)
                .strong(),
        );
        ui.label(theme::faint_label("Dragon Quest XI \u{b7} 3DS"));
        ui.separator();
        ui.add_space(4.0);
        for section in SECTIONS {
            let selected = section == self.section;
            // room on the left for the painted icon
            let text = format!("        {}", section.title());
            let label = if selected {
                egui::RichText::new(text).color(theme::ACCENT).strong()
            } else {
                egui::RichText::new(text).color(theme::TEXT_DIM)
            };
            let button = egui::Button::new(label)
                .fill(if selected { theme::BG_SELECT } else { theme::BG_PANEL })
                .min_size(egui::vec2(ui.available_width(), 26.0));
            let response = ui.add(button);
            let color = if selected { theme::ACCENT } else { theme::TEXT_DIM };
            section.paint_icon(ui.painter(), egui::pos2(response.rect.left() + 18.0, response.rect.center().y), color);
            if response.clicked() {
                self.go(section);
            }
        }
        ui.with_layout(egui::Layout::bottom_up(egui::Align::LEFT), |ui| {
            ui.add_space(6.0);
            ui.label(theme::faint_label(self.boot_label()));
            let progress = self.boot_step.0.min(BOOT_STEPS) as f32 / BOOT_STEPS as f32;
            ui.add(egui::ProgressBar::new(progress).desired_height(4.0));
            ui.separator();
        });
    }

    fn status_bar(&mut self, ui: &mut egui::Ui) {
        ui.horizontal(|ui| {
            ui.label(theme::dim_label(self.status.clone()));
            ui.with_layout(egui::Layout::right_to_left(egui::Align::Center), |ui| {
                let right = if self.section == Section::Search {
                    self.panels.search.summary()
                } else if self.data.is_some() {
                    format!("{}  \u{b7}  {}", self.section.title(), self.section_detail())
                } else {
                    self.section.title().to_string()
                };
                ui.label(egui::RichText::new(right).color(theme::ACCENT).size(12.0));
            });
        });
    }

    fn section_detail(&mut self) -> String {
        if self.section == Section::Editor {
            return format!("{} decoded maps", human_count(self.panels.editor.map_count()));
        }
        let Some(data) = self.data.as_deref_mut() else {
            return String::new();
        };
        let dialogues = data.dialogues.stats();
        match self.section {
            Section::Textures => format!("{} textures", human_count(data.textures.items.len())),
            Section::Models => format!(
                "{} models \u{b7} {} categories",
                human_count(data.models.items.len()),
                data.models.categories().len()
            ),
            Section::Layouts => format!("{} files", human_count(data.layouts.items.len())),
            Section::Scripts => format!("{} packs", human_count(data.scripts.items.len())),
            Section::Tables => format!("{} tables", human_count(data.tables.items.len())),
            Section::Audio => format!("{} streams", human_count(data.audio.streams.len())),
            Section::Code => format!("{} functions", human_count(data.code.functions.len())),
            Section::Dialogues => format!("{} entries", human_count(dialogues.sources)),
            Section::Maps => format!("{} areas", human_count(data.areas.areas.len())),
            Section::Editor => format!("{} decoded maps", human_count(data.areas.areas.len())),
            _ => String::new(),
        }
    }

    fn global_search(&mut self, query: &str) {
        if query.trim().is_empty() {
            return;
        }
        self.open_search(query);
    }
}

impl eframe::App for ViewerApp {
    fn ui(&mut self, ui: &mut egui::Ui, _frame: &mut eframe::Frame) {
        let ctx = ui.ctx().clone();
        self.poll_boot();
        if !self.booted() && self.boot_error.is_none() {
            ctx.request_repaint_after(std::time::Duration::from_millis(100));
        }
        if self.thumbs.poll(&ctx) | self.preview.poll(&ctx) | self.layout_tex.poll(&ctx) {
            // new images arrived; a repaint is already queued
        }

        // shortcuts
        if ctx.input(|i| i.modifiers.command && i.key_pressed(egui::Key::F)) {
            self.focus_search = true;
        }
        if ctx.input(|i| i.key_pressed(egui::Key::F5)) {
            self.panels.refresh(self.section);
        }
        for (index, section) in SECTIONS.iter().enumerate() {
            let key = match index {
                0 => egui::Key::Num1,
                1 => egui::Key::Num2,
                2 => egui::Key::Num3,
                3 => egui::Key::Num4,
                4 => egui::Key::Num5,
                5 => egui::Key::Num6,
                6 => egui::Key::Num7,
                7 => egui::Key::Num8,
                8 => egui::Key::Num9,
                _ => continue,
            };
            if ctx.input(|i| i.modifiers.command && i.key_pressed(key)) {
                self.go(*section);
            }
        }

        egui::Panel::top("header")
            .frame(egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::symmetric(12, 8)))
            .show(ui, |ui| self.header(ui));
        egui::Panel::bottom("status")
            .frame(egui::Frame::new().fill(theme::BG_RAISED).inner_margin(egui::Margin::symmetric(12, 4)))
            .show(ui, |ui| self.status_bar(ui));
        egui::Panel::left("sidebar")
            .exact_size(212.0)
            .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::symmetric(10, 6)))
            .show(ui, |ui| self.sidebar(ui));

        egui::CentralPanel::default()
            .frame(egui::Frame::new().fill(theme::BG).inner_margin(egui::Margin::same(8)))
            .show(ui, |ui| {
                self.central(ui);
            });

        if let Some(renderer) = self.renderer.lock().ok().and_then(|r| r.error.clone()) {
            self.renderer_error = Some(renderer);
        }
        if self.thumbs.is_pending() {
            ctx.request_repaint_after(std::time::Duration::from_millis(120));
        }
    }
}

impl ViewerApp {
    fn central(&mut self, ui: &mut egui::Ui) {
        match self.section {
            Section::Overview => panels::overview::show(self, ui),
            Section::Search => panels::search::show(self, ui),
            Section::Textures => panels::textures::show(self, ui),
            Section::Models => panels::models::show(self, ui),
            Section::Layouts => panels::layouts::show(self, ui),
            Section::Scripts => panels::scripts::show(self, ui),
            Section::Tables => panels::tables::show(self, ui),
            Section::Audio => panels::audio::show(self, ui),
            Section::Code => panels::code::show(self, ui),
            Section::Dialogues => panels::dialogues::show(self, ui),
            Section::Maps => panels::maps::show(self, ui),
            Section::Editor => panels::editor::show(self, ui),
        }
    }
}

/// Helper used by panels that draw a GPU viewport.
pub fn paint_mesh_viewport(
    ui: &mut egui::Ui,
    renderer: Arc<Mutex<GlRenderer>>,
    camera: &crate::render::camera::Camera,
    opts: crate::render::gpu::RenderOptions,
    mesh: Option<(u64, Arc<crate::render::mesh::Mesh>)>,
) -> egui::Response {
    let size = ui.available_size();
    let (rect, response) = ui.allocate_exact_size(size, egui::Sense::click_and_drag());
    let camera = *camera;
    ui.painter().add(egui::PaintCallback {
        rect,
        callback: Arc::new(CallbackFn::new(move |info, _painter| {
            let vp = info.viewport_in_pixels();
            let Ok(mut r) = renderer.lock() else { return };
            // the mesh is offered every frame; the renderer uploads it once, on a
            // frame that is actually painted (UI passes and paints are not 1:1)
            if let Some((id, mesh)) = &mesh {
                if *id != r.uploaded_id {
                    match r.upload(*id, mesh) {
                        Ok(()) => r.error = None,
                        Err(e) => r.error = Some(e),
                    }
                }
            }
            r.paint([vp.left_px, vp.from_bottom_px, vp.width_px, vp.height_px], &camera, &opts);
        })),
    });
    response
}


