import pytest

from ccc_data import layers
from ccc_data.layers import AmbiguousLayer, LayerNotFound, normalise, resolve

BASE = "https://gis.ccc.govt.nz/server/rest/services/OpenData"


@pytest.fixture(autouse=True)
def clear_listing_cache():
    layers._listings.clear()


def wc_server(fake_server):
    return fake_server({
        f"{BASE}/WaterCharacteristic/FeatureServer": {"layers": [
            {"id": 22, "name": "RiverUrbanImpact"}, {"id": 29, "name": "FishObstruction"},
            {"id": 6, "name": "WalkingMountainBikeRoute"}], "tables": []},
        f"{BASE}/WaterCharacteristic/FeatureServer/22": {
            "name": "RiverUrbanImpact", "objectIdField": "RiverUrbanImpactID", "maxRecordCount": 2000,
            "geometryType": "esriGeometryPolygon",
            "fields": [{"name": "RiverUrbanImpactID"}, {"name": "Score"}]},
    })


def test_normalise():
    assert normalise("On-Street Parking Casual") == normalise("OnStreetParkingCasual") == "onstreetparkingcasual"


def test_resolve_normalises_names(fake_server):
    wc_server(fake_server)
    ref = resolve("WaterCharacteristic", "River Urban Impact")
    assert ref.layer_id == 22 and ref.object_id_field == "RiverUrbanImpactID"
    assert ref.url == f"{BASE}/WaterCharacteristic/FeatureServer/22"
    assert ref.has_geometry is True and ref.max_record_count == 2000
    assert ref.fields == ("RiverUrbanImpactID", "Score") and ref.name == "RiverUrbanImpact"


def test_resolve_missing_suggests_nearest(fake_server):
    wc_server(fake_server)
    with pytest.raises(LayerNotFound, match="WalkingMountainBikeRoute"):
        resolve("WaterCharacteristic", "Walking Track")


def test_resolve_ambiguous_raises(fake_server):
    fake_server({f"{BASE}/Electoral/FeatureServer": {"layers": [{"id": 0, "name": "Ward"}, {"id": 1, "name": "WARD"}], "tables": []}})
    with pytest.raises(AmbiguousLayer):
        resolve("Electoral", "Ward")


def test_resolve_searches_tables_too(fake_server):
    fake_server({
        f"{BASE}/Property/FeatureServer": {"layers": [], "tables": [{"id": 20, "name": "RevaluationValuationRoll"}]},
        f"{BASE}/Property/FeatureServer/20": {"objectIdField": "OBJECTID", "maxRecordCount": 2000, "fields": [{"name": "OBJECTID"}]},
    })
    assert resolve("Property", "Revaluation Valuation Roll").has_geometry is False


def test_resolve_caches_service_listing(fake_server):
    wc_server(fake_server)
    resolve("WaterCharacteristic", "River Urban Impact")
    resolve("WaterCharacteristic", "River Urban Impact")
    assert sum(u.endswith("/FeatureServer?f=json") for u in fake_server.calls) == 1
