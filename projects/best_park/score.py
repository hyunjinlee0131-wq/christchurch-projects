"""Best Park scoring: pure functions over GeoDataFrames in EPSG:2193."""
import re
import unicodedata

import geopandas as gpd
import numpy as np
import pandas as pd

from ccc_data import log_step

INCLUDED_TYPES = {"Local/Community Park", "Sports Park", "Regional Park", "Garden & Heritage Park", "Residential Red Zone"}
MIN_AREA_HA = 0.1
BUFFER_M = 20.0  # amenities just outside a park boundary (car park, verge) still serve it
TREE_DENSITY_CAP = 200.0  # trees per ha; stops tiny planted strips topping the tree factor

FACTORS: list[tuple[str, str]] = [
    ("play", "Playground equipment"), ("seating", "Seats & picnic tables"), ("bbq", "Barbecues"),
    ("water", "Drinking water & showers"), ("sport", "Sports fields"), ("dogs", "Dog exercise area"),
    ("trees", "Tree cover"), ("size", "Size"),
]
WEIGHTS: dict[str, float] = {"play": 2, "seating": 1, "bbq": 1, "water": 1, "sport": 1, "dogs": 1, "trees": 1.5, "size": 1.5}


def select_parks(parks: gpd.GeoDataFrame, log: list[dict]) -> gpd.GeoDataFrame:
    n = len(parks)
    out = parks[parks["Type"].isin(INCLUDED_TYPES)]
    log_step(log, "keep visitor park types", n, len(out), f"excluded types not in {sorted(INCLUDED_TYPES)}")
    n = len(out)
    out = out[out["drvArea"] / 1e4 >= MIN_AREA_HA]
    log_step(log, "drop parks under min area", n, len(out), f"area < {MIN_AREA_HA} ha")
    return out


def _count(zones: gpd.GeoDataFrame, layer: gpd.GeoDataFrame) -> pd.Series:
    if layer.empty:
        return pd.Series(0, index=zones.index, dtype=float)
    right = gpd.GeoDataFrame({"_zone": zones.index}, geometry=zones.geometry.values, crs=zones.crs)
    hits = gpd.sjoin(layer[["geometry"]], right, predicate="intersects")
    return hits.groupby("_zone").size().reindex(zones.index, fill_value=0).astype(float)


def raw_factors(parks: gpd.GeoDataFrame, layers: dict[str, gpd.GeoDataFrame]) -> pd.DataFrame:
    zones = parks[["ParkID", "geometry"]].set_index("ParkID")
    buffered = zones.copy()
    buffered["geometry"] = zones.buffer(BUFFER_M)
    area_ha = zones.area / 1e4
    c = lambda key, z=buffered: _count(z, layers[key])  # noqa: E731
    raw = pd.DataFrame({
        "play": c("play_equipment"),
        "seating": c("seat") + c("picnic_table"),
        "bbq": c("bbq"),
        "water": c("drinking_fountain") + c("shower"),
        "sport": c("sport_field"),
        "dogs": (c("dog_exercise_area") > 0).astype(float),
        "trees": (c("tree", zones) / area_ha).clip(upper=TREE_DENSITY_CAP),
        "size": area_ha,
    })
    return raw[list(WEIGHTS)]


def percentiles(raw: pd.DataFrame) -> pd.DataFrame:
    # Having none of an amenity scores 0, not the average rank of all the tied zeros.
    pct = raw.rank(pct=True, method="average")
    return pct.where(raw > 0, 0.0)


def score(pct: pd.DataFrame, weights: dict[str, float]) -> pd.Series:
    w = {k: float(weights.get(k, 0)) for k in pct.columns}
    if sum(w.values()) == 0:
        w = {k: float(WEIGHTS.get(k, 0)) for k in pct.columns}
    total = sum(w.values())
    # Round half up, the same arithmetic as the site's scoring.ts (Math.round(1000 * sum / total) / 10).
    return np.floor(1000 * sum(pct[k] * v for k, v in w.items()) / total + 0.5) / 10


def slugify_unique(names: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    out = []
    for name in names:
        ascii_ = "".join(ch for ch in unicodedata.normalize("NFKD", name) if not unicodedata.combining(ch))
        base = re.sub(r"[^a-z0-9]+", "-", ascii_.lower().replace("'", "")).strip("-") or "park"
        seen[base] = seen.get(base, 0) + 1
        out.append(base if seen[base] == 1 else f"{base}-{seen[base]}")
    return out
