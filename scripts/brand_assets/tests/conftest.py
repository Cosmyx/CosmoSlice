"""Import the brand_assets modules as the `brand_assets` package (tests run with --import-mode=importlib).

Every suite runs in one pytest session, so the module folder is not put on sys.path: bare names such as `derive`
or `icns` would clash with another suite's modules. Tests import `from brand_assets import derive, icns`.
"""

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

MODULE_DIR = Path(__file__).resolve().parents[1]

if "brand_assets" not in sys.modules:
    spec = importlib.machinery.ModuleSpec("brand_assets", None, is_package=True)
    spec.submodule_search_locations = [str(MODULE_DIR)]
    sys.modules["brand_assets"] = importlib.util.module_from_spec(spec)
