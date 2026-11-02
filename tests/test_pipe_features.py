import pandas as pd

from projects.pipe_blockages.profile import profile_report, write_summary


def test_profile_summary_reports_missingness(tmp_path):
    df = pd.DataFrame({"a": [1, 2, None, None], "b": ["x", "y", "x", "z"]})
    s = profile_report(df, "t", tmp_path / "p.html")
    assert s["rows"] == 4 and s["cols"] == 2
    assert s["missing_pct"]["a"] == 50.0 and s["missing_pct"]["b"] == 0.0
    assert s["n_unique"]["b"] == 3
    assert (tmp_path / "p.html").exists()
    out = tmp_path / "summary.md"
    write_summary(s, None, ["H1: something"], False, out)
    text = out.read_text(encoding="utf-8")
    assert "NO-GO" in text and "H1: something" in text and "| a |" in text
