import geopandas as gpd
import pandas as pd
import pytest
from shapely.geometry import Point, box

from projects.best_park.score import (WEIGHTS, percentiles, raw_factors, score, select_parks,
                                      slugify_unique)

X, Y = 1_570_000, 5_180_000
PARKS = gpd.GeoDataFrame({
    "ParkID": ["A", "B", "C"], "ParkName": ["Alpha", "Beta", "Gamma"],
    "Type": ["Local/Community Park", "Local/Community Park", "Utility Park"],
    "drvArea": [10_000.0, 500.0, 20_000.0],
}, geometry=[box(X, Y, X + 100, Y + 100), box(X + 500, Y, X + 520, Y + 25), box(X + 1000, Y, X + 1200, Y + 100)], crs=2193)


def pts(coords):
    return gpd.GeoDataFrame(geometry=[Point(c) for c in coords], crs=2193)


EMPTY = gpd.GeoDataFrame(geometry=[], crs=2193)
LAYERS = {k: EMPTY for k in ["seat", "picnic_table", "bbq", "shower", "drinking_fountain", "sport_field", "tree"]}
LAYERS |= {
    # 3 inside A, 1 at 15 m outside A (counted, BUFFER_M=20), 1 at 50 m (not counted)
    "play_equipment": pts([(X + 10, Y + 10), (X + 50, Y + 50), (X + 90, Y + 90), (X + 115, Y + 50), (X + 150, Y + 50)]),
    "dog_exercise_area": gpd.GeoDataFrame(geometry=[box(X + 80, Y + 80, X + 140, Y + 140)], crs=2193),
}


def test_select_parks_filters_type_and_area():
    log = []
    out = select_parks(PARKS, log)
    assert list(out.ParkID) == ["A"] and [s["dropped"] for s in log] == [1, 1]


def test_raw_factors_counts_within_buffer():
    raw = raw_factors(select_parks(PARKS, []), LAYERS)
    assert raw.loc["A", "play"] == 4 and raw.loc["A", "dogs"] == 1.0
    assert raw.loc["A", "size"] == pytest.approx(1.0) and raw.loc["A", "seating"] == 0
    assert list(raw.columns) == list(WEIGHTS)


def test_trees_density_capped():
    layers = LAYERS | {"tree": pts([(X + 1 + i % 98, Y + 1 + i // 98 % 98) for i in range(500)])}
    assert raw_factors(select_parks(PARKS, []), layers).loc["A", "trees"] == 200.0


def test_percentiles_all_zero_column_is_zero():
    pct = percentiles(pd.DataFrame({"play": [0, 0, 0], "size": [1.0, 2.0, 3.0]}))
    assert list(pct["play"]) == [0.0, 0.0, 0.0]
    assert list(pct["size"]) == pytest.approx([1 / 3, 2 / 3, 1.0])


def test_score_weighted_mean_0_to_100():
    pct = pd.DataFrame({"play": [1.0, 0.5], "size": [0.0, 1.0]})
    assert list(score(pct, {"play": 3, "size": 1})) == [75.0, 62.5]


def test_score_zero_weights_falls_back_to_defaults():
    pct = pd.DataFrame({k: [1.0] for k in WEIGHTS})
    assert list(score(pct, {k: 0 for k in WEIGHTS})) == [100.0]


def test_slugify_unique_handles_collisions_and_macrons():
    assert slugify_unique(["Ōtākaro Park", "Hagley Park", "Hagley Park", "St. Albans' / Edgeware", "!!!"]) == \
        ["otakaro-park", "hagley-park", "hagley-park-2", "st-albans-edgeware", "park"]


def test_percentiles_zero_means_none_not_tied_rank():
    pct = percentiles(pd.DataFrame({"bbq": [0, 0, 5]}))
    assert list(pct["bbq"]) == [0.0, 0.0, 1.0]


def test_slugify_unique_never_reuses_an_existing_suffixed_slug():
    # real data has a park literally named "Owaka Reserve 2"; a duplicate "Owaka Reserve" must not collide with it
    slugs = slugify_unique(["Owaka Reserve 2", "Owaka Reserve", "Owaka Reserve"])
    assert len(set(slugs)) == 3 and slugs[0] == "owaka-reserve-2"


def test_slugify_strips_curly_apostrophes_like_straight_ones():
    assert slugify_unique(["St Paul’s Park"]) == slugify_unique(["St Paul's Park"]) == ["st-pauls-park"]
