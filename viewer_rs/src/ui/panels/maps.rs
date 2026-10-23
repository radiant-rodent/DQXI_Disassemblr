//! Map / area dossiers: everything about one game area on a single screen.

use eframe::egui;

use crate::app::ViewerApp;
use crate::data::areas::AreaDossier;
use crate::theme;
use crate::utils::{human_count, human_size};

#[derive(Clone, Copy, PartialEq, Eq)]
enum Tab {
    Textures,
    Models,
    Scripts,
    Dialogues,
    Levels,
    Audio,
    Layouts,
}

pub struct MapsPanel {
    pub query: String,
    list: Vec<String>,
    selected: Option<usize>,
    dossier: Option<AreaDossier>,
    tab: Tab,
    sort_by_assets: bool,
    sort_desc: bool,
    dirty: bool,
    request: Option<String>,
}

impl Default for MapsPanel {
    fn default() -> Self {
        Self {
            query: String::new(),
            list: Vec::new(),
            selected: None,
            dossier: None,
            tab: Tab::Textures,
            sort_by_assets: false,
            sort_desc: false,
            dirty: true,
            request: None,
        }
    }
}

impl MapsPanel {
    pub fn request(&mut self, area: &str) {
        self.request = Some(area.to_string());
        self.dirty = true;
    }

    pub fn reset(&mut self) {
        self.query.clear();
        self.dirty = true;
    }
}

