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

### resources

- The 3D bed of the Custom printers (MyKlipper, MyMarlin, MyRRF, MyToolChanger) shows the CosmoSlice logo
  instead of Orca's. MR: pending. D-012.
- The home page and setup guide logo, the macOS app icon and the macOS document icons (.3mf/.obj/.amf, .stl,
  .gcode) now show the CosmoSlice logo instead of Orca's; the .3mf/.obj/.amf icon was a broken file before. They are
  rendered from `resources/images/OrcaSlicer.svg` by `just -f scripts/brand_assets/justfile derive`, and `just ci`
  fails when one drifts. The .stl and .gcode icons are the app icon until dedicated document icons are provided.
  MR: pending. D-010, D-011, D-012.

### tooling

- `just lint` now checks the Python modules below `scripts/` (only the legacy upstream scripts are skipped).
  MR: pending. D-007.
- `just i18n-rename`: renames msgids in place in the pot and every .po from a frozen mapping, marking changed
  translations fuzzy with the previous msgid, without re-wrapping the catalogues. MR: pending. D-004.
- Repository-wide `just` task runner with a pinned Docker CI image for Python tests, lint and i18n checks, and LF
  line endings enforced for every text file. MR: pending. D-007, D-008.
