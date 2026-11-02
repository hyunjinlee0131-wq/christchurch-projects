"""Cleaning and feature engineering for pipe blockages (baseline A5). Pure functions over EPSG:2193 frames."""
from datetime import date, datetime, timezone

import geopandas as gpd
import numpy as np
import pandas as pd

from ccc_data import log_step

GRAVITY_TYPES = {"Gravity", "Gravity Collector"}
MIN_LENGTH_M = 1.0

_GROUPS = {
    "Earthenware": ["EW", "VC"],
    "Concrete": ["RCRR", "CONC"],
    "Asbestos cement": ["AC"],
    "Plastic": ["UPVC", "PVC", "MPVC", "OPVC", "PVCLRC", "PE", "PE100", "HDPE", "LDPE", "MDPE80", "MDPE100", "PELRC",
                "CORRPE", "NovaFlow", "ABS", "GRP"],
    "Metal": ["CI", "DI", "CLDI", "CLS", "STEEL", "WI", "AL"],
    "Other": ["BB", "BLBRUTE"],
}
MATERIAL_GROUPS: dict[str, str] = {code: group for group, codes in _GROUPS.items() for code in codes}

# Genera commonly cited for sewer root intrusion (tunable; source noted in SUMMARY.md).
ROOT_AGGRESSIVE_GENERA = {"Populus", "Salix", "Eucalyptus", "Ulmus", "Platanus", "Fraxinus", "Quercus", "Acer",
                          "Betula", "Liquidambar"}


def select_population(pipes: gpd.GeoDataFrame, log: list[dict]) -> gpd.GeoDataFrame:
    steps = [
        ("keep gravity pipes", pipes["Type"].isin(GRAVITY_TYPES), f"Type in {sorted(GRAVITY_TYPES)}"),
        ("keep in-service pipes", pipes["ServiceStatus"] == "In Service", "ServiceStatus == In Service"),
        ("keep council-owned pipes", pipes["Ownership"] == "CCC", "Ownership == CCC"),
        ("drop pipes under 1 m", pipes["drvLength"].fillna(0) >= MIN_LENGTH_M, "log(length) offset needs length > 0"),
    ]
    out = pipes
    for name, mask, note in steps:
        n = len(out)
        out = out[mask.loc[out.index]]
        log_step(log, name, n, len(out), note)
    return out


def join_blockages(pipes: gpd.GeoDataFrame, blockages: pd.DataFrame, log: list[dict]) -> gpd.GeoDataFrame:
    counts = blockages.groupby("WwPipeID")["NumberOfBlockages"].sum()
    out = pipes.copy()
    out["blockages"] = out["WwPipeID"].map(counts).fillna(0).astype(int)
    unmatched = sorted(set(counts.index) - set(out["WwPipeID"]))
    log_step(log, "blockage ids unmatched to population (dropped)", len(counts), len(counts) - len(unmatched),
             "blocked pipes outside the modelled population (other types, abandoned, private)")
    out.attrs["unmatched_blockage_ids"] = unmatched
    return out


def _median_fill(s: pd.Series) -> tuple[pd.Series, pd.Series]:
    missing = s.isna()
    return s.fillna(s.median() if s.notna().any() else 0.0), missing


def pipe_features(pipes: gpd.GeoDataFrame, as_of: date) -> gpd.GeoDataFrame:
    out = pipes.copy()
    out["material"] = out["Construction"].map(lambda c: "Unknown" if pd.isna(c) else MATERIAL_GROUPS.get(c, "Other"))
    out["diameter_mm"], out["diameter_missing"] = _median_fill(out["NominalDiameter"].astype(float))
    as_of_ms = datetime(as_of.year, as_of.month, as_of.day, tzinfo=timezone.utc).timestamp() * 1000
    age = (as_of_ms - out["CommissionDate"].astype(float)) / (365.25 * 24 * 3600 * 1000)
    out["age_missing"] = age.isna()
    # Impute age by material first (materials have distinct eras), then overall.
    by_material = age.groupby(out["material"]).transform("median")
    out["age_years"] = age.fillna(by_material).fillna(age.median() if age.notna().any() else 0.0).round(2)
    out["depth_m"], out["depth_missing"] = _median_fill(out["Depth"].astype(float))
    # CCC records grade as "1 in N" (median ~218; sign = flow direction). Convert to slope % = 100 / |N|.
    n = out["Grade"].astype(float).abs()
    out["grade"], out["grade_missing"] = _median_fill((100.0 / n).where(n >= 1.0))
    out["relined"] = out["Treatment"].notna()
    out["length_m"] = out["drvLength"].astype(float)
    return out


def _count_near(pipes: gpd.GeoDataFrame, trees: gpd.GeoDataFrame, radius: float, value: str | None = None) -> pd.Series:
    if trees.empty:
        return pd.Series(0.0, index=pipes.index)
    zones = gpd.GeoDataFrame({"_pipe": pipes.index}, geometry=pipes.geometry.buffer(radius).values, crs=pipes.crs)
    hits = gpd.sjoin(trees, zones, predicate="intersects")
    agg = hits.groupby("_pipe")[value].sum() if value else hits.groupby("_pipe").size()
    return agg.reindex(pipes.index, fill_value=0).astype(float)


def tree_features(pipes: gpd.GeoDataFrame, trees: gpd.GeoDataFrame, radii: tuple[float, float] = (5.0, 10.0)) -> gpd.GeoDataFrame:
    near, far = radii
    t = trees[["Genus", "CrownSpread", "geometry"]].copy()
    t["CrownSpread"] = t["CrownSpread"].fillna(0.0)
    t["aggressive"] = t["Genus"].isin(ROOT_AGGRESSIVE_GENERA).astype(float)
    out = pipes.copy()
    out["trees_5m"] = _count_near(out, t, near).astype(int)
    out["trees_10m"] = _count_near(out, t, far).astype(int)
    out["aggressive_trees_10m"] = _count_near(out, t, far, "aggressive").astype(int)
    out["crown_sum_10m"] = _count_near(out, t, far, "CrownSpread").round(1)
    out["trees_per_100m_10m"] = (100 * out["trees_10m"] / out.geometry.length.clip(lower=MIN_LENGTH_M)).round(3)
    return out


def street_names(pipes: gpd.GeoDataFrame, streets: gpd.GeoDataFrame, max_m: float = 40.0) -> pd.Series:
    left = gpd.GeoDataFrame({"_pipe": pipes.index}, geometry=pipes.geometry.interpolate(0.5, normalized=True).values,
                            crs=pipes.crs)
    hits = gpd.sjoin_nearest(left, streets[["FullRoadName", "geometry"]], max_distance=max_m, how="left")
    names = hits.drop_duplicates("_pipe").set_index("_pipe")["FullRoadName"]
    return names.reindex(pipes.index).fillna("").astype(str)


def grid_cell(pipes: gpd.GeoDataFrame, size_m: int = 1000) -> pd.Series:
    mid = pipes.geometry.interpolate(0.5, normalized=True)
    return (np.floor(mid.x / size_m).astype(int).astype(str) + "_" + np.floor(mid.y / size_m).astype(int).astype(str))
