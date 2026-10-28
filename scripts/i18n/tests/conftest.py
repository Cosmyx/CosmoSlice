"""Make the i18n modules importable (tests run with --import-mode=importlib)."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
