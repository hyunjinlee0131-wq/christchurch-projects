"""Christchurch Projects: interactive tools (Streamlit). Entry point for Streamlit Community Cloud."""
import streamlit as st

st.set_page_config(page_title="Christchurch Projects: tools", page_icon="🗺️", layout="wide")
st.title("Christchurch Projects: tools")
st.write(
    "Interactive tools built on Christchurch City Council open data. "
    "The first one, **wastewater pipe blockages and tree roots**, is on its way."
)
st.link_button("Back to Christchurch Projects", "https://hyunjinlee0131-wq.github.io/christchurch-projects/")
