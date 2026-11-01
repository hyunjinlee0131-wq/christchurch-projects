"""Download a layer in pages, verify it against the server's count, cache and log it."""
import hashlib
import json
import os
from collections.abc import Iterable
from datetime import datetime, timedelta, timezone
from pathlib import Path

import geopandas as gpd
import pandas as pd

from .http import get_json
from .layers import LayerRef, normalise

CRS = 2193  # NZTM2000, metres


class CountMismatch(Exception):
    pass


class SchemaDrift(Exception):
    pass


def cache_path(ref: LayerRef, cache_dir: Path) -> Path:
    return Path(cache_dir) / f"{ref.service}__{normalise(ref.name)}.parquet"


def _meta_path(path: Path) -> Path:
    return path.with_suffix(".meta.json")


def _fields_hash(fields: Iterable[str]) -> str:
    return hashlib.sha256(",".join(sorted(fields)).encode()).hexdigest()[:16]


def _read_cache(path: Path, max_age_days: int) -> tuple[gpd.GeoDataFrame, dict] | None:
    try:
        meta = json.loads(_meta_path(path).read_text(encoding="utf-8"))
        if datetime.now(timezone.utc) - datetime.fromisoformat(meta["pulled_at"]) > timedelta(days=max_age_days):
            return None
        return gpd.read_parquet(path), meta
    except Exception:  # missing, stale-format or corrupt cache -> refetch
        return None


def _download(ref: LayerRef, out_fields: str, page_size: int) -> gpd.GeoDataFrame:
    query = f"{ref.url}/query"
    count = get_json(query, {"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"]
    fmt = "geojson" if ref.has_geometry else "json"
    feats: list[dict] = []
    for offset in range(0, count, page_size):
        page = get_json(query, {"where": "1=1", "outFields": out_fields, "orderByFields": ref.object_id_field,
                                "resultOffset": offset, "resultRecordCount": page_size, "f": fmt})
        feats += page.get("features") or []
    if len(feats) != count:
        raise CountMismatch(f"{ref.service}/{ref.name}: server count {count}, fetched {len(feats)}")
    if ref.has_geometry:
        if not feats:
            return gpd.GeoDataFrame(geometry=[], crs=CRS)
        return gpd.GeoDataFrame.from_features(feats, crs=4326).to_crs(CRS)
    df = pd.DataFrame([f["attributes"] for f in feats])
    return gpd.GeoDataFrame(df, geometry=[None] * len(df), crs=CRS)


def fetch(ref: LayerRef, *, exclude_fields: Iterable[str] = (), refresh: bool = False, max_age_days: int = 35,
          page_size: int | None = None, cache_dir: Path = Path("data/raw"),
          accept_schema_change: bool = False) -> gpd.GeoDataFrame:
    cache_dir = Path(cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    path = cache_path(ref, cache_dir)
    fields_hash = _fields_hash(ref.fields)

    cached = None if refresh else _read_cache(path, max_age_days)
    if cached is not None and cached[1].get("fields_hash") == fields_hash:
        gdf, meta = cached
        _log(cache_dir, ref, len(gdf), path, meta["pulled_at"], fields_hash, from_cache=True)
        gdf.attrs["pulled_at"] = meta["pulled_at"]
        return gdf

    try:
        old = json.loads(_meta_path(path).read_text(encoding="utf-8"))
    except Exception:
        old = None
    if old and old.get("fields_hash") != fields_hash and not accept_schema_change:
        raise SchemaDrift(f"{ref.service}/{ref.name}: fields changed since last pull; "
                          f"check the pipeline, then pass accept_schema_change=True")

    exclude = set(exclude_fields)
    out_fields = ",".join(f for f in ref.fields if f not in exclude) if exclude else "*"
    gdf = _download(ref, out_fields, page_size or ref.max_record_count)

    pulled_at = datetime.now(timezone.utc).isoformat()
    tmp = path.with_suffix(".parquet.tmp")
    gdf.to_parquet(tmp)
    os.replace(tmp, path)  # atomic: a failed run never leaves a half-written cache
    _meta_path(path).write_text(json.dumps({"pulled_at": pulled_at, "count": len(gdf), "fields_hash": fields_hash,
                                            "url": ref.url}), encoding="utf-8")
    _log(cache_dir, ref, len(gdf), path, pulled_at, fields_hash, from_cache=False)
    gdf.attrs["pulled_at"] = pulled_at
    return gdf


def _log(cache_dir: Path, ref: LayerRef, count: int, path: Path, pulled_at: str, fields_hash: str, *, from_cache: bool):
    line = {"url": ref.url, "service": ref.service, "name": ref.name, "count": count, "bytes": path.stat().st_size,
            "pulled_at": pulled_at, "fields_hash": fields_hash, "from_cache": from_cache}
    with open(cache_dir / "_fetch_log.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(line) + "\n")
