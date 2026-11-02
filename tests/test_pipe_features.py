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


# ---- Task 2: cleaning and features (synthetic data, EPSG:2193) ----
from datetime import date

import geopandas as gpd
import pytest
from shapely.geometry import LineString, Point

from projects.pipe_blockages.features import (MATERIAL_GROUPS, grid_cell, join_blockages, pipe_features,
                                              select_population, street_names, tree_features)

X, Y = 1_570_000, 5_180_000
MS_1980 = 315_532_800_000.0  # 1980-01-01 in epoch ms


def pipes(rows):
    base = {"Type": "Gravity", "ServiceStatus": "In Service", "Ownership": "CCC", "Construction": "UPVC",
            "NominalDiameter": 150.0, "CommissionDate": MS_1980, "Depth": 1.5, "Grade": 0.01, "Treatment": None,
            "drvLength": 100.0}
    recs = [base | r for r in rows]
    geoms = [LineString([(X, Y + 50 * i), (X + r.get("drvLength", 100.0), Y + 50 * i)]) for i, r in enumerate(recs)]
    for i, r in enumerate(recs):
        r.setdefault("WwPipeID", i + 1)
    return gpd.GeoDataFrame(recs, geometry=geoms, crs=2193)


def test_select_population_filters_type_status_owner_length():
    p = pipes([{}, {"Type": "Pressure"}, {"ServiceStatus": "Abandoned"}, {"Ownership": "Private"},
               {"drvLength": 0.5}, {"Type": "Gravity Collector"}])
    log = []
    out = select_population(p, log)
    assert sorted(out.WwPipeID) == [1, 6]
    assert sum(s["dropped"] for s in log) == 4


def test_join_reports_unmatched_blockage_ids():
    p = pipes([{}, {}])
    b = gpd.GeoDataFrame({"WwPipeID": [1, 999], "NumberOfBlockages": [3, 5]}, geometry=[None, None], crs=2193)
    log = []
    out = join_blockages(p, b, log)
    assert list(out.sort_values("WwPipeID").blockages) == [3, 0]
    assert out.attrs["unmatched_blockage_ids"] == [999]
    assert any("unmatched" in s["step"] for s in log)


def test_features_keep_pipes_with_missing_attributes():
    p = pipes([{}, {"CommissionDate": None, "Construction": None, "Depth": None, "Grade": None, "NominalDiameter": None}])
    out = pipe_features(p, as_of=date(2026, 1, 1))
    assert len(out) == 2
    r = out.iloc[1]
    assert r.material == "Unknown" and bool(r.age_missing) and bool(r.depth_missing) and bool(r.grade_missing)
    assert bool(r.diameter_missing) and r.age_years > 0 and r.depth_m > 0
    assert out.iloc[0].age_years == pytest.approx(46.0, abs=0.1)


def test_features_drop_degenerate_lengths():
    p = pipes([{}, {"drvLength": 0.0}, {"drvLength": 0.4}])
    log = []
    assert len(select_population(p, log)) == 1


def test_material_groups_cover_known_codes():
    assert MATERIAL_GROUPS["EW"] == MATERIAL_GROUPS["VC"] == "Earthenware"
    assert MATERIAL_GROUPS["RCRR"] == "Concrete" and MATERIAL_GROUPS["UPVC"] == "Plastic"
    out = pipe_features(pipes([{"Construction": "SOMETHINGNEW"}]), as_of=date(2026, 1, 1))
    assert out.iloc[0].material == "Other"


def test_relined_flag():
    out = pipe_features(pipes([{}, {"Treatment": "CIPP"}]), as_of=date(2026, 1, 1))
    assert list(out.relined) == [False, True]


def test_tree_features_counts_within_radius():
    p = pipes([{}])  # pipe along y=Y from X to X+100
    trees = gpd.GeoDataFrame({"Genus": ["Quercus", "Prunus", "Salix"], "CrownSpread": [4.0, None, 6.0]},
                             geometry=[Point(X + 50, Y + 3), Point(X + 50, Y + 7), Point(X + 50, Y + 15)], crs=2193)
    out = tree_features(p, trees)
    r = out.iloc[0]
    assert (r.trees_5m, r.trees_10m) == (1, 2)
    assert r.crown_sum_10m == 4.0
    assert r.trees_per_100m_10m == pytest.approx(2.0)


def test_aggressive_trees_counted_by_genus():
    p = pipes([{}])
    trees = gpd.GeoDataFrame({"Genus": ["Salix", "Prunus", "Populus"], "CrownSpread": [1.0, 1.0, 1.0]},
                             geometry=[Point(X + 10, Y + 2), Point(X + 20, Y + 2), Point(X + 30, Y + 8)], crs=2193)
    assert tree_features(p, trees).iloc[0].aggressive_trees_10m == 2


def test_street_names_nearest_within_max():
    p = pipes([{}, {}])  # second pipe 50 m north
    streets = gpd.GeoDataFrame({"FullRoadName": ["Near Street", "Far Road"]},
                               geometry=[LineString([(X, Y - 10), (X + 100, Y - 10)]),
                                         LineString([(X, Y + 500), (X + 100, Y + 500)])], crs=2193)
    assert list(street_names(p, streets, max_m=40.0)) == ["Near Street", ""]


def test_grid_cell_groups_by_km():
    p = pipes([{}, {}])
    cells = grid_cell(p)
    assert cells.iloc[0] == cells.iloc[1] == f"{(X + 50) // 1000}_{Y // 1000}"
