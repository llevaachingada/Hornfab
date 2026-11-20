# Favorites

`FAVORITES.yaml` is the owner's starred-horn list. Agents: **read it before proposing seeds, variants or
renders.** A favorite is a design the owner likes on sight (directivity plots, looks). That is not the same as
the lowest J, and it is often a sign the objective is missing something.

## Adding a favorite

1. Append an entry with the next `FAV-NNN` id. Required: `design_hash`, `config`, `brief`, `objective`,
   `runs.screen` (and `runs.verify` if one exists), `owner_note` (the owner's words), `status: active`.
   Read J values from `best.json`; never type them from memory.
2. Copy the knobs from the run's `best.json` `params.grid.knobs` (or the family's param block).
3. Link any research or queue that follows from it.
4. Never delete: set `status: retired` with a `retired_note`.
5. Same commit: add a CONTINUITY entry. If the commit is pushed, ISSUES too (repo push rule).

## Using favorites

- Seeds: start variant searches from a favorite's knobs (`seed_params`) under its **own** brief, or a
  documented copy of it.
- Ranking: J is comparable only within one brief/objective identity. A favorite's J is never ranked against
  another brief's J.
- Rendering: `hornlab-render` takes the `runs.screen` / `runs.verify` dirs.
