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

// ---------------------------------------------------------------------------
// filled controls: readable text on light / saturated backgrounds
// ---------------------------------------------------------------------------

/// Ink for light fills. `#111` (not pure black) keeps the look softer while
/// still clearing WCAG AA on every fill in this palette (amber is ~10:1).
pub const ON_LIGHT: Color32 = Color32::from_rgb(0x11, 0x11, 0x11);
/// Ink for dark fills.
pub const ON_DARK: Color32 = Color32::WHITE;

/// WCAG 2.x relative luminance of an opaque colour (0.0 black .. 1.0 white).
pub fn relative_luminance(color: Color32) -> f32 {
    fn linear(channel: u8) -> f32 {
        let v = channel as f32 / 255.0;
        if v <= 0.039_28 {
            v / 12.92
        } else {
            ((v + 0.055) / 1.055).powf(2.4)
        }
    }
    0.2126 * linear(color.r()) + 0.7152 * linear(color.g()) + 0.0722 * linear(color.b())
}

/// WCAG contrast ratio between two opaque colours: 1.0 (identical) .. 21.0
/// (black on white). AA body text needs >= 4.5:1.
pub fn contrast_ratio(a: Color32, b: Color32) -> f32 {
    let (la, lb) = (relative_luminance(a), relative_luminance(b));
    let (hi, lo) = if la >= lb { (la, lb) } else { (lb, la) };
    (hi + 0.05) / (lo + 0.05)
}

/// Text colour for a filled surface: dark ink on light fills, white on dark
/// ones, whichever actually measures better contrast.
///
/// This exists because `egui::Button::fill` keeps the fill in *every* state
/// (inactive, hovered, pressed), so the default light label can land on amber
/// and drop to ~1.8:1. Deriving the ink from the fill keeps hover and pressed
/// readable too. The theme has no light mode (`apply` uses `Visuals::dark`),
/// but the rule only depends on the fill, so it would hold there as well.
pub fn text_on(fill: Color32) -> Color32 {
    if contrast_ratio(ON_LIGHT, fill) >= contrast_ratio(ON_DARK, fill) {
        ON_LIGHT
    } else {
        ON_DARK
    }
}

/// A filled (saturated) button whose label stays readable in every state.
///
/// Use this instead of `Button::new(..).fill(..)` for `ACCENT`, `WARN`, `OK`,
/// `INFO` and any other light fill. Hover/pressed feedback is the theme's
/// border stroke plus the pointing-hand cursor, because the fill itself is
/// pinned; the label colour is pinned too, so contrast cannot regress.
pub fn filled_button(text: impl Into<String>, fill: Color32) -> egui::Button<'static> {
    let label = egui::RichText::new(text.into())
        .color(text_on(fill))
        .strong();
    egui::Button::new(label).fill(fill)
}

pub fn accent_button(ui: &mut egui::Ui, label: &str) -> egui::Response {
    ui.add(filled_button(label, ACCENT))
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

#[cfg(test)]
mod contrast_tests {
    use super::*;

    /// Every colour in this module that is used as a filled background behind
    /// text (button fills, badges, chips, selected rows). `text_on` must give
    /// each of them an AA-readable label.
    const FILLS: &[(&str, Color32)] = &[
        ("ACCENT", ACCENT),
        ("ACCENT_DIM", ACCENT_DIM),
        ("INFO", INFO),
        ("WARN", WARN),
        ("ERR", ERR),
        ("OK", OK),
        ("JP_TEXT", JP_TEXT),
        ("BG_SELECT", BG_SELECT),
        ("BG_HOVER", BG_HOVER),
        ("BG_RAISED", BG_RAISED),
        ("BG_PANEL", BG_PANEL),
        ("BG_INPUT", BG_INPUT),
        ("BORDER_LIGHT", BORDER_LIGHT),
        ("COL_STRING", COL_STRING),
        ("COL_KEYWORD", COL_KEYWORD),
        ("COL_TYPE", COL_TYPE),
        ("COL_NUMBER", COL_NUMBER),
        ("COL_ADDR", COL_ADDR),
        ("TEXT_DIM", TEXT_DIM),
        ("TEXT_FAINT", TEXT_FAINT),
    ];

    #[test]
    fn every_fill_gets_aa_readable_text() {
        for (name, fill) in FILLS {
            let ink = text_on(*fill);
            let ratio = contrast_ratio(ink, *fill);
            assert!(
                ratio >= 4.5,
                "{name} ({fill:?}) picks ink {ink:?} at only {ratio:.2}:1 (WCAG AA needs 4.5:1)"
            );
        }
    }

    #[test]
    fn light_fills_use_dark_ink() {
        assert_eq!(text_on(ACCENT), ON_LIGHT);
        assert_eq!(text_on(WARN), ON_LIGHT);
        assert_eq!(text_on(OK), ON_LIGHT);
        assert_eq!(text_on(INFO), ON_LIGHT);
        assert_eq!(text_on(ERR), ON_LIGHT);
        assert_eq!(text_on(COL_STRING), ON_LIGHT);
    }

    #[test]
    fn dark_fills_use_white_ink() {
        assert_eq!(text_on(BG), ON_DARK);
        assert_eq!(text_on(BG_PANEL), ON_DARK);
        assert_eq!(text_on(BG_INPUT), ON_DARK);
        assert_eq!(text_on(BG_SELECT), ON_DARK);
        assert_eq!(text_on(ACCENT_DIM), ON_DARK);
    }

    /// Sanity-check the formula itself so a typo in the constants cannot make
    /// the AA assertions above pass trivially.
    #[test]
    fn luminance_and_ratio_match_known_values() {
        assert!(relative_luminance(Color32::BLACK).abs() < 1e-6);
        assert!((relative_luminance(Color32::WHITE) - 1.0).abs() < 1e-6);
        assert!((contrast_ratio(Color32::BLACK, Color32::WHITE) - 21.0).abs() < 0.01);
        assert!((contrast_ratio(ACCENT, ACCENT) - 1.0).abs() < 1e-6);
        // White on the amber Play button was the reported bug: ~1.8:1.
        assert!(contrast_ratio(Color32::WHITE, ACCENT) < 2.0);
    }

    /// The two normal-text pairs that are not fills still need AA.
    #[test]
    fn body_and_accent_text_read_against_the_panels() {
        assert!(contrast_ratio(TEXT, BG_PANEL) >= 4.5);
        assert!(contrast_ratio(TEXT_DIM, BG_PANEL) >= 4.5);
        assert!(contrast_ratio(ACCENT, BG_PANEL) >= 4.5);
        assert!(contrast_ratio(TEXT, BG_SELECT) >= 4.5);
        assert!(contrast_ratio(ACCENT, BG_SELECT) >= 4.5);
    }
}
