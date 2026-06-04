"""Backward-compatible entry point — prefer `streamlit run streamlit_app/app.py`."""

import importlib.util
import sys
from pathlib import Path

_BOOTSTRAP = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("streamlit_bootstrap", _BOOTSTRAP)
if _spec and _spec.loader:
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["streamlit_bootstrap"] = _module
    _spec.loader.exec_module(_module)

from streamlit_app.app import main

if __name__ == "__main__":
    main()
