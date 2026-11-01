import json
import shutil
from pathlib import Path

import pytest

from projects.best_park.pipeline import check

OUT = Path(__file__).parents[1] / "projects" / "best_park" / "outputs"


def test_committed_outputs_pass_check():
    check(OUT)


def _copy(tmp_path):
    dst = tmp_path / "outputs"
    shutil.copytree(OUT, dst)
    return dst, json.loads((dst / "parks.json").read_text(encoding="utf-8"))


def _write(dst, data):
    (dst / "parks.json").write_text(json.dumps(data), encoding="utf-8")


def test_check_rejects_donor_fields(tmp_path):
    dst, data = _copy(tmp_path)
    data["parks"][0]["DonorName"] = "Jane Citizen"
    _write(dst, data)
    with pytest.raises(AssertionError, match="Donor"):
        check(dst)


def test_check_rejects_bad_scores(tmp_path):
    dst, data = _copy(tmp_path)
    data["parks"][0]["score"] = 101
    _write(dst, data)
    with pytest.raises(AssertionError, match="score"):
        check(dst)


def test_check_rejects_duplicate_slugs(tmp_path):
    dst, data = _copy(tmp_path)
    data["parks"][1]["slug"] = data["parks"][0]["slug"]
    _write(dst, data)
    with pytest.raises(AssertionError, match="slug"):
        check(dst)


def test_check_rejects_score_not_reproducible_from_pct(tmp_path):
    dst, data = _copy(tmp_path)
    data["parks"][0]["score"] = round(data["parks"][0]["score"] + 0.1, 1)
    _write(dst, data)
    with pytest.raises(AssertionError, match="reproduc"):
        check(dst)
