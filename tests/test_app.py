import sys
from pathlib import Path

import pandas as pd
import pytest
from streamlit.testing.v1 import AppTest

APP = Path(__file__).parents[1] / "app"
PAGE = str(APP / "pages" / "1_Pipe_Blockages.py")
sys.path.insert(0, str(APP))


@pytest.fixture(autouse=True)
def no_secrets(monkeypatch):
    monkeypatch.delenv("SUPABASE_URL", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)


def run_page(**env):
    at = AppTest.from_file(PAGE, default_timeout=60)
    return at.run()


def test_app_page_renders_headline_metrics():
    at = run_page()
    assert not at.exception, at.exception
    assert len(at.metric) >= 4
    assert any("recorded blockages" in m.label.lower() for m in at.metric)


def test_app_street_search_handles_no_match():
    at = run_page()
    at.text_input(key="street").input("zzzz-no-such-street").run()
    assert not at.exception
    assert any("No pipes found" in i.value for i in at.info)


def test_app_street_search_finds_a_real_street():
    at = run_page()
    at.text_input(key="street").input("main road").run()
    assert not at.exception
    assert len(at.dataframe) >= 2  # top-20 table + street results


def test_app_street_search_ignores_macrons():
    from lib.data import search_street
    df = pd.DataFrame({"street": ["Ōtākaro Avenue", "Hagley Avenue"], "id": [1, 2]})
    assert list(search_street(df, "otakaro").id) == [1]
    assert list(search_street(df, "HAGLEY").id) == [2]
    assert search_street(df, "   ").empty


def test_app_runs_without_secrets():
    at = run_page()
    assert not at.exception
    assert not [b for b in at.button if "👍" in b.label or "👎" in b.label]


def test_app_missing_outputs_shows_message(monkeypatch, tmp_path):
    monkeypatch.setenv("CP_PROJECTS_DIR", str(tmp_path))
    at = run_page()
    assert not at.exception
    assert any("not available" in i.value for i in at.info)


def test_home_lists_pipe_tool():
    at = AppTest.from_file(str(APP / "Home.py"), default_timeout=30).run()
    assert not at.exception
    assert any("pipe" in m.value.lower() for m in at.markdown)
