"""Find a layer by service + name on the live server (catalog URLs go stale)."""
import difflib
import re
from dataclasses import dataclass

from .http import get_json

BASE = "https://gis.ccc.govt.nz/server/rest/services/OpenData"

_listings: dict[str, list[dict]] = {}  # service -> layers + tables, for this process


class LayerNotFound(Exception):
    pass


class AmbiguousLayer(Exception):
    pass


@dataclass(frozen=True)
class LayerRef:
    service: str
    name: str
    layer_id: int
    url: str
    object_id_field: str
    max_record_count: int
    has_geometry: bool
    fields: tuple[str, ...]


def normalise(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def resolve(service: str, name: str) -> LayerRef:
    if service not in _listings:
        listing = get_json(f"{BASE}/{service}/FeatureServer", {"f": "json"})
        _listings[service] = (listing.get("layers") or []) + (listing.get("tables") or [])
    entries = _listings[service]
    hits = [e for e in entries if normalise(e["name"]) == normalise(name)]
    if not hits:
        by_norm = {normalise(e["name"]): e["name"] for e in entries}
        near = [by_norm[n] for n in difflib.get_close_matches(normalise(name), list(by_norm), n=5, cutoff=0.4)]
        raise LayerNotFound(f"No layer {name!r} in {service}. Nearest: {', '.join(near) or 'none'}")
    if len(hits) > 1:
        raise AmbiguousLayer(f"{name!r} matches {[e['name'] for e in hits]} in {service}")
    hit = hits[0]
    url = f"{BASE}/{service}/FeatureServer/{hit['id']}"
    d = get_json(url, {"f": "json"})
    return LayerRef(
        service=service,
        name=hit["name"],
        layer_id=hit["id"],
        url=url,
        object_id_field=d["objectIdField"],
        max_record_count=d.get("maxRecordCount", 1000),
        has_geometry="geometryType" in d,
        fields=tuple(f["name"] for f in d.get("fields") or []),
    )