pub fn show(app: &mut ViewerApp, ui: &mut egui::Ui) {
    if !app.data().is_some_and(|d| d.areas.ready) {
        ui.label(theme::dim_label("building map dossiers\u{2026}"));
        return;
    }
    if let Some(area) = app.panels.maps.request.take() {
        app.panels.maps.query = area;
        app.panels.maps.dirty = true;
    }
    if app.panels.maps.dirty {
        let query = app.panels.maps.query.to_lowercase();
        if let Some(data) = app.data.as_deref() {
            app.panels.maps.list = data
                .areas
                .areas
                .iter()
                .filter(|a| {
                    query.is_empty()
                        || a.to_lowercase().contains(&query)
                        || data
                            .areas
                            .display_name(a)
                            .is_some_and(|n| n.to_lowercase().contains(&query))
                })
                .cloned()
                .collect();
            let by_assets = app.panels.maps.sort_by_assets;
            let desc = app.panels.maps.sort_desc;
            if by_assets {
                app.panels.maps.list.sort_by_key(|a| data.areas.dossier(a).asset_count());
            } else {
                app.panels.maps.list.sort_by_key(|a| a.to_lowercase());
            }
            if desc {
                app.panels.maps.list.reverse();
            }
        }
        app.panels.maps.dirty = false;
        if app.panels.maps.selected.is_none() {
            if let Some(first) = app.panels.maps.list.first().cloned() {
                select(app, &first);
            }
        } else if let Some(area) = app
            .panels
            .maps
            .selected
            .and_then(|i| app.panels.maps.list.get(i).cloned())
        {
            select(app, &area);
        }
    }

    egui::Panel::left("area_list")
        .exact_size(280.0)
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            ui.label(theme::heading("Game areas"));
            if ui
                .add(
                    egui::TextEdit::singleline(&mut app.panels.maps.query)
                        .hint_text("Search areas\u{2026}")
                        .desired_width(f32::INFINITY),
                )
                .changed()
            {
                app.panels.maps.dirty = true;
            }
            ui.label(theme::faint_label(format!(
                "{} areas",
                human_count(app.panels.maps.list.len())
            )));
            ui.separator();
            let list = app.panels.maps.list.clone();
            let selected = app
                .panels
                .maps
                .selected
                .and_then(|i| app.panels.maps.list.get(i).cloned());
            let mut clicked = None;
            use egui_extras::{Column, TableBuilder};
            TableBuilder::new(ui)
                .id_salt("area_scroll")
                .striped(true)
                .sense(egui::Sense::click())
                .cell_layout(egui::Layout::left_to_right(egui::Align::Center))
                .auto_shrink([false, false])
                .column(Column::remainder().at_least(80.0))
                .column(Column::exact(80.0))
                .header(20.0, |mut header| {
                    header.col(|ui| {
                        let label = if !app.panels.maps.sort_by_assets {
                            if app.panels.maps.sort_desc { "Area \u{25bc}" } else { "Area \u{25b2}" }
                        } else { "Area" };
                        if ui.add(egui::Button::new(theme::faint_label(label)).frame(false)).clicked() {
                            app.panels.maps.sort_by_assets = false;
                            app.panels.maps.sort_desc = !app.panels.maps.sort_desc;
                            app.panels.maps.dirty = true;
                        }
                    });
                    header.col(|ui| {
                        let label = if app.panels.maps.sort_by_assets {
                            if app.panels.maps.sort_desc { "Assets \u{25bc}" } else { "Assets \u{25b2}" }
                        } else { "Assets" };
                        if ui.add(egui::Button::new(theme::faint_label(label)).frame(false)).clicked() {
                            app.panels.maps.sort_by_assets = true;
                            app.panels.maps.sort_desc = !app.panels.maps.sort_desc;
                            app.panels.maps.dirty = true;
                        }
                    });
                })
                .body(|body| {
                    body.rows(17.0, list.len(), |mut row| {
                        let area = &list[row.index()];
                        let assets = app
                            .data
                            .as_deref()
                            .map(|d| d.areas.dossier(area).asset_count())
                            .unwrap_or(0);
                        row.set_selected(selected.as_deref() == Some(area.as_str()));
                        let name = app.data.as_deref().and_then(|d| d.areas.display_name(area)).map(str::to_owned);
                        row.col(|ui| {
                            let label = match &name {
                                Some(name) => format!("{area}  {name}"),
                                None => area.clone(),
                            };
                            ui.label(egui::RichText::new(label).size(12.0));
                        });
                        row.col(|ui| {
                            ui.label(theme::faint_label(assets.to_string()));
                        });
                        if row.response().clicked() {
                            clicked = Some(area.clone());
                        }
                    });
                });
            if let Some(area) = clicked {
                select(app, &area);
            }
        });

    egui::CentralPanel::default()
        .frame(egui::Frame::new().fill(theme::BG_PANEL).inner_margin(egui::Margin::same(8)))
        .show(ui, |ui| {
            let Some(dossier) = app.panels.maps.dossier.clone() else {
                ui.label(theme::faint_label("Select an area."));
                return;
            };
            ui.horizontal(|ui| {
                let name = app.data.as_deref().and_then(|d| d.areas.display_name(&dossier.area)).map(str::to_owned);
                ui.label(theme::heading(match name {
                    Some(name) => format!("{name}  ({})", dossier.area),
                    None => dossier.area.clone(),
                }));
                ui.label(theme::dim_label(format!(
                    "{} texture packs  \u{b7}  {} 3D models  \u{b7}  {} script packs  \u{b7}  {} audio  \u{b7}  {} text entries  \u{b7}  {} level packs",
                    dossier.textures.len(),
                    dossier.models.len(),
                    dossier.scripts.len(),
                    dossier.audio.len(),
                    human_count(dossier.dialogue_total),
                    dossier.level2d.len() + dossier.level3d.len()
                )));
            });
            ui.horizontal(|ui| {
                if ui.button("Show in Textures").clicked() {
                    app.open_textures("", dossier.textures.first().map(|s| s.as_str()));
                }
                if ui.button("Show in Models").clicked() {
                    let name = dossier
                        .models
                        .first()
                        .cloned()
                        .unwrap_or_else(|| dossier.area.clone());
                    app.open_model(&name);
                }
                if ui.button("Show in Scripts").clicked() {
                    app.open_scripts(&dossier.area);
                }
                if ui.button("Show in Dialogues").clicked() {
                    app.open_dialogues("", Some(&dossier.area));
                }
                if ui.button("Show in Audio").clicked() {
                    app.open_audio(&dossier.area);
                }
                if ui.button("Show in Layouts").clicked() {
                    app.open_layout(&dossier.area);
                }
            });
            ui.separator();
            ui.horizontal(|ui| {
                for (label, tab) in [
                    ("Textures", Tab::Textures),
                    ("3D models", Tab::Models),
                    ("Scripts", Tab::Scripts),
                    ("Dialogues", Tab::Dialogues),
                    ("Level packs", Tab::Levels),
                    ("Audio", Tab::Audio),
                    ("UI packs", Tab::Layouts),
                ] {
                    if ui.selectable_label(app.panels.maps.tab == tab, label).clicked() {
                        app.panels.maps.tab = tab;
                    }
                }
            });
            ui.separator();
            match app.panels.maps.tab {
                Tab::Textures => texture_tab(app, ui, &dossier),
                Tab::Models => {
                    if dossier.models.is_empty() {
                        ui.label(theme::faint_label("No extracted 3D model is named after this area."));
                    }
                    for name in &dossier.models {
                        let size = app
                            .data
                            .as_deref()
                            .and_then(|d| d.models.get(name))
                            .map(|m| human_size(m.size))
                            .unwrap_or_default();
                        if ui
                            .selectable_label(false, format!("{name:<34} {size}"))
                            .double_clicked()
                        {
                            app.open_model(name);
                        }
                    }
                    ui.label(theme::faint_label("double-click a model to open it in the 3D viewer"));
                }
                Tab::Scripts => {
                    for name in &dossier.scripts {
                        if ui.selectable_label(false, name.clone()).double_clicked() {
                            app.open_scripts(name);
                        }
                    }
                }
                Tab::Dialogues => {
                    ui.label(theme::faint_label(format!(
                        "{} text entries reference this area",
                        human_count(dossier.dialogue_total)
                    )));
                    for (file, count) in dossier.dialogue_files.iter().take(40) {
                        if ui
                            .selectable_label(false, format!("{file:<44} {count:>6}"))
                            .double_clicked()
                        {
                            app.open_dialogues("", Some(file));
                        }
                    }
                }
                Tab::Levels => {
                    if dossier.level3d.is_empty() && dossier.level2d.is_empty() {
                        ui.label(theme::faint_label(
                            "No level geometry pack found for this area in the reference workspace.",
                        ));
                    }
                    for (name, size) in &dossier.level3d {
                        ui.label(theme::mono(format!("{name:<36} {:>10}  level3d", human_size(*size))));
                    }
                    for (name, size) in &dossier.level2d {
                        ui.label(theme::mono(format!("{name:<36} {:>10}  level2d", human_size(*size))));
                    }
                }
                Tab::Audio => {
                    for name in &dossier.audio {
                        if ui.selectable_label(false, name.clone()).double_clicked() {
                            app.open_audio(name);
                        }
                    }
                }
                Tab::Layouts => {
                    for name in &dossier.layouts {
                        if ui.selectable_label(false, name.clone()).double_clicked() {
                            app.open_layout(name);
                        }
                    }
                }
            }
        });
}

