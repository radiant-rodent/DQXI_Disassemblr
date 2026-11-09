---
lane: editor
---
Brand-new materials for imported models (CL3).

Context: OBJ import and PNG texture replacement work on existing materials (docs/MODEL_IMPORT.md); a texture or material the model does not already have cannot be added yet. Extend tools/bch_writer.py / model_import.py to add a material + texture entry to a BCH and expose it in the Models Inspector.
Verify: emulator-proven on a cloned level slot, then cargo build/test. Report what you checked.
