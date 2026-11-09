//! In-editor project tour: a small window that walks through the sections in order, switching
//! the editor to each one as it explains it. Started from the "Tour" button in the top bar, or
//! on launch with `DQXI_TOUR=1`. The long-form version is docs/PROJECT_TOUR.md.

use eframe::egui;

use crate::app::Section;
use crate::theme;

pub struct Step {
    pub section: Section,
    pub title: &'static str,
    pub body: &'static str,
}

pub const STEPS: &[Step] = &[
    Step {
        section: Section::Overview,
        title: "Welcome to DQXI Studio",
        body: "This editor opens every part of Dragon Quest XI (3DS): assets, tables, text, scripts \
               and the native code. Edits are staged in mod/ and never touch original/. This tour \
               takes about two minutes; each step switches the editor to the section it describes.",
    },
    Step {
        section: Section::Search,
        title: "Search everything",
        body: "One box finds textures, models, layouts, scripts, table rows, dialogue lines and \
               functions by name or address. Ctrl+F jumps here from anywhere.",
    },
    Step {
        section: Section::Tables,
        title: "Game data tables",
        body: "Items, monsters, spells and shops with typed fields. Names and descriptions are \
               editable, every change can be undone, and \"Add entry\" turns a placeholder row \
               into a new item. The item table cannot grow past 0xB3B rows (the code checks it).",
    },
    Step {
        section: Section::Dialogues,
        title: "Text and dialogue",
        body: "Edit the lines the game shows. The preview measures them with the game's own font \
               against the real text box and warns about missing glyphs and overflowing lines.",
    },
    Step {
        section: Section::Layouts,
        title: "Menus and HUD layouts",
        body: "BFLYT screens drawn the way the game draws them: textures, window frames and text in \
               the game font on the 400x240 / 320x240 screens. Move, resize, retext or add panes.",
    },
    Step {
        section: Section::Textures,
        title: "Textures, models and audio",
        body: "Browse and replace assets. Replacements are converted to the game's formats, \
               validated and staged in mod/romfs. Models and audio work the same way.",
    },
    Step {
        section: Section::Scripts,
        title: "Squirrel scripts",
        body: "Event and game-logic scripts, decompiled to readable source. Edit, compile and pack \
               them back; unchanged functions are kept byte for byte.",
    },
    Step {
        section: Section::Code,
        title: "Native code",
        body: "All 18,787 ARM functions as readable C with names and summaries. Names starting with \
               maybe_ are still guesses. The rebuilt code is checked to match the original exactly.",
    },
    Step {
        section: Section::Maps,
        title: "Maps and the level editor",
        body: "Open a field map in 3D, select objects, move them and save. The Editor section holds \
               the level-editor project for the open map.",
    },
    Step {
        section: Section::Playtest,
        title: "Export & Play",
        body: "Build your mod as a Luma LayeredFS folder, a rebuilt .3ds or an installable CIA, and \
               boot it in the bundled emulator. The Play button in the top bar does this in one \
               click. Exports are built to run on a real 3DS/2DS (CIA needs custom firmware).",
    },
];

#[derive(Default)]
pub struct Tour {
    /// Index into STEPS while the tour is open.
    pub step: Option<usize>,
}

impl Tour {
    pub fn start(&mut self) {
        self.step = Some(0);
    }

    /// Draws the tour window and moves the editor to the current step's section.
    pub fn show(&mut self, ctx: &egui::Context, section: &mut Section) {
        let Some(i) = self.step else { return };
        let step = &STEPS[i.min(STEPS.len() - 1)];
        *section = step.section;
        let mut open = true;
        let mut next = Some(i);
        egui::Window::new("Project tour")
            .open(&mut open)
            .collapsible(false)
            .resizable(false)
            .default_width(360.0)
            .anchor(egui::Align2::RIGHT_BOTTOM, egui::vec2(-16.0, -40.0))
            .show(ctx, |ui| {
                ui.label(theme::faint_label(&format!("Step {} of {}", i + 1, STEPS.len())));
                ui.label(theme::heading(step.title));
                ui.add_space(4.0);
                ui.label(step.body);
                ui.add_space(8.0);
                ui.horizontal(|ui| {
                    if ui.add_enabled(i > 0, egui::Button::new("Back")).clicked() {
                        next = Some(i - 1);
                    }
                    if i + 1 < STEPS.len() {
                        if ui.add(theme::filled_button("Next", theme::ACCENT)).clicked() {
                            next = Some(i + 1);
                        }
                    } else if ui.add(theme::filled_button("Finish", theme::ACCENT)).clicked() {
                        next = None;
                    }
                    if ui.button("Skip tour").clicked() {
                        next = None;
                    }
                });
            });
        self.step = if open { next } else { None };
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn every_section_with_content_is_in_the_tour_once() {
        let mut seen = std::collections::HashSet::new();
        for s in STEPS {
            assert!(seen.insert(s.section), "{:?} appears twice", s.section);
            assert!(!s.body.is_empty() && !s.title.is_empty());
        }
        assert_eq!(STEPS[0].section, Section::Overview);
        assert_eq!(STEPS.last().unwrap().section, Section::Playtest);
    }
}
