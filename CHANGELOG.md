# Changelog

Every change to CosmoSlice is recorded here, in English, in the branch that makes it.

## Rules

- **Newest first.** Periods are months, `## YYYY-MM`; the current period is at the top. Open a new period when the
  month changes.
- **Areas.** Inside a period, lines are grouped under the area they touch, one of `### gui`, `### i18n`, `### web`,
  `### resources`, `### tooling` (add a new area only for a new module or tool).
- **One line per change**, newest at the top of its area: what changed for someone reading the history (not how),
  then the merge request link, the decision it implements (`D-NNN`, see `wiki/decision-register.md`) if any, and the
  new `COSMYX_PATCH_VERSION` (from `version.inc`) when the change bumps it.
- **Breaking changes, removals and migrations** start with **Breaking:** in bold and say what the reader has to do.
- A change whose merge request does not exist yet carries `MR: pending`; the link replaces it when the request opens.

## 2026-10

### gui

- Dialogs, messages, tooltips, preferences and hints say CosmoSlice instead of OrcaSlicer; the About dialog credits
  OrcaSlicer, and names that refer to upstream or are stored in files are kept. MR: pending. D-001, D-002, D-003,
  D-005, D-006.

### i18n

- The 76 renamed msgids are renamed in the pot and every .po; existing translations are kept but marked fuzzy with the
  previous msgid until each language is updated (`just i18n-status <lang>`). MR: pending. D-004.

### web

- The first-run setup guide says CosmoSlice (English text and page fallbacks); the 14 other guide languages are
  listed in `scripts/i18n/pending/` until translated. MR: pending. D-002, D-006.

### tooling

- `just i18n-check` validates every catalogue and guards against the upstream product name in user-visible text;
  `just i18n-status` lists what each language still has to translate. MR: pending. D-006.
- `just lint` now checks the Python modules below `scripts/` (only the legacy upstream scripts are skipped).
  MR: pending. D-007.
- `just i18n-rename`: renames msgids in place in the pot and every .po from a frozen mapping, marking changed
  translations fuzzy with the previous msgid, without re-wrapping the catalogues. MR: pending. D-004.
- Repository-wide `just` task runner with a pinned Docker CI image for Python tests, lint and i18n checks, and LF
  line endings enforced for every text file. MR: pending. D-007, D-008.
