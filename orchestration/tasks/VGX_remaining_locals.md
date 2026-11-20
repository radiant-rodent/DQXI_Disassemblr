---
lane: V_gap
---
DEFERRED (held by claim): about 8% of the local variables are still unnamed after the VG_* gap-fill pass
(stack buffers, scratch temporaries, `unaff_*` registers that workers could not justify naming).
Plan: after the merge, run `python tools/gapfill.py --build` again; it lists only what is still unnamed. If that is
under ~4,000 variables, either accept them as is or run the new batches with a stronger model. Do not start it
before the VG_*, R5_* and SF_* results are merged. Remove `claims/VGX_remaining_locals` to release.
