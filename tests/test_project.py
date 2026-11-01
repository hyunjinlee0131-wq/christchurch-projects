import json
from pathlib import Path

import geopandas as gpd
import pytest
from shapely.geometry import Point

from ccc_data import project
from ccc_data.layers import LayerRef

FIXTURES = Path(__file__).parent / "fixtures" / "projects"


def gdf2193(n=3):
    return gpd.GeoDataFrame({"name": [f"p{i}" for i in range(n)], "extra": range(n)},
                            geometry=[Point(1_570_000 + i * 10, 5_180_000) for i in range(n)], crs=2193)


@pytest.fixture
def fakes(monkeypatch):
    calls = []

    def fake_resolve(service, name):
        return LayerRef(service, name, 0, f"https://x/{service}/FeatureServer/0", "OID", 2000, True, ("OID",))

    def fake_fetch(ref, *, exclude_fields=(), refresh=False, **kw):
        calls.append((ref.name, tuple(exclude_fields), refresh))
        g = gdf2193()
        g.attrs["pulled_at"] = "2026-11-0%dT00:00:00+00:00" % (1 if ref.name == "Park" else 2)
        return g

    monkeypatch.setattr(project, "resolve", fake_resolve)
    monkeypatch.setattr(project, "fetch", fake_fetch)
    return calls


def test_load_layers_reads_toml_and_records_sources(fakes):
    layers = project.load_layers("_example", root=FIXTURES)
    assert set(layers) == {"park", "seat"}
    assert fakes == [("Park", ("OwnerName",), False), ("Seat", (), False)]
    src = {s["key"]: s for s in project.last_sources}
    assert src["park"]["count"] == 3 and src["park"]["service"] == "GreenAsset"
    assert src["park"]["pulled_at"].startswith("2026-11-01")


def test_log_step_records_drops():
    log = []
    project.log_step(log, "drop tiny parks", 10, 7, "area < 500 m2")
    assert log == [{"step": "drop tiny parks", "rows_in": 10, "rows_out": 7, "dropped": 3, "note": "area < 500 m2"}]


def test_export_web_reprojects_and_slims(tmp_path):
    out = project.export_web(gdf2193(), tmp_path / "x.geojson", keep=["name"])
    back = gpd.read_file(out)
    assert back.crs.to_epsg() == 4326 and list(back.columns) == ["name", "geometry"]
    assert 172 < back.geometry.x.min() < 173


def test_export_web_parquet(tmp_path):
    out = project.export_web(gdf2193(), tmp_path / "x.parquet", keep=["name"])
    assert gpd.read_parquet(out).crs.to_epsg() == 4326


def test_export_web_enforces_size_budget(tmp_path):
    with pytest.raises(ValueError, match="MB"):
        project.export_web(gdf2193(500), tmp_path / "x.geojson", keep=["name"], max_mb=0.001)
    assert not (tmp_path / "x.geojson").exists()


def test_write_manifest_has_provenance(tmp_path, fakes):
    project.load_layers("_example", root=FIXTURES)
    out = tmp_path / "_example" / "outputs" / "a.geojson"
    p = project.write_manifest("_example", outputs=[out], transform_log=[{"step": "s"}], root=tmp_path)
    m = json.loads(p.read_text(encoding="utf-8"))
    assert p == tmp_path / "_example" / "outputs" / "manifest.json"
    assert m["schema_version"] == 1
    assert m["data_pulled_at"].startswith("2026-11-01")  # oldest source
    assert len(m["sources"]) == 2 and m["outputs"] == ["a.geojson"]
    assert m["git_sha"] and m["transform_log"] == [{"step": "s"}]


def test_load_layers_passes_fields(tmp_path, monkeypatch, fakes):
    (tmp_path / "p").mkdir()
    (tmp_path / "p" / "layers.toml").write_text('[layers.tree]\nservice = "Tree"\nname = "Tree"\nfields = []\n', encoding="utf-8")
    seen = {}
    real = project.fetch
    monkeypatch.setattr(project, "fetch", lambda ref, **kw: seen.update(kw) or real(ref, **kw))
    project.load_layers("p", root=tmp_path)
    assert seen["fields"] == []
