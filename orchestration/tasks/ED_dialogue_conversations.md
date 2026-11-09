---
lane: editor
---
Add and remove NPC conversations in the Level Editor's Dialogue group.

Context: the Dialogue group (viewer_rs/src/ui/panels/editor.rs `dialogue_section`, docs/DIALOGUE_FORMAT.md) edits the existing lines of a region character's conversations (`param/region/rNNN/npc_ie`). Adding a new conversation (story-flag group, minimum, time mask, variants, lines) or deleting one needs the BXON writer to grow the talk/variant/line arrays (see tools/bxon_grow.py and tools/text_tool.py `rebuild_bank`, which only replaces strings today).

Also: name the story-flag groups (the byte-0 group of a talk; find what each group reads in `func_0066B17C`), and prove in the emulator that pressing A on a street NPC (b002_001a) plays the conversation the editor shows (the edit path itself is proven with a test event, docs/DIALOGUE_FORMAT.md).

Owns: tools/npc_talk.py, tools/text_tool.py (new writer), viewer_rs/src/ui/panels/editor.rs (Dialogue group).
Verify: cargo build/test, run the editor, emulator probe as in docs/TESTING_EMULATOR.md. Report what you checked.
