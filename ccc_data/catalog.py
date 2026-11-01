"""The CCC open data portal's dataset catalog (ArcGIS Hub search API)."""
from .http import get_json

HUB_ITEMS = "https://opendata-christchurchcity.hub.arcgis.com/api/search/v1/collections/dataset/items"


def catalog(*, page_size: int = 100) -> list[dict]:
    # Without a stable sort the Hub returns overlapping pages (386 unique of 483 seen).
    seen: dict[str, dict] = {}
    start = 1
    while True:
        page = get_json(HUB_ITEMS, {"limit": page_size, "startindex": start, "sortBy": "properties.created"})
        feats = page.get("features") or []
        for f in feats:
            seen.setdefault(f["id"], f)
        if not feats or not any(l.get("rel") == "next" for l in page.get("links") or []):
            return list(seen.values())
        start += page_size