fn select(app: &mut ViewerApp, area: &str) {
    if let Some(index) = app.panels.maps.list.iter().position(|a| a == area) {
        app.panels.maps.selected = Some(index);
    }
    if let Some(data) = app.data.as_mut() {
        let mut dossier = data.areas.dossier(area);
        data.areas.refresh_dialogues(&mut data.dialogues, &mut dossier);
        app.panels.maps.dossier = Some(dossier);
    }
}

fn texture_tab(app: &mut ViewerApp, ui: &mut egui::Ui, dossier: &AreaDossier) {
    let mut items: Vec<usize> = Vec::new();
    if let Some(data) = app.data.as_deref() {
        for pack in &dossier.textures {
            let found = data.textures.search("", Some(pack), None);
            items.extend(found);
            if items.len() >= 300 {
                break;
            }
        }
    }
    ui.label(theme::faint_label(format!(
        "{} texture items from packs: {}",
        human_count(items.len()),
        dossier.textures.join(", ")
    )));
    let cell = egui::vec2(118.0, 118.0);
    let spacing = 8.0;
    let columns = ((ui.available_width() + spacing) / (cell.x + spacing)).floor().max(1.0) as usize;
    let rows = items.len().div_ceil(columns);
    let mut clicked = None;
    egui::ScrollArea::vertical()
        .id_salt("area_textures")
        .auto_shrink([false, false])
        .show_rows(ui, cell.y + spacing + 16.0, rows, |ui, range| {
            for row in range {
                ui.horizontal(|ui| {
                    for column in 0..columns {
                        let i = row * columns + column;
                        if i >= items.len() {
                            break;
                        }
                        let index = items[i];
                        let (rect, response) = ui.allocate_exact_size(cell, egui::Sense::click());
                        let painter = ui.painter_at(rect);
                        painter.rect_filled(rect, 2.0, theme::BG_INPUT);
                        let path = app
                            .data
                            .as_deref()
                            .and_then(|d| d.textures.items.get(index))
                            .map(|t| t.path.clone());
                        let name = app
                            .data
                            .as_deref()
                            .and_then(|d| d.textures.items.get(index))
                            .map(|t| t.name.clone())
                            .unwrap_or_default();
                        if let Some(path) = &path {
                            if let Some(handle) = app.thumbs.get(ui.ctx(), &app.pool, path) {
                                let tex_size = handle.size_vec2();
                                let scale = (rect.width() / tex_size.x.max(1.0))
                                    .min(rect.height() / tex_size.y.max(1.0));
                                painter.image(
                                    handle.id(),
                                    egui::Rect::from_center_size(rect.center(), tex_size * scale),
                                    egui::Rect::from_min_max(egui::pos2(0.0, 0.0), egui::pos2(1.0, 1.0)),
                                    egui::Color32::WHITE,
                                );
                            }
                        }
                        painter.text(
                            rect.left_bottom() + egui::vec2(2.0, 2.0),
                            egui::Align2::LEFT_TOP,
                            crate::utils::elide(&name, 20),
                            egui::FontId::proportional(10.5),
                            theme::TEXT_DIM,
                        );
                        if response.clicked() {
                            clicked = Some(index);
                        }
                    }
                });
            }
        });
    if let Some(index) = clicked {
        let pack = app
            .data
            .as_deref()
            .and_then(|d| d.textures.items.get(index))
            .map(|t| t.pack.clone())
            .unwrap_or_default();
        app.open_textures("", Some(&pack));
    }
}
