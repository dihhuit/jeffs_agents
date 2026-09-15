"""Shared pytest fixtures/helpers.

Makes the scripts/lib package importable as a plain module namespace so the
tests can import ``model_registry`` and ``validate`` the same way
``scripts/build.sh`` invokes them (``python3 scripts/lib/validate.py``).
"""

from __future__ import annotations

import sys
from pathlib import Path

SCRIPT_LIB = Path(__file__).resolve().parents[1] / "scripts" / "lib"
if str(SCRIPT_LIB) not in sys.path:
    sys.path.insert(0, str(SCRIPT_LIB))