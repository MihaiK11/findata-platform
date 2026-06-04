"""Put the repository root on sys.path when Streamlit runs scripts inside streamlit_app/."""

from __future__ import annotations

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_ROOT_STR = str(_ROOT)
if _ROOT_STR not in sys.path:
    sys.path.insert(0, _ROOT_STR)
