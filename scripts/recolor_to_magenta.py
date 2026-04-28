#!/usr/bin/env python3
"""
Recolor CosmoSlice UI from Teal/Cyan (#009688) to Magenta/Purple (#9C27B0).

Run from the repo root:
    python scripts/recolor_to_magenta.py

What it does
------------
- Replaces every hardcoded teal/cyan colour in C++/header files under src/
  with the corresponding magenta/purple value.
- BitmapCache.cpp is handled specially: SVG lookup KEYS stay as #009688
  (SVG files are not changed), only the target VALUES are updated.
  A new light-mode replacement is also inserted so icons become purple in
  both light and dark mode.
- Idempotent: safe to run more than once.
"""

import os

# ---------------------------------------------------------------------------
# Colour map
# ---------------------------------------------------------------------------
# Light   Dark     Notes
# #009688 #00675b  Main brand (teal)            -> #9C27B0 / #6A1B9A
# #26A69A #--      Hover tint                   -> #AB47BC
# #52c7b8 #--      Secondary lighter teal       -> #CE93D8
# #BFE1DE #223C3C  25 % tint (dropdown sel bg)  -> #E1BEE7 / #2E1A35
# #E5F0EE #283232  10 % tint (combo focus bg)   -> #F3E5F5 / #231533
# #00FFD4 #--      Bright accent (Button.cpp)   -> #EA80FC
# #009789 #--      Typo variant (AboutDialog)   -> #9C27B0
# ---------------------------------------------------------------------------

GENERAL_REPLACEMENTS = [
    # StateColor.cpp dark-mode colour-map pairs (match whole pair for safety)
    ('{"#009688", "#00675b"}', '{"#9C27B0", "#6A1B9A"}'),
    ('{"#BFE1DE", "#223C3C"}', '{"#E1BEE7", "#2E1A35"}'),
    ('{"#E5F0EE", "#283232"}', '{"#F3E5F5", "#231533"}'),

    # ImGui colour constructors
    ('IM_COL32(0, 150, 136, 255)', 'IM_COL32(156, 39, 176, 255)'),
    ('ImColor(0, 150, 136,',       'ImColor(156, 39, 176,'),

    # wxColour/wxColor RGB constructors
    ('wxColour(0, 150, 136)',   'wxColour(156, 39, 176)'),
    ('wxColor(0, 150, 136)',    'wxColor(156, 39, 176)'),
    # Hover variant rgb(38,166,154) == #26A69A  ->  rgb(171,71,188) == #AB47BC
    ('wxColour(38, 166, 154)', 'wxColour(171, 71, 188)'),
    ('wxColor(38, 166, 154)',  'wxColor(171, 71, 188)'),

    # Hex integer literals
    ('0x009688', '0x9C27B0'),
    ('0xBFE1DE', '0xE1BEE7'),
    ('0xE5F0EE', '0xF3E5F5'),
    ('0x52c7b8', '0xCE93D8'),

    # Quoted hex strings — dark-mode teal first, then variants, then main
    ('"#00675b"', '"#6A1B9A"'),
    ('"#26A69A"', '"#AB47BC"'),
    ('"#BFE1DE"', '"#E1BEE7"'),
    ('"#E5F0EE"', '"#F3E5F5"'),
    ('"#52c7b8"', '"#CE93D8"'),
    ('"#00FFD4"', '"#EA80FC"'),
    ('"#009789"', '"#9C27B0"'),   # typo variant in AboutDialog.cpp
    ('"#009688"', '"#9C27B0"'),   # main — do last

    # HTML span bgcolor
    ('bgcolor="#009688"', 'bgcolor="#9C27B0"'),
    ("bgcolor='#009688'", "bgcolor='#9C27B0'"),

    # wxColour("#XXXX") / wxColor("#XXXX") — bare call with parens
    ('("#BFE1DE")', '("#E1BEE7")'),
    ('("#E5F0EE")', '("#F3E5F5")'),
    ('("#009688")', '("#9C27B0")'),
    ('("#00675b")', '("#6A1B9A")'),
    ('("#26A69A")', '("#AB47BC")'),
]

# ---------------------------------------------------------------------------
# BitmapCache.cpp — needs special treatment
#
# The file stores SVG colour-replacement maps like:
#   replaces["\"#009688\""] = "\"#00675b\"";
# As raw text the value portion is:  = "\"#009688\""
# In Python that string is:          '= "\\"#009688\\""'
# (\\  = one backslash,  " = doublequote)
#
# We must NOT change the lookup KEYS (SVG files still contain #009688).
# We only change the TARGET VALUES and also update the bare-form:
#   replaces["#009688"] = "#00675b";
# ---------------------------------------------------------------------------
_bq = '\\"'   # backslash + doublequote — the escaped-quote used in BitmapCache

BITMAP_CACHE_REPLACEMENTS = [
    # Line 326 value:  "\"#009688\""  ->  "\"#9C27B0\""
    (f'= "{_bq}#009688{_bq}"', f'= "{_bq}#9C27B0{_bq}"'),
    # Line 327 value:  "\"#52c7b8\""  ->  "\"#CE93D8\""
    (f'= "{_bq}#52c7b8{_bq}"', f'= "{_bq}#CE93D8{_bq}"'),
    # Line 337 value (dark mode):  "\"#00675b\""  ->  "\"#6A1B9A\""
    (f'= "{_bq}#00675b{_bq}"', f'= "{_bq}#6A1B9A{_bq}"'),
    # Line 346 bare form (dark-mode toggle):  ] = "#00675b"  ->  ] = "#6A1B9A"
    ('] = "#00675b"', '] = "#6A1B9A"'),
]

