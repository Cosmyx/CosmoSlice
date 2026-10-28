# Decision register

Every decision taken while working on CosmoSlice is recorded here with its number, so later changes can find why the
code is the way it is. Numbers are never reused. An entry gives the context, the decision, the reason, and what
reverting it would take. Problems found but not fixed go to [Open issues](#open-issues).

## D-004 In-place msgid rename tool

- **Context.** Renaming a msgid with the usual gettext tools is destructive here: `run_gettext.sh --full` /
  `gettext_make_pot` regenerate from `list.txt` and would drop about 276 msgids, and a plain `msgmerge` re-wraps
  about 2000 lines per language.
- **Decision.** `scripts/i18n/rename_msgids.py` (`just i18n-rename`) applies a frozen JSON mapping
  (`[{old, new}]`) in place. In the pot only the msgid lines change. In a .po, the msgid lines change and, when the
  entry has a non-empty translation, it gets `#, fuzzy` (merged into an existing flag line) and `#| msgid "<old>"`
  (kept as it is if the entry already had a previous msgid). New msgids are laid out the gettext way
  (`scripts/i18n/po.py`, 79 columns). Idempotent; fails when a catalogue has neither the old nor the new msgid, or
  both (duplicate); the mapping is rejected on identity, duplicates and chains. Obsolete `#~` entries and headers
  are never touched. `--check` reports without writing.
- **Reason.** Translators get gettext's own "previous msgid" signal for exactly the renamed entries, and nothing else
  in the 21 catalogues moves.
- **Reverting.** Run the tool with the mapping's old and new swapped, then drop the fuzzy flags it added.

## D-007 Tooling: root justfile, pinned CI image, Python tests and lint in Docker

- **Context.** The repository had no task runner and no Python test or lint setup; scripts were run by hand.
- **Decision.** A root `justfile` holds every manual operation. Python tests (pytest) and lint (ruff) run in one
  pinned CI image, `tools/docker/ci/Dockerfile` (`python:3.12-slim-bookworm` pinned by digest, `gettext` pinned, exact
  Python requirements including transitive ones). Every Docker call goes through `tools/docker/run.py`, which tags the
  image with a hash of its whole build context (not only the Dockerfile, so a requirements change also rebuilds),
  always builds and runs `linux/amd64`, mounts the repository at `/repo`, and passes `--user uid:gid` only where the
  host has POSIX ids. Test suites are discovered as `scripts/<suite>/tests` and `tools/<suite>/tests`; module checks
  as the `check` recipe of `scripts/<module>/justfile` or `tools/<module>/justfile` (`tools/ci/suites.py`). Ruff
  lints `scripts/` and `tools/`, excluding the legacy upstream scripts directly in `scripts/`. `CHANGELOG.md` at the
  root carries its rules at its top; this register lives in `wiki/`.
- **The C++ build and the C++ tests (Catch2, `tests/`) run on GitHub CI only.** They need the full dependency build
  (several hours, per OS); no local recipe builds them.
- **Reason.** One command per job, identical for humans, agents and CI, on every host OS. `tools/<suite>/tests` is
  discovered too so the tooling's own tests live next to it.
- **Reverting.** Remove `justfile`, `pyproject.toml`, `tools/docker/`, `tools/ci/`, `tools/repo/`; scripts go back
  to being run by hand.

## D-008 Line endings: LF everywhere, binaries marked

- **Context.** The repository is opened from macOS and Windows over SMB. 20 tracked files were stored with CRLF
  (`text.js`, several web assets, two workflows, `ExPolygon.cpp`, …), which churned on every edit and can break shell
  scripts on macOS.
- **Decision.** `.gitattributes` sets `* text=auto eol=lf` and marks the binary types (`png jpg jpeg gif ico icns 3mf
  stl ttf xlsx dll lib exe`) as `binary`; the CRLF files were renormalised (only line endings changed).
  `tools/repo/tests/test_line_endings.py` fails on any CRLF text file in the tree.
- **Reason.** One line ending for every OS; binary assets never touched by normalisation.
- **Reverting.** Restore the old `.gitattributes` (`* text=auto`) and drop the test.

## D-009 GUI goldens: known gap

- **Context.** The rules require every screen to be pinned to a golden image. No golden suite exists in this
  repository yet. The wxWidgets dialogs touched by the rename can only be captured from a built application, and no
  local C++ build exists (D-007).
- **Decision.** No golden is created by the safe-rename branch. The setup-guide HTML pages (`resources/web/guide/`)
  can be captured without a build; their golden suite is a separate follow-up workstream. Later branches reference
  this entry instead of creating a one-off capture.
- **Reason.** A golden suite needs its own screenshot script, fixtures and Docker capture; bolting a partial one onto a
  text change would not give full coverage.
- **Reverting.** Not applicable: closing the gap means adding the suites.

## D-010 Brand assets rendered by a pinned resvg and a stdlib ICNS writer

- **Context.** Logos and icons derived from the CosmoSlice SVG must come from a recipe and be byte-identical on every
  host. `sips`/`iconutil` exist only on macOS, a host `rsvg-convert` is unpinned, and `cairosvg` needs native cairo.
- **Decision.** `resvg` 0.48.1 is built with `cargo install --locked` in a digest-pinned `rust:1.90-slim-bookworm`
  stage of the shared CI image (`tools/docker/ci/Dockerfile`); only its binary is copied into the final stage, and it
  always runs `linux/amd64` through `tools/docker/run.py`. `scripts/brand_assets/derive.py` renders each PNG with
  `resvg -w N -h N` and writes ICNS files with `scripts/brand_assets/icns.py` (stdlib): entries in a fixed order
  (`icp4` 16, `icp5` 32, `ic07` 128, `ic08` 256, `ic09` 512, `ic10` 1024, `ic11` 32, `ic12` 64, `ic13` 256, `ic14` 512;
  type/size table verified against macOS `iconutil`), PNG payloads only, no table of contents, no info chunk, no
  timestamp. `icp6` is not written: it is a 48 px slot, and 64 px already lives in `ic12`. Outputs are rewritten in
  place and only when their bytes change. Recipes: `just -f scripts/brand_assets/justfile derive|check|stable`; `check`
  runs in `just ci`. The module lives in `scripts/`, not `resources/`, which is installed whole.
- **Reason.** One pinned renderer and one deterministic container format give the same bytes on every host and in CI.
- **Reverting.** Remove `scripts/brand_assets/` and the `resvg` stage and `COPY` line of the CI Dockerfile; the
  derived binaries then become hand-maintained files again.

## D-011 Source of truth for the visible logos, and temporary document icons

- **Context.** The Orca logo was still shown by `resources/web/image/logo.png` (home page, setup guide),
  `resources/Icon.icns` (the macOS bundle icon: `CFBundleIconFile` in `cmake/modules/MacOSXBundleInfo.plist.in`,
  `resources/` copied into `Contents/Resources`), and `resources/images/stl.icns` and `gcode.icns` (document icons).
  `resources/images/OrcaSlicer.icns` (.3mf/.obj/.amf document icon) was corrupt: no `icns` header, first 5072 bytes zero.
- **Decision.** `resources/images/OrcaSlicer.svg` is the single source of every derived app-icon variant, listed in
  `scripts/brand_assets/derived-assets.toml`: `logo.png` at 154 px (the size of the file it replaces), and
  `Icon.icns`, `images/OrcaSlicer.icns`, `images/stl.icns`, `images/gcode.icns`. File names are unchanged, so no C++,
  CMake or HTML changes. **User decision (2026-10-28), temporary:** until dedicated document icons are provided
  (asset request A2 in Open issues), `stl.icns` and `gcode.icns` use the same icon as the app; when the A2 sources
  arrive only their manifest `source` changes. Tests (`scripts/brand_assets/tests/`) require every output to equal a
  fresh render, no file under `resources/` to match the hashes of the replaced Orca files, and every `.icns` under
  `resources/` to be a valid container.
- **Reason.** One source means one place to change the brand; deriving by recipe keeps the binaries reviewable as
  "output of this source".
- **Reverting.** Restore the five binaries from git history and drop their manifest entries and the denylist test.

## D-012 Scope of the visible-logos change, and what is asked for instead of drawn

- **Context.** Several Orca or Bambu images remain in the tree; some are composed designs that cannot be derived
  from the app icon, and project rules forbid drawing a missing asset.
- **Decision.** In scope: the five files of D-011. Asked for, not drawn: the bed texture
  `resources/profiles/Custom/orcaslicer_bed_texture.svg` (A1) and dedicated .stl/.gcode document icon sources (A2),
  specified in Open issues (A1 has since been provided, see Resolved issues). Out of scope, on purpose:
  `resources/images/logo2.png` (not referenced), the embossed model `OrcaCube_v2.3mf`, the flatpak screenshots, the
  dead `src/dev-utils/platform/osx/Info.plist.in`, the single-size `.ico` files, the "grayscale" PNG that is
  coloured, and `resources/web/homepage/img/3d_text.png` (Bambu wordmark). Already CosmoSlice and untouched: `OrcaSlicer.svg`, `_about*`, `_gradient*`, `_gray`,
  `studio_logo`, `splash_logo*`, `OrcaSlicer*.png`, `OrcaSlicer.ico`, `OrcaSlicerTitle.ico`, `OrcaSlicer-mac_256px.*`.
  No golden is added: no suite exists (D-009). A bed texture is stretched over the bounding box of the printable_area,
  so its viewBox must have the aspect ratio of every bed that uses it, within 5% (not be square): the Nova artwork
  is 4.5% narrower than its 300x200 bed, which does not show.
- **Reason.** Only files that are both visible and derivable from the existing source change here; the rest needs a
  new asset or is not seen by users.
- **Reverting.** Not applicable: it only bounds the change.

## Open issues

- **Asset request A2, document icons** (D-011, optional improvement): `scripts/brand_assets/sources/stl-document.svg`
  and `gcode-document.svg` (viewBox `0 0 1024 1024`; Apple document page with a folded corner, the CosmoSlice tile
  centred, about 410 px wide at y 290-700, an "STL" / "GCODE" grey label with text outlined to paths). Then point the
  `stl.icns` and `gcode.icns` manifest entries at them and run `just -f scripts/brand_assets/justfile derive`.
  Alternative: finished `.icns` files with 16-1024 px entries.
- **CI job runs `just ci`** (follow-up): the GitHub workflows do not run `just ci` yet, so the brand-asset `check` and
  tests only gate locally until a CI job calls it.
- **Icon.icns chain not verified on a build** (D-011): `CFBundleIconFile` = `Icon.icns` is read from the CMake and
  packaging scripts; check the icon of the next CI DMG. Finder and LaunchServices may show the old icon from cache.
  Also check the 16 and 32 px list-view icons in Finder: `icp4`/`icp5` hold PNG payloads, while `iconutil` writes
  ARGB `ic04`/`ic05` for those sizes.
- **No golden suite** (D-009): wx dialogs need a build; the setup-guide HTML goldens are a follow-up workstream.
- **Nova Double Tete bed logo squeezed** (D-012): the `Cosmyx Nova Double Tete` machine model reuses
  `resources/profiles/cosmyx/Nova-bed_texture.svg` (drawn for the 300x200 Nova bed), but its printable_area is
  156x200 (x 68-224), and the texture is stretched over that box, so the logo is about half as wide as it should be.
  Needs a dedicated texture from Cosmyx with the aspect ratio of a 156x200 bed (SVG, NanoSVG-safe: inline styles, no
  `<style>`, clipPath, mask, filter or text), or a decision that the bed area is wrong. Excluded in `KNOWN_STRETCHED`
  of `scripts/brand_assets/tests/test_bed_texture.py`, which fails once it is no longer needed.
- **Merge request links**: CHANGELOG lines of this branch carry `MR: pending` until the request is opened.

## Resolved issues

- **Asset request A1, bed texture** (D-012), resolved 2026-10-28: the user provided the CosmoSlice bed texture, now
  `resources/profiles/Custom/orcaslicer_bed_texture.svg` (name kept, so the MyKlipper, MyMarlin, MyRRF and
  MyToolChanger profiles need no change). On the user's request one change was made to the file as provided: its
  `<clipPath id="_clip1">` element was removed and the `<g clip-path="url(#_clip1)">` that used it became a plain
  `<g>`. NanoSVG, which draws the bed, has no clipPath support and draws the rect inside it as an opaque black square
  behind the logo; the clip region was the whole 100x100 logo box and the logo lies inside it, so removing it changes
  nothing in a browser. The Orca texture's hash is in the denylist of
  `scripts/brand_assets/tests/test_visible_logos.py`, and `scripts/brand_assets/tests/test_bed_texture.py` keeps
  every SVG bed texture of the profiles NanoSVG-safe.
- **Nova bed texture not NanoSVG-safe** (D-012), resolved 2026-10-28 on the user's decision:
  `resources/profiles/cosmyx/Nova-bed_texture.svg` (cosmyx profile pack, used by the Nova, Nova Metal Ceramique,
  Nova Haute Temperature, Nova Double Tete and Nova can-out machine models) coloured its 77 shapes through a
  `<style>` sheet with classes. NanoSVG, which draws the bed, has no stylesheet support, so every shape was drawn
  opaque black instead of white, blue (`#335AFA`) and red (`#DA0000`). Each `class="stN"` was replaced by the inline
  `style` of its class and the `<style>` element removed, nothing else changed (paths, viewBox, ids, order): the
  resolved fill and stroke of every shape are identical, and NanoSVG now reads 75 white, 1 blue and 1 red shape. The
  file now passes the NanoSVG check of `scripts/brand_assets/tests/test_bed_texture.py` without an exclusion.
  Reverting: restore the file from git history and put it back in `KNOWN_UNSAFE`.
