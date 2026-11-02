"""Read precomputed project outputs (the app never fetches council data or runs models)."""
import json
import os
import unicodedata
from pathlib import Path

import pandas as pd
import streamlit as st


def projects_dir() -> Path:
    return Path(os.environ.get("CP_PROJECTS_DIR", Path(__file__).parents[2] / "projects"))


@st.cache_data(show_spinner=False)
def _read_parquet(path: str, mtime: float) -> pd.DataFrame:
    return pd.read_parquet(path)


def load_pipes() -> pd.DataFrame | None:
    p = projects_dir() / "pipe_blockages" / "outputs" / "pipes.parquet"
    return _read_parquet(str(p), p.stat().st_mtime) if p.exists() else None


def load_metrics(slug: str) -> dict | None:
    p = projects_dir() / slug / "outputs" / "metrics.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def fold(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)).lower().strip()


def search_street(df: pd.DataFrame, q: str) -> pd.DataFrame:
    q = fold(q)
    if not q:
        return df.iloc[0:0]
    return df[df["street"].map(fold).str.contains(q, regex=False)]
