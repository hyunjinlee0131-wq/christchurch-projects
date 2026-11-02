"""Christchurch Projects: interactive tools (Streamlit). Entry point for Streamlit Community Cloud.

Pages are declared here with st.navigation (not discovered from a pages/ folder at startup), so adding a page
never depends on the server process having been started after the folder existed.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

st.set_page_config(page_title="Christchurch Projects: tools", page_icon="🗺️", layout="wide")

pages = {
    "home": st.Page("home_page.py", title="Home", icon="🏠", default=True),
    "pipes": st.Page("pages/1_Pipe_Blockages.py", title="Sewer pipe blockages", icon="🚰", url_path="Pipe_Blockages"),
}
st.session_state["pages"] = pages
st.navigation(list(pages.values())).run()
