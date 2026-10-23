//! Dark palette + egui styling, matching the Tk viewer's look.

use std::sync::Arc;

use eframe::egui::{self, Color32, FontData, FontDefinitions, FontFamily, FontId, TextStyle};

pub const BG: Color32 = Color32::from_rgb(0x11, 0x13, 0x18);
pub const BG_PANEL: Color32 = Color32::from_rgb(0x17, 0x1a, 0x21);
pub const BG_RAISED: Color32 = Color32::from_rgb(0x1e, 0x22, 0x2b);
pub const BG_INPUT: Color32 = Color32::from_rgb(0x0d, 0x0f, 0x14);
pub const BG_HOVER: Color32 = Color32::from_rgb(0x24, 0x2a, 0x35);
pub const BG_SELECT: Color32 = Color32::from_rgb(0x2e, 0x36, 0x48);
pub const BORDER: Color32 = Color32::from_rgb(0x2a, 0x2f, 0x3a);
pub const TEXT: Color32 = Color32::from_rgb(0xe6, 0xe8, 0xee);
pub const TEXT_DIM: Color32 = Color32::from_rgb(0x9a, 0xa2, 0xb1);
pub const TEXT_FAINT: Color32 = Color32::from_rgb(0x6b, 0x73, 0x83);
pub const ACCENT: Color32 = Color32::from_rgb(0xe8, 0xb8, 0x4b);
pub const ACCENT_DIM: Color32 = Color32::from_rgb(0x8a, 0x6d, 0x2b);
pub const INFO: Color32 = Color32::from_rgb(0x6d, 0xb3, 0xf2);
pub const WARN: Color32 = Color32::from_rgb(0xe8, 0xa3, 0x3d);
pub const ERR: Color32 = Color32::from_rgb(0xe8, 0x6a, 0x5b);
pub const OK: Color32 = Color32::from_rgb(0x5e, 0xc9, 0x8a);
pub const JP_TEXT: Color32 = Color32::from_rgb(0x9f, 0xc7, 0xff);
pub const BORDER_LIGHT: Color32 = Color32::from_rgb(0x3a, 0x41, 0x50);
pub const COL_COMMENT: Color32 = Color32::from_rgb(0x6f, 0x7f, 0x95);
pub const COL_KEYWORD: Color32 = Color32::from_rgb(0xc7, 0x92, 0xea);
pub const COL_TYPE: Color32 = Color32::from_rgb(0x82, 0xaa, 0xff);
pub const COL_STRING: Color32 = Color32::from_rgb(0xc3, 0xe8, 0x8d);
pub const COL_NUMBER: Color32 = Color32::from_rgb(0xf7, 0x8c, 0x6c);
pub const COL_ADDR: Color32 = Color32::from_rgb(0xe8, 0xb8, 0x4b);
pub const COL_PUNCT: Color32 = Color32::from_rgb(0x88, 0x92, 0xa6);
pub const MONO: Color32 = Color32::from_rgb(0xc9, 0xd3, 0xe0);

pub fn accent_button(ui: &mut egui::Ui, label: &str) -> egui::Response {
    let button = egui::Button::new(egui::RichText::new(label).color(Color32::from_rgb(0x16, 0x18, 0x1d)))
        .fill(ACCENT);
    ui.add(button)
}

pub fn dim_label(text: impl Into<String>) -> egui::RichText {
    egui::RichText::new(text.into()).color(TEXT_DIM).size(12.0)
}

pub fn faint_label(text: impl Into<String>) -> egui::RichText {
    egui::RichText::new(text.into()).color(TEXT_FAINT).size(11.0)
}

pub fn mono(text: impl Into<String>) -> egui::RichText {
    egui::RichText::new(text.into())
        .monospace()
        .color(MONO)
        .size(12.0)
}

pub fn heading(text: impl Into<String>) -> egui::RichText {
    egui::RichText::new(text.into()).color(TEXT).size(17.0).strong()
}

pub fn accent(text: impl Into<String>) -> egui::RichText {
    egui::RichText::new(text.into()).color(ACCENT).strong()
}

pub fn apply(ctx: &egui::Context) {
    install_fonts(ctx);
    let mut visuals = egui::Visuals::dark();
    visuals.panel_fill = BG;
    visuals.window_fill = BG_PANEL;
    visuals.extreme_bg_color = BG_INPUT;
    visuals.faint_bg_color = BG_RAISED;
    visuals.window_stroke = egui::Stroke::new(1.0, BORDER);
    visuals.widgets.noninteractive.bg_fill = BG_PANEL;
    visuals.widgets.noninteractive.fg_stroke = egui::Stroke::new(1.0, TEXT_DIM);
    visuals.widgets.inactive.bg_fill = BG_RAISED;
    visuals.widgets.inactive.weak_bg_fill = BG_RAISED;
    visuals.widgets.inactive.fg_stroke = egui::Stroke::new(1.0, TEXT);
    visuals.widgets.hovered.bg_fill = BG_HOVER;
    visuals.widgets.hovered.weak_bg_fill = BG_HOVER;
    visuals.widgets.active.bg_fill = BG_SELECT;
    visuals.widgets.active.weak_bg_fill = BG_SELECT;
    visuals.selection.bg_fill = BG_SELECT;
    visuals.selection.stroke = egui::Stroke::new(1.0, ACCENT);
    visuals.hyperlink_color = ACCENT;
    visuals.window_shadow = egui::epaint::Shadow::NONE;
    ctx.set_visuals(visuals);

    let mut style = (*ctx.style_of(ctx.theme())).clone();
    style.spacing.item_spacing = egui::vec2(6.0, 5.0);
    style.spacing.button_padding = egui::vec2(8.0, 4.0);
    style.spacing.scroll.bar_width = 10.0;
    // Lists are click targets, not text-selection surfaces. Code/dialogue views
    // opt back into selection in `ui::text_view`.
    style.interaction.selectable_labels = false;
    style.text_styles = [
        (TextStyle::Heading, FontId::new(17.0, FontFamily::Proportional)),
        (TextStyle::Body, FontId::new(13.0, FontFamily::Proportional)),
        (TextStyle::Button, FontId::new(13.0, FontFamily::Proportional)),
        (TextStyle::Small, FontId::new(11.0, FontFamily::Proportional)),
        (TextStyle::Monospace, FontId::new(12.5, FontFamily::Monospace)),
    ]
    .into();
    ctx.set_style_of(ctx.theme(), style);
}

/// Add a Japanese-capable system font as a fallback so dialogue text renders.
fn install_fonts(ctx: &egui::Context) {
    let candidates = [
        ("meiryo", r"C:\Windows\Fonts\meiryo.ttc"),
        ("yugothic", r"C:\Windows\Fonts\YuGothM.ttc"),
        ("msgothic", r"C:\Windows\Fonts\msgothic.ttc"),
        ("msmincho", r"C:\Windows\Fonts\msmincho.ttc"),
        ("noto", r"C:\Windows\Fonts\NotoSansJP-VF.ttf"),
    ];
    let mut fonts = FontDefinitions::default();
    let mut installed = Vec::new();
    for (name, path) in candidates {
        let Ok(bytes) = std::fs::read(path) else { continue };
        fonts
            .font_data
            .insert(name.to_string(), Arc::new(FontData::from_owned(bytes)));
        installed.push(name.to_string());
        break;
    }
    for name in installed {
        for family in [FontFamily::Proportional, FontFamily::Monospace] {
            fonts.families.entry(family).or_default().push(name.clone());
        }
    }
    ctx.set_fonts(fonts);
}
