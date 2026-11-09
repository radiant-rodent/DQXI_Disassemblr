---
lane: editor
---
Fix unreadable buttons in DQXI Studio. User report: "a couple buttons are yellow with white text,
unreadable — for example the Play button."

Owns: `viewer_rs/src/theme.rs`, and the button-drawing code in `viewer_rs/src/ui/panels/*.rs`
(colour/style lines only; don't change behaviour).

1. Find every button/chip/badge drawn with a filled background (`theme::WARN` = #E8A33D amber,
   and any other light/saturated fill: ACCENT, OK, success greens, etc.) — e.g. the Play button
   in `ui/panels/playtest.rs`, plus anything in audio.rs and mod.rs. List them in your report.
2. Add one helper in theme.rs, e.g. `theme::filled_button(text, fill) -> egui::Button`, that picks
   the text colour from the fill's luminance (dark text #111 on light fills, white on dark fills)
   so contrast is >= 4.5:1 (WCAG AA). Compute and assert the ratio in a unit test for every theme
   fill colour, in both light and dark mode if the theme has both.
3. Use the helper for all filled buttons; hover/pressed states must stay readable too.
4. `cargo build --release` + `cargo test` green. Start the editor, take a screenshot of the
   playtest panel and one other fixed panel, and look at them before reporting.
