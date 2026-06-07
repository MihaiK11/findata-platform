from __future__ import annotations

import importlib.util
import logging
import sys
from pathlib import Path

# Streamlit puts streamlit_app/ on sys.path, not the repo root — load bootstrap first.
_BOOTSTRAP = Path(__file__).resolve().parent / "_bootstrap.py"
_spec = importlib.util.spec_from_file_location("streamlit_bootstrap", _BOOTSTRAP)
if _spec and _spec.loader:
    _module = importlib.util.module_from_spec(_spec)
    sys.modules["streamlit_bootstrap"] = _module
    _spec.loader.exec_module(_module)
else:
    _root = Path(__file__).resolve().parent.parent
    if str(_root) not in sys.path:
        sys.path.insert(0, str(_root))

import streamlit as st

from streamlit_app.views.analytics import render as render_analytics
from streamlit_app.views.assistant import render as render_assistant
from streamlit_app.views.dashboard import render as render_dashboard

logging.basicConfig(level=logging.INFO)


def main() -> None:
    st.set_page_config(page_title="Findata Dashboard", page_icon="📈", layout="wide")
    st.sidebar.title("Findata")
    page = st.sidebar.radio("Navigate", ["Dashboard", "Analytics", "Assistant"], index=0)
    if page == "Dashboard":
        render_dashboard()
    elif page == "Analytics":
        render_analytics()
    else:
        render_assistant()


if __name__ == "__main__":
    main()
