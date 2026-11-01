"""The one place that talks to the network."""
import json
import ssl
import time
import urllib.request
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode

# gis.ccc.govt.nz's CA lacks a critical Basic Constraints flag, which Python 3.13's
# strict X.509 mode rejects. Clear only that flag; verification stays on.
SSL_CONTEXT = ssl.create_default_context()
SSL_CONTEXT.verify_flags &= ~ssl.VERIFY_X509_STRICT

USER_AGENT = "christchurch-projects/0.1"


class ArcGISError(Exception):
    """ArcGIS returned an error body (often with HTTP 200)."""


def _open(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as r:
        return r.read()


_sleep = time.sleep


def get_json(url: str, params: dict | None = None, *, retries: int = 3, timeout: float = 60.0) -> dict:
    full = f"{url}?{urlencode(params)}" if params else url
    for attempt in range(retries):
        try:
            body = _open(full, timeout)
            break
        except HTTPError as e:
            if e.code < 500 or attempt == retries - 1:
                raise
        except (URLError, TimeoutError):
            if attempt == retries - 1:
                raise
        _sleep(0.5 * 2**attempt)
    data = json.loads(body)
    if isinstance(data, dict) and "error" in data:
        err = data["error"]
        raise ArcGISError(f"{err.get('message', '')} {' '.join(err.get('details') or [])} ({full})".strip())
    return data
