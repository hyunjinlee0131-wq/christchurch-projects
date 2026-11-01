import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone
from urllib.error import URLError
from urllib.parse import parse_qs, urlsplit

import pytest

from ccc_data.fetch import CountMismatch, SchemaDrift, cache_path, fetch
from ccc_data.layers import LayerRef

REF = LayerRef(service="Svc", name="Thing", layer_id=0, url="https://x/Svc/FeatureServer/0",
               object_id_field="OID", max_record_count=2000, has_geometry=True,
               fields=("OID", "Label", "OwnerName"))
TABLE = replace(REF, name="Tbl", has_geometry=False)


def layer_server(fake_server, *, n=5, served=None, fail_after=None):
    """Serve n rows (or `served` rows while claiming n) from REF's /query, paged by `OID > last` (keyset)."""
    rows = [{"OID": i, "Label": f"r{i}", "OwnerName": "secret"} for i in range(served if served is not None else n)]

    def query(url):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        if q.get("returnCountOnly") == "true":
            return {"count": n}
        assert "resultOffset" not in q, "keyset paging must not use resultOffset"
        last = int(q["where"].split(">")[1]) if ">" in q["where"] else -1
        if fail_after is not None and last >= fail_after:
            raise URLError("down")
        keep = None if q["outFields"] == "*" else q["outFields"].split(",")
        chunk = [r for r in rows if r["OID"] > last][: int(q["resultRecordCount"])]
        chunk = [{k: v for k, v in r.items() if keep is None or k in keep} for r in chunk]
        if q["f"] == "geojson":
            return {"type": "FeatureCollection", "features": [
                {"type": "Feature", "geometry": {"type": "Point", "coordinates": [172.63 + r["OID"] / 1000, -43.53]}, "properties": r}
                for r in chunk]}
        return {"features": [{"attributes": r} for r in chunk]}

    fake_server({f"{REF.url}/query": query})
    return fake_server


def page_calls(server):
    return [u for u in server.calls if "resultRecordCount" in u]


def test_fetch_pages_and_verifies_count(fake_server, tmp_path):
    s = layer_server(fake_server)
    gdf = fetch(REF, page_size=2, cache_dir=tmp_path)
    assert len(gdf) == 5 and gdf.crs.to_epsg() == 2193
    assert list(gdf["OID"]) == [0, 1, 2, 3, 4]
    assert len(page_calls(s)) == 3
    assert all("orderByFields=OID" in u for u in page_calls(s))
    assert [parse_qs(urlsplit(u).query)["where"][0] for u in page_calls(s)] == ["1=1", "OID > 1", "OID > 3"]
    assert 1_560_000 < gdf.geometry.x.min() < 1_580_000  # reprojected to NZTM metres


def test_fetch_count_mismatch_raises(fake_server, tmp_path):
    layer_server(fake_server, n=5, served=4)
    with pytest.raises(CountMismatch):
        fetch(REF, page_size=2, cache_dir=tmp_path)
    assert not cache_path(REF, tmp_path).exists()


def test_fetch_failure_leaves_no_cache(fake_server, tmp_path):
    layer_server(fake_server, fail_after=1)
    with pytest.raises(URLError):
        fetch(REF, page_size=2, cache_dir=tmp_path)
    assert not cache_path(REF, tmp_path).exists()
    assert not list(tmp_path.glob("*.tmp"))


def test_fetch_uses_cache_then_refetches_stale_cache(fake_server, tmp_path):
    s = layer_server(fake_server)
    fetch(REF, cache_dir=tmp_path)
    n_calls = len(s.calls)
    assert len(fetch(REF, cache_dir=tmp_path)) == 5
    assert len(s.calls) == n_calls  # served from cache
    meta = cache_path(REF, tmp_path).with_suffix(".meta.json")
    m = json.loads(meta.read_text(encoding="utf-8"))
    m["pulled_at"] = (datetime.now(timezone.utc) - timedelta(days=40)).isoformat()
    meta.write_text(json.dumps(m), encoding="utf-8")
    fetch(REF, cache_dir=tmp_path)
    assert len(s.calls) > n_calls


def test_fetch_refresh_bypasses_cache(fake_server, tmp_path):
    s = layer_server(fake_server)
    fetch(REF, cache_dir=tmp_path)
    n_calls = len(s.calls)
    fetch(REF, cache_dir=tmp_path, refresh=True)
    assert len(s.calls) > n_calls


def test_fetch_refetches_corrupt_cache(fake_server, tmp_path):
    layer_server(fake_server)
    fetch(REF, cache_dir=tmp_path)
    cache_path(REF, tmp_path).write_bytes(b"not parquet")
    assert len(fetch(REF, cache_dir=tmp_path)) == 5


