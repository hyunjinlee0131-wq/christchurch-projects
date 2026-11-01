from ccc_data.catalog import HUB_ITEMS, catalog


def page(ids, has_next, matched=3):
    links = [{"rel": "next", "href": "x"}] if has_next else []
    return {"numberMatched": matched, "features": [{"id": i, "properties": {"title": i}} for i in ids], "links": links}


def test_catalog_pages_with_stable_sort_and_dedupes(fake_server):
    fake_server({HUB_ITEMS: [page(["a", "b"], True), page(["b", "c"], False)]})
    feats = catalog(page_size=2)
    assert [f["id"] for f in feats] == ["a", "b", "c"]
    assert len(fake_server.calls) == 2
    assert all("sortBy=properties.created" in u for u in fake_server.calls)
    assert "startindex=1&" in fake_server.calls[0] and "startindex=3&" in fake_server.calls[1]


def test_catalog_stops_when_no_next_link(fake_server):
    fake_server({HUB_ITEMS: [page(["a"], False, matched=1)]})
    assert [f["id"] for f in catalog()] == ["a"]
    assert len(fake_server.calls) == 1


def test_catalog_stops_on_empty_page(fake_server):
    fake_server({HUB_ITEMS: [page(["a"], True), page([], True)]})
    assert [f["id"] for f in catalog(page_size=1)] == ["a"]
