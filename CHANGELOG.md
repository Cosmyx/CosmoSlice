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

- The About dialog, the splash screen and the network test dialog show the CosmoSlice version, `2.3.1-5`, built
  from the OrcaSlicer base version and the Cosmyx patch number, instead of `2.3.1` plus a separate "Cosmyx Bundle
  Version" line. The "new build" notice compares and shows this full version: users of a `CSDEV-V1.2` build see
  "CSDEV-V1.2 → 2.3.1-5" in it, and it keeps appearing at each launch until they reset their AppData folder or
  turn it off, as it already did for a new build hash.
  MR: pending. D-014. COSMYX_PATCH_VERSION 5.
- Dialogs, messages, tooltips, preferences and hints say CosmoSlice instead of OrcaSlicer; the About dialog credits
  OrcaSlicer, and names that refer to upstream or are stored in files are kept. MR: pending. D-001, D-002, D-003,
  D-005, D-006.

### i18n

- The 76 renamed msgids are renamed in the pot and every .po; existing translations are kept but marked fuzzy with the
  previous msgid until each language is updated (`just i18n-status <lang>`). Until then these 76 strings show in
  English in translated UIs (fuzzy entries are left out of the .mo). MR: pending. D-004.

### web

- The first-run setup guide says CosmoSlice (English text and page fallbacks); the 14 other guide languages are
  listed in `scripts/i18n/pending/` until translated. MR: pending. D-002, D-006.

### resources

- **Removal:** the two "0.20mm Cosmyx Support W" process presets (Nova and Metal and Ceramics) are deleted: they
  were never listed in the Cosmyx index, so they never showed in the slicer, and nothing changes for users.
  MR: pending. D-013.
- **Breaking:** `resources/profiles/cosmyx.json` is no longer in git: it is generated for every build from the
  profile tree, with the build commit's UTC date as its version (`YYYYMMDD.HHMMSS.00.00`), so each new build
  reinstalls the bundled Cosmyx profiles over the copy in the user's folder. A local C++ build must run
  `just profiles-index` first; CMake stops otherwise. New presets no longer need a hand-written index entry.
  MR: pending. D-013.
- The Cosmyx Nova can-out printer loads on Linux: its profile index named the `nova_can_out` folder with the wrong
  case, which only case-insensitive file systems (macOS, Windows) accepted. MR: pending.
- The 3D bed of the Cosmyx Nova printers shows its logo in white, blue and red instead of black. MR: pending.
  D-012.
- The 3D bed of the Custom printers (MyKlipper, MyMarlin, MyRRF, MyToolChanger) shows the CosmoSlice logo
  instead of Orca's. MR: pending. D-012.
- The home page and setup guide logo, the macOS app icon and the macOS document icons (.3mf/.obj/.amf, .stl,
  .gcode) now show the CosmoSlice logo instead of Orca's; the .3mf/.obj/.amf icon was a broken file before. They are
  rendered from `resources/images/OrcaSlicer.svg` by `just -f scripts/brand_assets/justfile derive`, and `just ci`
  fails when one drifts. The .stl and .gcode icons are the app icon until dedicated document icons are provided.
  MR: pending. D-010, D-011, D-012.

### tooling

- CI build artifacts are named `CosmoSlice_<OS>_<version>_<short commit hash>` (for example
  `CosmoSlice_Windows_2.3.1-5_aa9dac8`); `just version` prints the version. MR: pending. D-014.
- The macOS build no longer stops at its disk-space step on the macos-15 runners, where the disk device it
  named does not exist; it now reports the volume of `/Applications`. MR: pending.
- `just profiles-index` generates the Cosmyx vendor index from the profile tree and the current commit; CI
  generates it before every build and checks the copy inside each package. MR: pending. D-013.
- `just i18n-check` validates every catalogue (`just i18n-catalogs` alone) and guards against the upstream product
  name in user-visible text; `just i18n-status` lists what each language still has to translate. MR: pending. D-006.
- `just lint` now checks the Python modules below `scripts/` (only the legacy upstream scripts are skipped).
  MR: pending. D-007.
- `just i18n-rename`: renames msgids in place in the pot and every .po from a frozen mapping, marking changed
  translations fuzzy with the previous msgid (and context), without re-wrapping the catalogues; when one catalogue
  cannot be renamed, none is written. MR: pending. D-004.
- Repository-wide `just` task runner with a pinned Docker CI image for Python tests, lint and i18n checks, and LF
  line endings enforced for every tracked text file. MR: pending. D-007, D-008.
