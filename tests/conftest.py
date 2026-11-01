import json
from urllib.parse import urlsplit

import pytest


@pytest.fixture
def fake_server(monkeypatch):
    """Route URLs (query string stripped) to canned responses.

    A value may be a dict (always returned), an Exception (always raised),
    a list (one item consumed per call) or a callable(full_url) -> dict.
    Every requested full URL is recorded in `.calls`.
    """
    import ccc_data.http as http

    class Server:
        calls: list[str] = []
        routes: dict = {}

        def __call__(self, routes):
            self.routes.update(routes)
            return self

    server = Server()
    server.calls, server.routes = [], {}

    def fake_open(url, timeout):
        server.calls.append(url)
        p = urlsplit(url)
        key = f"{p.scheme}://{p.netloc}{p.path}"
        if key not in server.routes:
            raise AssertionError(f"unexpected URL {url}")
        r = server.routes[key]
        if isinstance(r, list):
            r = r.pop(0)
        if callable(r) and not isinstance(r, (dict, Exception)):
            r = r(url)
        if isinstance(r, Exception):
            raise r
        return json.dumps(r).encode()

    monkeypatch.setattr(http, "_open", fake_open)
    monkeypatch.setattr(http, "_sleep", lambda s: None)
    return server
