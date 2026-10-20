"""Download one AR file: sequential, gzip, clear User-Agent, retries with backoff."""

import gzip
import time
import urllib.error
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

USER_AGENT = (
    "parlamento-aberto/0.1 (+https://github.com/rfsbraz/parlamento-aberto; "
    "open data mirror, sequential requests)"
)


@dataclass
class Response:
    status: int
    content_type: str
    body: bytes


def http_get(url: str, timeout: float = 600) -> Response:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            if r.headers.get("Content-Encoding", "").lower() == "gzip":
                body = gzip.decompress(body)
            return Response(r.status, r.headers.get("Content-Type", ""), body)
    except urllib.error.HTTPError as e:
        return Response(e.code, e.headers.get("Content-Type", ""), e.read())


def is_soft_404(resp: Response) -> bool:
    """AR answers a missing or regenerating file with an HTML page and status 200."""
    head = resp.body[:512].lstrip().lower()
    return "html" in resp.content_type.lower() or head.startswith((b"<!doctype", b"<html"))


def fetch(
    url: str,
    *,
    get: Callable[[str], Response] = http_get,
    sleep: Callable[[float], None] = time.sleep,
    attempts: int = 4,
    backoff: float = 60.0,
) -> tuple[Response | None, int]:
    """Return (last response, attempts used). Retries soft 404s, 5xx and network errors.

    The last response is returned even if it is still a soft 404, so the caller
    can reject it. None means every attempt failed at the network level.
    """
    last = None
    for attempt in range(1, attempts + 1):
        try:
            last = get(url)
        except (OSError, urllib.error.URLError):
            last = None
        if last is not None and last.status == 200 and not is_soft_404(last):
            return last, attempt
        if attempt < attempts:
            sleep(backoff * 2 ** (attempt - 1))
    return last, attempts
