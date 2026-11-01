"""Best Park pipeline: CCC layers -> park scores -> web outputs. Run: python -m projects.best_park.pipeline [--refresh]"""
import json
import math
import re
import sys
from pathlib import Path

from ccc_data import export_web, load_layers, project, write_manifest

from .score import FACTORS, WEIGHTS, percentiles, raw_factors, score, select_parks, slugify_unique

SLUG = "best_park"
MAX_MB = 5.0


def run(*, refresh: bool = False, root: Path = Path("projects")) -> Path:
    out_dir = Path(root) / SLUG / "outputs"
    layers = load_layers(SLUG, refresh=refresh, root=root)
    log: list[dict] = []
    parks = select_parks(layers["park"], log).sort_values("ParkID").reset_index(drop=True)
    parks["slug"] = slugify_unique(parks["ParkName"].tolist())

    raw = raw_factors(parks, layers)
    # Score from exactly the floats we publish (Python round, as in the records below), so the site reproduces it.
    pct = percentiles(raw).map(lambda v: round(float(v), 3))
    parks = parks.set_index("ParkID")
    parks["score"] = score(pct, WEIGHTS)
    parks["area_ha"] = raw["size"]
    parks = parks.sort_values(["score", "area_ha", "ParkName"], ascending=[False, False, True])
    parks["rank"] = range(1, len(parks) + 1)

    pts = parks.geometry.representative_point().to_crs(4326)
    pulled = min(s["pulled_at"] for s in project.last_sources if s.get("pulled_at"))
    records = [{
        "id": str(pid), "slug": r.slug, "name": r.ParkName, "type": r.Type, "area_ha": round(float(r.area_ha), 3),
        "lon": round(pts[pid].x, 5), "lat": round(pts[pid].y, 5),
        "raw": {k: round(float(raw.loc[pid, k]), 3) for k in WEIGHTS},
        "pct": {k: round(float(pct.loc[pid, k]), 3) for k in WEIGHTS},
        "score": float(r.score), "rank": int(r["rank"]),
    } for pid, r in parks.iterrows()]

    out_dir.mkdir(parents=True, exist_ok=True)
    data = {"schema_version": 1, "data_pulled_at": pulled, "weights": WEIGHTS,
            "factors": [{"key": k, "label": label} for k, label in FACTORS], "parks": records}
    parks_json = out_dir / "parks.json"
    parks_json.write_text(json.dumps(data, ensure_ascii=False, separators=(",", ":")), encoding="utf-8", newline="\n")

    geo = parks.reset_index().rename(columns={"ParkID": "id", "ParkName": "name"})
    geo["id"] = geo["id"].astype(str)
    geojson = export_web(geo, out_dir / "parks.geojson", keep=["id", "slug", "name", "score", "rank"],
                         simplify_m=2.0, max_mb=MAX_MB)

    metrics = out_dir / "metrics.json"
    metrics.write_text(json.dumps({"n_parks": len(records), "top5": [p["name"] for p in records[:5]],
                                   "data_pulled_at": pulled}, ensure_ascii=False, indent=2) + "\n",
                       encoding="utf-8", newline="\n")
    write_manifest(SLUG, outputs=[parks_json, geojson, metrics], transform_log=log, root=root)
    return out_dir


def check(out_dir: Path = Path("projects/best_park/outputs")) -> None:
    out_dir = Path(out_dir)
    files = ["parks.json", "parks.geojson", "metrics.json", "manifest.json"]
    for f in files:
        p = out_dir / f
        assert p.exists(), f"missing {p}"
        text = p.read_text(encoding="utf-8")
        assert "DonorName" not in text and "DonatedBy" not in text, f"Donor fields leaked into {f}"
        assert p.stat().st_size <= MAX_MB * 1e6, f"{f} over {MAX_MB} MB"
    data = json.loads((out_dir / "parks.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1, "schema_version"
    parks = data["parks"]
    assert len(parks) >= 300, f"only {len(parks)} parks"
    assert [p["rank"] for p in parks] == list(range(1, len(parks) + 1)), "ranks not 1..n in order"
    slugs = [p["slug"] for p in parks]
    assert len(set(slugs)) == len(slugs), "duplicate slug"
    assert all(re.fullmatch(r"[a-z0-9-]+", s) for s in slugs), "bad slug characters"
    for p in parks:
        assert 0 <= p["score"] <= 100, f"score out of range for {p['name']}: {p['score']}"
        assert all(0 <= v <= 1 for v in p["pct"].values()), f"pct out of range for {p['name']}"
        w = data["weights"]
        acc = 0.0
        for k in w:  # plain left-to-right addition, like score() and scoring.ts (builtin sum() compensates)
            acc += p["pct"][k] * w[k]
        again = math.floor(1000 * acc / sum(w.values()) + 0.5) / 10
        assert abs(again - p["score"]) < 1e-9, f"score for {p['name']} not reproducible from published pct ({again} vs {p['score']})"
        assert 172.3 <= p["lon"] <= 173.2 and -43.95 <= p["lat"] <= -43.35, f"{p['name']} outside Christchurch"


if __name__ == "__main__":
    out = run(refresh="--refresh" in sys.argv)
    check(out)
    top = json.loads((out / "parks.json").read_text(encoding="utf-8"))["parks"]
    print(f"best_park: {len(top)} parks, #1 {top[0]['name']} ({top[0]['score']})")
