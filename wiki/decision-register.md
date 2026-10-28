# Decision register

Every decision taken while working on CosmoSlice is recorded here with its number, so later changes can find why the
code is the way it is. Numbers are never reused. An entry gives the context, the decision, the reason, and what
reverting it would take. Problems found but not fixed go to [Open issues](#open-issues).

## D-001 Rename scope: user-visible text only

- **Context.** CosmoSlice is a fork of OrcaSlicer and must show its own name, while staying easy to merge with
  upstream.
- **Decision.** Only text a user reads is renamed: translatable msgids, dialog titles and messages, hints, the setup
  guide. Out of scope: log lines (`BOOST_LOG_TRIVIAL`, `COSMO_LOG`, `[Orca Updater]`), the `orcaslicer_main` thread
  name, comments and `// Orca:` markers, C++ identifiers, file and icon names, persisted keys, strings compared or
  parsed elsewhere, links to upstream documentation, the CLI `result.json` messages, the Linux `.desktop` names
  (follow-up), developer tools and third-party identifiers. Each kept literal is listed with its reason in
  `scripts/i18n/data/product_name_allowlist.json`.
- **Reason.** Renaming invisible text gives users nothing and multiplies upstream merge conflicts; renaming persisted
  or compared strings would break existing installs, projects and integrations.
- **Reverting.** Swap the mapping and run `just i18n-rename`, revert the C++ literal changes.

## D-002 Literal "CosmoSlice" in msgids

- **Context.** A msgid can name the product literally or through `%s` filled with `SLIC3R_APP_NAME`.
- **Decision.** msgids, hints and text.js strings say "CosmoSlice" literally. Non-translated narrow C++ literals use
  `SLIC3R_APP_NAME` by adjacent literal concatenation (`"Switching " SLIC3R_APP_NAME " to language "`); the wide
  Windows DLL warning in `OrcaSlicer.cpp` says `L"...CosmoSlice..."` directly.
- **Reason.** Static `L()` tooltips, hints.ini and text.js cannot format; mixing placeholders into existing
  translations is error-prone; translators see the real sentence. Precedent: `GUI_App.cpp` and `Preferences.cpp`
  already had literal "CosmoSlice" msgids.
- **Reverting.** As D-001.

## D-003 Display-name macros

- **Context.** `SLIC3R_APP_FULL_NAME` ("Orca Slicer") feeds about 100 display-only sites; `GCODEVIEWER_APP_NAME` and
  `GCODEVIEWER_BUILD_ID` are shown in About, System information and an error title.
- **Decision.** In `libslic3r.h`: `SLIC3R_APP_FULL_NAME` = `SLIC3R_APP_NAME`; `GCODEVIEWER_APP_NAME` =
  `SLIC3R_APP_NAME " G-code Viewer"`; `GCODEVIEWER_BUILD_ID` = `std::string(GCODEVIEWER_APP_NAME "-") +
  SLIC3R_VERSION + "-RC"`. `GCODEVIEWER_APP_KEY` stays (it names the viewer's configuration folder).
- **Reason.** One source for the name (`version.inc`); every use is a string literal context, checked before commit
  (only these three macro lines and seven `SLIC3R_APP_NAME` substitutions change code outside literal contents,
  and every touched file includes `libslic3r_version.h`). The C++ build itself is verified by GitHub CI (D-007).
- **Reverting.** Restore the three `#define` lines.

## D-004 In-place msgid rename tool

- **Context.** Renaming a msgid with the usual gettext tools is destructive here: `run_gettext.sh --full` /
  `gettext_make_pot` regenerate from `list.txt` and would drop about 276 msgids, and a plain `msgmerge` re-wraps
  about 2000 lines per language.
- **Decision.** `scripts/i18n/rename_msgids.py` (`just i18n-rename`) applies a frozen JSON mapping
  (`[{old, new}]`) in place. In the pot only the msgid lines change. In a .po, the msgid lines change and, when the
  entry has a non-empty translation, it gets `#, fuzzy` (merged into an existing flag line) and `#| msgid "<old>"`,
  preceded by `#| msgctxt "<ctx>"` when the entry has a context (kept as it is if the entry already had a previous
  msgid). New msgids are laid out the gettext way (`scripts/i18n/po.py`, 79 columns). Idempotent; fails when a
  catalogue has neither the old nor the new msgid, or both (duplicate); the mapping is rejected on identity,
  duplicates and chains. Every catalogue is computed before any is written, so a failure leaves none half-renamed.
  Obsolete `#~` entries and headers are never touched. `--check` reports without writing.
- **Consequence.** msgfmt leaves fuzzy entries out of the `.mo` (the build does not pass `--use-fuzzy`), so until
  each language's translation is updated the 76 renamed strings show in English in translated UIs.
- **Reason.** Translators get gettext's own "previous msgid" signal for exactly the renamed entries, and nothing else
  in the 21 catalogues moves.
- **Reverting.** Run the tool with the mapping's old and new swapped, then drop the fuzzy flags it added.

## D-005 Upstream names kept on purpose

- **Decision.** These keep "Orca"/"OrcaSlicer": the About credit ("CosmoSlice is based on OrcaSlicer, …"); the
  built-in models Orca Cube, Orca Tolerance Test, Orca String Hell (their names are compared in
  `GUI_Factories.cpp`); the Orca YOLO calibration (its name is persisted in projects); the Orca Arena printers;
  "created with an OrcaSlicer 2.3.1-alpha" (names the release that wrote the project); "Test OrcaSlicer (GitHub)"
  (tests the upstream server); "If you would like to try Orca Slicer Beta" (the link opens upstream releases).
- **Reason.** Each one names the upstream project or a thing that is called that, or is compared/persisted.
- **Reverting.** Add the entry to the mapping and remove it from the allow-list.

## D-006 Product-name guard

- **Decision.** `scripts/i18n/tests/test_product_name_guard.py` (in `just test i18n` and `just i18n-check`) fails
  when a translatable msgid, a non-log C++ literal, the pot, hints.ini, the `en` block of text.js or the setup-guide
  HTML names the upstream product, unless the entry is in `scripts/i18n/data/product_name_allowlist.json`. Entries
  are keyed by file and exact literal (with an occurrence count), never by line number, and carry a reason category
  (`asset`, `cli`, `compared`, `credit`, `dev-tool`, `external`, `internal`, `kept-name`, `linux-desktop`,
  `persisted`, `url`). Stale entries fail too. Log statements and `#include` lines are skipped by rule. The token is
  `Orca ?Slicer|Orca|ORCA` as a word (also after an escaped `\n`); lowercase identifiers never match. Translations
  are checked for the upstream name and its native spellings (zh 逆戟鲸/逆戟鯨, ko 오르카) in confirmed (non-fuzzy)
  entries of renamed msgids.
- **Reason.** Upstream merges bring new strings; the guard catches them instead of a user.
- **Reverting.** Delete the test and the allow-list.

## D-007 Tooling: root justfile, pinned CI image, Python tests and lint in Docker

- **Context.** The repository had no task runner and no Python test or lint setup; scripts were run by hand.
- **Decision.** A root `justfile` holds every manual operation. Python tests (pytest) and lint (ruff) run in one
  pinned CI image, `tools/docker/ci/Dockerfile` (`python:3.12-slim-bookworm` pinned by digest, `gettext` pinned, exact
  Python requirements including transitive ones). Every Docker call goes through `tools/docker/run.py`, which tags the
  image with a hash of its whole build context (not only the Dockerfile, so a requirements change also rebuilds),
  always builds and runs `linux/amd64`, mounts the repository at `/repo`, and passes `--user uid:gid` only where the
  host has POSIX ids. Test suites are discovered as `scripts/<suite>/tests` and `tools/<suite>/tests`; module checks
  as the `check` recipe of `scripts/<module>/justfile` or `tools/<module>/justfile` (`tools/ci/suites.py`). The
  image tag hashes only real build-context files: `__pycache__`, host dotfiles (`.DS_Store`, `._*`) and SMB
  `.smbdelete*` leftovers are skipped, `.dockerignore` is kept. `just ci` runs lint, every suite (the
  product-name guard included), the catalogue check (`just i18n-catalogs`) and the module checks, each once. Ruff
  lints `scripts/` and `tools/`, excluding the legacy upstream scripts directly in `scripts/`. `CHANGELOG.md` at the
  root carries its rules at its top; this register lives in `wiki/`.
- **Accepted risk: the apt pin.** `gettext=0.21-12` is pinned against the live bookworm index, which drops a version
  after a Debian point or security release that replaces it; the image build then fails. Fix at that point: bump the
  pin to the new version, or install from `snapshot.debian.org` for a frozen index.
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
  `tools/repo/line_endings.py` (the `check` recipe of `tools/repo/justfile`, run by `just ci`) fails on any
  tracked text file with CRLF in the working tree; untracked and ignored files are never read. It lists the files
  with `git ls-files`, so it runs on the host, not in the CI image: the image has no git, and a worktree's git
  folder lies outside the mounted repository. git is present on every host OS that has the repository. Its
  selection logic and `.gitattributes` are tested in `tools/repo/tests/`.
- **Reason.** One line ending for every OS; binary assets never touched by normalisation.
- **Reverting.** Restore the old `.gitattributes` (`* text=auto`) and drop `tools/repo/line_endings.py`, the `check`
  recipe of `tools/repo/justfile` and `tools/repo/tests/test_line_endings.py`.

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
  coloured, and `resources/web/homepage/img/3d_text.png` (Bambu wordmark). Already CosmoSlice and untouched:
  `OrcaSlicer.svg`, `_about*`, `_gradient*`, `_gray`, `studio_logo`, `splash_logo*`, `OrcaSlicer*.png`,
  `OrcaSlicer.ico`, `OrcaSlicerTitle.ico`, `OrcaSlicer-mac_256px.*`.
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
- **Config.cpp:1287** only recognises `; generated by CosmoSlice` as its own G-code header (pre-existing; G-code
  written by OrcaSlicer is detected by the `; OrcaSlicer` branch only).
- **InstanceCheck.cpp:108**: Windows single-instance detection looks for "OrcaSlicer" in window titles while the main
  window is titled CosmoSlice, so it likely never matches (pre-existing).
- **Catalogue regeneration is destructive**: `update-translation.yml` / `run_gettext.sh --full` would drop about 276
  msgids (list.txt is incomplete); use `just i18n-update-pot` and `just i18n-rename`.
- **HintsToPot.py** appends duplicate entries when re-run.
- **8 obsolete pot entries** have no source any more.
- **"Download Beta Version"** links to the BambuStudio releases page.
- **Version check URL** still points upstream (the check is disabled).
- **Pot without blank lines**: a few pot entries are not separated by a blank line (`po.py` handles it).
- **macOS menu name**: `WipeTowerDialog.cpp:466` tells users to look in "CosmoSlice > Preferences", but the macOS
  application menu is titled by `CFBundleName`, which is `SLIC3R_APP_KEY` ("OrcaSlicer",
  `src/dev-utils/platform/osx/Info.plist.in`). The string stays; it becomes right with the Info.plist / bundle-name
  follow-up that renames the bundle.
- **`.bat` files are LF now** (D-008): cmd has label-lookup bugs with LF batch files, and
  `build_release_vs2022.bat` jumps with `GOTO :slicer` (called by `.github/workflows/build_orca.yml`). Verify on
  the GitHub Windows build; if it fails, add a recorded `*.bat eol=crlf` exception.
- **Translations pending**: after the rename, every .po has fuzzy entries for the renamed msgids and some text.js
  keys are listed in `scripts/i18n/pending/<lang>.txt`; see `just i18n-status`.
- **Setup guide leftovers**: `guide/21` and `guide/24` show "Orca colosseum" from their JS (out of scope), and some
  text.js blocks keep unused `wk*` keys naming the upstream product (no page uses them).


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
