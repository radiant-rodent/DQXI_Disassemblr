//! One module per navigable section.

pub mod audio;
pub mod code;
pub mod dialogues;
pub mod editor;
pub mod layouts;
pub mod maps;
pub mod models;
pub mod overview;
pub mod scripts;
pub mod search;
pub mod tables;
pub mod textures;

use crate::app::Section;

#[derive(Default)]
pub struct Panels {
    pub overview: overview::OverviewPanel,
    pub search: search::SearchPanel,
    pub textures: textures::TexturesPanel,
    pub models: models::ModelsPanel,
    pub layouts: layouts::LayoutsPanel,
    pub scripts: scripts::ScriptsPanel,
    pub tables: tables::TablesPanel,
    pub audio: audio::AudioPanel,
    pub code: code::CodePanel,
    pub dialogues: dialogues::DialoguesPanel,
    pub maps: maps::MapsPanel,
    pub editor: editor::EditorPanel,
}

impl Panels {
    pub fn new() -> Self {
        Self {
            scripts: scripts::ScriptsPanel::new(),
            ..Default::default()
        }
    }
}

impl Panels {
    /// F5: drop filters/caches for the visible section.
    pub fn refresh(&mut self, section: Section) {
        match section {
            Section::Search => self.search.reset(),
            Section::Textures => self.textures.reset(),
            Section::Models => self.models.reset(),
            Section::Layouts => self.layouts.reset(),
            Section::Scripts => self.scripts.reset(),
            Section::Tables => self.tables.reset(),
            Section::Audio => self.audio.reset(),
            Section::Code => self.code.reset(),
            Section::Dialogues => self.dialogues.reset(),
            Section::Maps => self.maps.reset(),
            Section::Editor => self.editor.reset(),
            Section::Overview => {}
        }
    }
}
