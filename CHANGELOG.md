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

### tooling

- `just i18n-rename`: renames msgids in place in the pot and every .po from a frozen mapping, marking changed
  translations fuzzy with the previous msgid, without re-wrapping the catalogues. MR: pending. D-004.
- Repository-wide `just` task runner with a pinned Docker CI image for Python tests, lint and i18n checks, and LF
  line endings enforced for every text file. MR: pending. D-007, D-008.
