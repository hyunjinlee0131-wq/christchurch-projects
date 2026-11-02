"""👍/👎 into the same Supabase `feedback` table the website uses (insert-only for the anon key)."""
import os

import requests
import streamlit as st


def _secret(name: str) -> str:
    try:
        return str(st.secrets.get(name, "")) or os.environ.get(name, "")
    except Exception:  # no secrets file at all
        return os.environ.get(name, "")


def feedback_enabled() -> bool:
    return bool(_secret("SUPABASE_URL") and _secret("SUPABASE_ANON_KEY"))


def send_feedback(project: str, item_id: str, value: int) -> bool:
    if not feedback_enabled():
        return False
    url, key = _secret("SUPABASE_URL").rstrip("/"), _secret("SUPABASE_ANON_KEY")
    try:
        r = requests.post(f"{url}/rest/v1/feedback", timeout=5,
                          headers={"apikey": key, "Authorization": f"Bearer {key}", "Content-Type": "application/json",
                                   "Prefer": "return=minimal"},
                          json={"project": project, "item_id": item_id, "value": value})
        return r.status_code in (201, 204)
    except requests.RequestException:
        return False
