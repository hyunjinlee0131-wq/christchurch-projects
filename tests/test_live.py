import pytest

from ccc_data.catalog import HUB_ITEMS, catalog
from ccc_data.http import get_json

pytestmark = pytest.mark.live


def test_catalog_live_matches_number_matched():
    matched = get_json(HUB_ITEMS, {"limit": 1})["numberMatched"]
    feats = catalog()
    ids = [f["id"] for f in feats]
    assert len(ids) == len(set(ids)) == matched


def test_fetch_live_dog_exercise_area(tmp_path):
    from ccc_data.fetch import fetch
    from ccc_data.layers import resolve

    ref = resolve("Recreation", "Dog Exercise Area")
    expected = get_json(f"{ref.url}/query", {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    gdf = fetch(ref, page_size=4, cache_dir=tmp_path, refresh=True)
    assert len(gdf) == expected > 4  # forces >1 page
    assert gdf.crs.to_epsg() == 2193
    assert gdf.geometry.is_valid.all()
    xmin, ymin, xmax, ymax = gdf.total_bounds
    assert 1_540_000 < xmin and xmax < 1_620_000  # inside Christchurch, NZTM metres
