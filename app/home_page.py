"""Landing page: lists the tools."""
import streamlit as st

from lib.data import load_metrics

st.title("Christchurch Projects: tools")
st.markdown("Interactive tools built on Christchurch City Council open data. Pick one:")

m = load_metrics("pipe_blockages")
with st.container(border=True):
    st.markdown("### 🚰 Which sewer pipes block, and do trees cause it?")
    if m:
        st.markdown(m["headline"])
    st.page_link(st.session_state["pages"]["pipes"], label="Open the pipe blockages tool →")

st.link_button("← Back to Christchurch Projects", "https://hyunjinlee0131-wq.github.io/christchurch-projects/")
