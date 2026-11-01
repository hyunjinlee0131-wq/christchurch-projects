import ssl
from urllib.error import URLError

import pytest

from ccc_data.http import SSL_CONTEXT, ArcGISError, get_json


def test_ssl_context_keeps_verification_but_not_strict():
    assert SSL_CONTEXT.verify_mode == ssl.CERT_REQUIRED
    assert SSL_CONTEXT.check_hostname is True
    assert not (SSL_CONTEXT.verify_flags & ssl.VERIFY_X509_STRICT)


def test_get_json_raises_on_error_body(fake_server):
    fake_server({"https://x/layer/5/query": {"error": {"code": 400, "message": "Invalid or missing input parameters.", "details": ["Invalid Layer or Table ID: 5."]}}})
    with pytest.raises(ArcGISError, match="Invalid Layer"):
        get_json("https://x/layer/5/query", {"f": "json"})


def test_get_json_encodes_params(fake_server):
    fake_server({"https://x/q": {"ok": 1}})
    get_json("https://x/q", {"where": "1=1", "f": "json"})
    assert fake_server.calls == ["https://x/q?where=1%3D1&f=json"]


def test_get_json_retries_then_succeeds(fake_server):
    fake_server({"https://x/q": [URLError("boom"), {"count": 9}]})
    assert get_json("https://x/q", retries=3) == {"count": 9}


def test_get_json_gives_up_after_retries(fake_server):
    fake_server({"https://x/q": [URLError("a"), URLError("b"), URLError("c")]})
    with pytest.raises(URLError):
        get_json("https://x/q", retries=3)
    assert len(fake_server.calls) == 3
