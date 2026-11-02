import json
import shutil
from pathlib import Path

import pandas as pd
import pytest

from projects.pipe_blockages.pipeline import check

OUT = Path(__file__).parents[1] / "projects" / "pipe_blockages" / "outputs"


def test_committed_outputs_pass_check():
    check(OUT)


def _copy(tmp_path):
    dst = tmp_path / "outputs"
    shutil.copytree(OUT, dst)
    return dst


def test_check_rejects_safe_wording(tmp_path):
    dst = _copy(tmp_path)
    df = pd.read_parquet(dst / "pipes.parquet")
    df.loc[df.index[0], "reason"] = "This pipe is safe"
    df.to_parquet(dst / "pipes.parquet")
    with pytest.raises(AssertionError, match="safe"):
        check(dst)


def test_check_rejects_blockage_total_mismatch(tmp_path):
    dst = _copy(tmp_path)
    m = json.loads((dst / "metrics.json").read_text(encoding="utf-8"))
    m["total_blockages"] += 1
    (dst / "metrics.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(AssertionError, match="blockages"):
        check(dst)


def test_check_rejects_headline_that_contradicts_ci(tmp_path):
    dst = _copy(tmp_path)
    m = json.loads((dst / "metrics.json").read_text(encoding="utf-8"))
    m["tree_effect"]["ci"] = [1.05, 1.20]
    m["tree_effect"]["irr_per_tree_5m"] = 1.1
    (dst / "metrics.json").write_text(json.dumps(m), encoding="utf-8")
    with pytest.raises(AssertionError, match="headline"):
        check(dst)
