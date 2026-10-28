# CosmoSlice task runner. `just` lists every recipe; containerised steps run in the pinned CI image
# (tools/docker/ci/Dockerfile) through tools/docker/run.py, so the same command works on every host OS.
# The C++ slicer itself is built and tested by GitHub CI only (see wiki/decision-register.md, D-007).

set windows-shell := ["powershell.exe", "-NoLogo", "-Command"]

python := if os_family() == "windows" { "python" } else { "python3" }
docker := python + " tools/docker/run.py"

# List every recipe
default:
    @just --justfile "{{justfile()}}" --list

# Build the pinned CI image if its Dockerfile changed, and print its tag
ci-image:
    {{docker}} --build-only

# Run one Python test suite (scripts/<suite>/tests or tools/<suite>/tests), or all of them, in the CI image
test suite="":
    {{docker}} -- python tools/ci/suites.py pytest {{suite}}

# List the discovered Python test suites
suites:
    {{python}} tools/ci/suites.py list

# Lint and format-check the Python tooling with ruff in the CI image
lint:
    {{docker}} -- ruff check scripts tools
    {{docker}} -- ruff format --check scripts tools

# Rewrite the Python tooling with ruff's formatter and safe fixes, in the CI image
fmt:
    {{docker}} -- ruff format scripts tools
    {{docker}} -- ruff check --fix scripts tools

# Append msgids found in src/ but missing from the pot and every .po (wraps scripts/update_pot.py)
i18n-update-pot:
    {{python}} scripts/update_pot.py --update-po

# Full gate: lint, every test suite, every module `check` recipe (discovered)
ci: lint test
    {{python}} tools/ci/suites.py checks --just "{{just_executable()}}"
