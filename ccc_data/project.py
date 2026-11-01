"""Helpers every project pipeline uses: load its layers, log cleaning, export for the web, write the manifest."""
import json
import subprocess
import tomllib
from pathlib import Path

import geopandas as gpd

from .fetch import fetch
from .layers import resolve

last_sources: list[dict] = []  # filled by load_layers, read by write_manifest


def load_layers(slug: str, *, refresh: bool = False, root: Path = Path("projects")) -> dict[str, gpd.GeoDataFrame]:
    cfg = tomllib.loads((Path(root) / slug / "layers.toml").read_text(encoding="utf-8"))
    last_sources.clear()
    out = {}
    for key, spec in cfg["layers"].items():
        ref = resolve(spec["service"], spec["name"])
        gdf = fetch(ref, exclude_fields=spec.get("exclude", ()), refresh=refresh)
        out[key] = gdf
        last_sources.append({"key": key, "service": ref.service, "name": ref.name, "url": ref.url,
                             "count": len(gdf), "pulled_at": gdf.attrs.get("pulled_at")})
    return out


def log_step(log: list[dict], step: str, rows_in: int, rows_out: int, note: str = "") -> None:
    log.append({"step": step, "rows_in": rows_in, "rows_out": rows_out, "dropped": rows_in - rows_out, "note": note})


def export_web(gdf: gpd.GeoDataFrame, path: Path, *, keep: list[str], max_mb: float = 5.0,
               simplify_m: float | None = None) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    g = gdf[keep + ["geometry"]].copy()
    if simplify_m:
        g["geometry"] = g.geometry.simplify(simplify_m)  # in metres: gdf is EPSG:2193
    g = g.to_crs(4326)
    if path.suffix == ".parquet":
        g.to_parquet(path)
    else:
        path.unlink(missing_ok=True)
        g.to_file(path, driver="GeoJSON")
    mb = path.stat().st_size / 1e6
    if mb > max_mb:
        path.unlink()
        raise ValueError(f"{path.name} is {mb:.2f} MB, over the {max_mb} MB budget; simplify or drop columns")
    return path


def _git_sha() -> str:
    try:
        r = subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True, text=True, check=True)
        return r.stdout.strip()
    except Exception:
        return "uncommitted"


def write_manifest(slug: str, *, outputs: list[Path], transform_log: list[dict],
                   root: Path = Path("projects")) -> Path:
    out_dir = Path(root) / slug / "outputs"
    out_dir.mkdir(parents=True, exist_ok=True)
    pulled = [s["pulled_at"] for s in last_sources if s.get("pulled_at")]
    manifest = {
        "schema_version": 1,
        "data_pulled_at": min(pulled) if pulled else None,
        "sources": list(last_sources),
        "outputs": [Path(o).relative_to(out_dir).as_posix() for o in outputs],
        "git_sha": _git_sha(),
        "transform_log": transform_log,
    }
    p = out_dir / "manifest.json"
    p.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return p
