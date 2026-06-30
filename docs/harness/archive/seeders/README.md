# Archived DB seeders

One-off DB seed generators + their generated SQL, moved out of `scripts/` because they had zero
callers (not wired into any workflow, hook, justfile recipe, or other script) and totaled ~4,930
LOC of Python + ~15 MB of checked-in SQL (incl. `seed_slot3_master_copy.sql` at 11.6 MB).

These were authored during early slot bring-up (slot 2/3/4 seeding, OPD/vital-signs/bedroom/
consultation/inpatient seed data, BV-test3 H7 seed). They are historical — keep here for reference
or re-running a one-off seed; do not restore them to `scripts/` (if a new seed workflow is needed,
author a new idempotent generator under `scripts/` with a justfile recipe).

`db_merge.py` is NOT here — it remains in `scripts/` (live, called by `worktree.py` sync-db --merge).