# Structural patch: insert a light-mode SVG replacement so icons become purple
# in light mode too (currently only dark mode replaces the colour).
_LIGHT_MODE_OLD_ELSE = (
    '    } else {\n'
    '        replaces["#949494"] = "#7C8282"; // ORCA replace icon line color for light theme\n'
    '    }'
)
_LIGHT_MODE_NEW_ELSE = (
    '    } else {\n'
    '        replaces["#949494"] = "#7C8282"; // ORCA replace icon line color for light theme\n'
    f'        replaces["{_bq}#009688{_bq}"] = "{_bq}#9C27B0{_bq}"; // CosmoSlice: teal SVGs -> purple\n'
    '    }'
)

_TOGGLE_OLD = (
    'if (strstr(bitmap_name.c_str(), "toggle_on") != NULL && dark_mode) '
    '// ORCA only replace color of toggle button\n'
    '        replaces["#009688"] = "#6A1B9A";'
)
_TOGGLE_NEW = (
    'if (strstr(bitmap_name.c_str(), "toggle_on") != NULL && dark_mode) '
    '// ORCA only replace color of toggle button\n'
    '        replaces["#009688"] = "#6A1B9A";\n'
    '    else if (strstr(bitmap_name.c_str(), "toggle_on") != NULL)\n'
    '        replaces["#009688"] = "#9C27B0"; // CosmoSlice brand (light mode)'
)

# ---------------------------------------------------------------------------
TARGET_EXTENSIONS = {'.cpp', '.hpp', '.h', '.mm'}
SKIP_DIRS         = {'build', 'deps', '.git', '__pycache__'}
BITMAP_CACHE_REL  = os.path.join('src', 'slic3r', 'GUI', 'BitmapCache.cpp')


def process_file(path: str, replacements: list) -> bool:
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            original = f.read()
    except Exception as e:
        print(f'  [SKIP] {path}: {e}')
        return False

    text = original
    applied = []
    for old, new in replacements:
        if old in text:
            text = text.replace(old, new)
            applied.append(f'    {old!r} -> {new!r}')

    if text == original:
        return False

    try:
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(text)
    except Exception as e:
        print(f'  [ERROR] {path}: {e}')
        return False

    print(f'[MODIFIED] {os.path.basename(path)}')
    for a in applied:
        print(a)
    return True


def patch_bitmap_cache_structure(path: str):
    """Insert light-mode SVG replacement and update toggle_on else branch."""
    DONE_MARKER = '#9C27B0"; // CosmoSlice: teal SVGs'
    try:
        with open(path, 'r', encoding='utf-8', errors='replace') as f:
            text = f.read()
    except Exception as e:
        print(f'  [SKIP] {path}: {e}')
        return

    changed = False

    if DONE_MARKER not in text:
        if _LIGHT_MODE_OLD_ELSE in text:
            text = text.replace(_LIGHT_MODE_OLD_ELSE, _LIGHT_MODE_NEW_ELSE)
            print(f'[MODIFIED] BitmapCache.cpp — light-mode else block patched')
            changed = True
        else:
            print('[WARNING] BitmapCache.cpp: else block not found — add manually:')
            print(f'          replaces["{_bq}#009688{_bq}"] = "{_bq}#9C27B0{_bq}"; // light mode')

    if _TOGGLE_OLD in text:
        text = text.replace(_TOGGLE_OLD, _TOGGLE_NEW)
        print(f'[MODIFIED] BitmapCache.cpp — toggle_on light-mode branch added')
        changed = True
    elif '#9C27B0"; // CosmoSlice brand (light mode)' in text:
        print(f'[SKIP] BitmapCache.cpp toggle_on patch already applied')

    if changed:
        with open(path, 'w', encoding='utf-8', errors='replace') as f:
            f.write(text)


def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    repo_root  = os.path.dirname(script_dir)
    src_dir    = os.path.join(repo_root, 'src')
    bitmap_cache = os.path.join(repo_root, BITMAP_CACHE_REL)

    print(f'Repo root : {repo_root}')
    print(f'Colour map: teal #009688 -> purple #9C27B0')
    print('=' * 70)

    modified = 0
    checked  = 0

    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for filename in filenames:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in TARGET_EXTENSIONS:
                continue
            filepath = os.path.join(dirpath, filename)
            checked += 1
            is_bitmap_cache = os.path.normpath(filepath) == os.path.normpath(bitmap_cache)
            replacements = BITMAP_CACHE_REPLACEMENTS if is_bitmap_cache else GENERAL_REPLACEMENTS
            if process_file(filepath, replacements):
                modified += 1

    print('=' * 70)
    print(f'Checked  : {checked} files')
    print(f'Modified : {modified} files')

    print('\n--- BitmapCache.cpp structural patch ---')
    if os.path.exists(bitmap_cache):
        patch_bitmap_cache_structure(bitmap_cache)
    else:
        print(f'[WARNING] Not found: {bitmap_cache}')

    print('\nDone. Rebuild to see the new magenta/purple theme.')
    print()
    print('Colour mapping:')
    print('  #009688 / rgb(0,150,136)    ->  #9C27B0 / rgb(156,39,176)  [main brand]')
    print('  #00675b                     ->  #6A1B9A                    [dark mode]')
    print('  #26A69A / rgb(38,166,154)   ->  #AB47BC / rgb(171,71,188)  [hover]')
    print('  #52c7b8                     ->  #CE93D8                    [secondary light]')
    print('  #BFE1DE                     ->  #E1BEE7                    [25 %% tint]')
    print('  #E5F0EE                     ->  #F3E5F5                    [10 %% tint]')
    print('  #00FFD4                     ->  #EA80FC                    [bright accent]')


if __name__ == '__main__':
    main()
