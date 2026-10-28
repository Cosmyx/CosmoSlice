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
  entry has a non-empty translation, it gets `#, fuzzy` (merged into an existing flag line) and `#| msgid "<old>"`
  (kept as it is if the entry already had a previous msgid). New msgids are laid out the gettext way
  (`scripts/i18n/po.py`, 79 columns). Idempotent; fails when a catalogue has neither the old nor the new msgid, or
  both (duplicate); the mapping is rejected on identity, duplicates and chains. Obsolete `#~` entries and headers
  are never touched. `--check` reports without writing.
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

## Open issues

- **No golden suite** (D-009): wx dialogs need a build; the setup-guide HTML goldens are a follow-up workstream.
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
- **Translations pending**: after the rename, every .po has fuzzy entries for the renamed msgids and some text.js
  keys are listed in `scripts/i18n/pending/<lang>.txt`; see `just i18n-status`.