def test_fetch_excludes_fields_at_request(fake_server, tmp_path):
    s = layer_server(fake_server)
    gdf = fetch(REF, exclude_fields=["OwnerName"], cache_dir=tmp_path)
    assert all("OwnerName" not in u for u in page_calls(s))
    assert "outFields=OID%2CLabel" in page_calls(s)[0]
    assert "OwnerName" not in gdf.columns


def test_fetch_schema_drift_raises(fake_server, tmp_path):
    layer_server(fake_server)
    fetch(REF, cache_dir=tmp_path)
    drifted = replace(REF, fields=REF.fields + ("NewField",))
    with pytest.raises(SchemaDrift):
        fetch(drifted, cache_dir=tmp_path, refresh=True)
    assert len(fetch(drifted, cache_dir=tmp_path, refresh=True, accept_schema_change=True)) == 5


def test_fetch_table_without_geometry(fake_server, tmp_path):
    layer_server(fake_server)
    gdf = fetch(TABLE, cache_dir=tmp_path)
    assert len(gdf) == 5 and gdf.geometry.isna().all() and gdf.crs.to_epsg() == 2193
    assert len(fetch(TABLE, cache_dir=tmp_path)) == 5  # round-trips through the cache


def test_fetch_empty_layer(fake_server, tmp_path):
    layer_server(fake_server, n=0)
    gdf = fetch(REF, cache_dir=tmp_path)
    assert len(gdf) == 0 and gdf.crs.to_epsg() == 2193


def test_fetch_writes_fetch_log(fake_server, tmp_path):
    layer_server(fake_server)
    fetch(REF, cache_dir=tmp_path)
    fetch(REF, cache_dir=tmp_path)
    lines = [json.loads(l) for l in (tmp_path / "_fetch_log.jsonl").read_text(encoding="utf-8").splitlines()]
    assert [(l["count"], l["from_cache"]) for l in lines] == [(5, False), (5, True)]
    assert {"url", "service", "name", "bytes", "pulled_at", "fields_hash"} <= set(lines[0])


def test_fetch_sets_pulled_at_attr(fake_server, tmp_path):
    layer_server(fake_server)
    first = fetch(REF, cache_dir=tmp_path).attrs["pulled_at"]
    assert first and fetch(REF, cache_dir=tmp_path).attrs["pulled_at"] == first


def test_cache_never_leaks_excluded_fields(fake_server, tmp_path):
    layer_server(fake_server)
    assert "OwnerName" in fetch(REF, cache_dir=tmp_path).columns  # someone fetched it unfiltered
    assert "OwnerName" not in fetch(REF, exclude_fields=["OwnerName"], cache_dir=tmp_path).columns
    assert "OwnerName" in fetch(REF, cache_dir=tmp_path).columns  # and the reverse


def test_fetch_rejects_duplicate_rows(fake_server, tmp_path):
    # server ignores resultOffset (no pagination support): every page is rows 0..1
    def query(url):
        if "returnCountOnly=true" in url:
            return {"count": 4}
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [172.6, -43.5]}, "properties": {"OID": i}}
            for i in (0, 1)]}
    fake_server({f"{REF.url}/query": query})
    with pytest.raises(CountMismatch, match="duplicate"):
        fetch(REF, page_size=2, cache_dir=tmp_path)


def test_fetch_follows_rows_actually_returned(fake_server, tmp_path):
    # server caps every page at 2 rows even though 3 were requested
    rows = list(range(5))
    def query(url):
        q = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        if q.get("returnCountOnly") == "true":
            return {"count": 5}
        last = int(q["where"].split(">")[1]) if ">" in q["where"] else -1
        return {"type": "FeatureCollection", "features": [
            {"type": "Feature", "geometry": {"type": "Point", "coordinates": [172.6, -43.5]}, "properties": {"OID": i}}
            for i in [r for r in rows if r > last][:2]]}
    fake_server({f"{REF.url}/query": query})
    assert sorted(fetch(REF, page_size=3, cache_dir=tmp_path)["OID"]) == rows


def test_fetch_clamps_page_size_to_server_max(fake_server, tmp_path):
    s = layer_server(fake_server)
    fetch(replace(REF, max_record_count=2), page_size=1000, cache_dir=tmp_path)
    assert all("resultRecordCount=2&" in u for u in page_calls(s))


def test_fetch_requests_only_listed_fields_plus_oid(fake_server, tmp_path):
    s = layer_server(fake_server)
    gdf = fetch(REF, fields=["Label"], cache_dir=tmp_path)
    assert all("outFields=OID%2CLabel&" in u for u in page_calls(s))
    assert set(gdf.columns) == {"OID", "Label", "geometry"}


def test_fetch_field_selection_has_its_own_cache(fake_server, tmp_path):
    layer_server(fake_server)
    assert "Label" not in fetch(REF, fields=[], cache_dir=tmp_path).columns
    assert "Label" in fetch(REF, cache_dir=tmp_path).columns
