import pytest

from ccc_data.catalog import HUB_ITEMS, catalog
from ccc_data.http import get_json

pytestmark = pytest.mark.live


def test_catalog_live_matches_number_matched():
    matched = get_json(HUB_ITEMS, {"limit": 1})["numberMatched"]
    feats = catalog()
    ids = [f["id"] for f in feats]
    assert len(ids) == len(set(ids)) == matched
