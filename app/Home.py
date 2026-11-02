"""Christchurch Projects: interactive tools (Streamlit). Entry point for Streamlit Community Cloud."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import streamlit as st

from lib.data import load_metrics

st.set_page_config(page_title="Christchurch Projects: tools", page_icon="🗺️", layout="wide")
st.title("Christchurch Projects: tools")
st.markdown("Interactive tools built on Christchurch City Council open data. Pick one:")

m = load_metrics("pipe_blockages")
with st.container(border=True):
    st.markdown("### 🚰 Which sewer pipes block, and do trees cause it?")
    if m:
        st.markdown(f"{m['headline']}")
    st.page_link("pages/1_Pipe_Blockages.py", label="Open the pipe blockages tool →")

st.link_button("← Back to Christchurch Projects", "https://hyunjinlee0131-wq.github.io/christchurch-projects/")
