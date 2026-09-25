"""A polite HTTP client: robots.txt, delays, a request budget, a cache and back-off.

* robots.txt of each host is fetched once and checked before every request;
* single-threaded, with a random 3–5 s pause before every network request;
* at most ``max_requests`` network requests per run (cache hits are free);
* raw responses are cached under ``<out>/.cache`` so re-runs do not fetch again;
* HTTP 429 or 403 stops the whole run (``StopCollecting``): the site wants us to back off.
"""

from __future__ import annotations

import hashlib
import json
import logging
import random
import time
from pathlib import Path
from urllib.parse import urlsplit

from corpus_collector.config import (
    MAX_DELAY_SECONDS,
    MIN_DELAY_SECONDS,
    REQUEST_TIMEOUT_SECONDS,
    USER_AGENT,
)
from corpus_collector.robots import RobotsRules

logger = logging.getLogger(__name__)


class StopCollecting(Exception):
    """The site asked us to stop (429/403) or the request budget is used up."""


class DisallowedUrl(Exception):
    """robots.txt (or the no-query-string rule) forbids this URL; it was not requested."""


def use_system_certificates() -> None:
    """Verify HTTPS against the operating-system store (antivirus that re-signs HTTPS)."""
    try:
        import truststore
    except ImportError:  # pragma: no cover - optional
        return
    truststore.inject_into_ssl()


class PoliteClient:
    def __init__(
        self,
        cache_dir: Path,
        max_requests: int,
        sleep=time.sleep,
        session=None,
        delay: tuple[float, float] = (MIN_DELAY_SECONDS, MAX_DELAY_SECONDS),
    ) -> None:
        import requests

        self.cache_dir = cache_dir
        self.max_requests = max_requests
        self.requests_made = 0
        self.cache_hits = 0
        self._sleep = sleep
        self._delay = delay
        self._robots: dict[str, RobotsRules] = {}
        self.session = session or requests.Session()
        self.session.headers["User-Agent"] = USER_AGENT

    # ----------------------------------------------------------------------- internals

    def _cache_path(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode()).hexdigest()[:24]
        return self.cache_dir / urlsplit(url).netloc / f"{digest}.json"

    def _network_get(self, url: str) -> tuple[int, str]:
        if self.requests_made >= self.max_requests:
            raise StopCollecting(f"Request budget of {self.max_requests} used up.")
        self._sleep(random.uniform(*self._delay))
        self.requests_made += 1
        response = self.session.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
        logger.info("GET %s -> %s", url, response.status_code)
        if response.status_code in (403, 429):
            raise StopCollecting(
                f"{urlsplit(url).netloc} answered {response.status_code}; stopping this run."
            )
        return response.status_code, response.text

    def robots_for(self, url: str) -> RobotsRules:
        parts = urlsplit(url)
        host = f"{parts.scheme}://{parts.netloc}"
        if host not in self._robots:
            status, text = self._cached_or_fetch(host + "/robots.txt", check_robots=False)
            # A missing robots.txt (404) allows everything; other errors disallow everything.
            if status == 404:
                text = ""
            elif status >= 400:
                text = "User-agent: *\nDisallow: /"
            self._robots[host] = RobotsRules.parse(text, USER_AGENT)
        return self._robots[host]

    def _cached_or_fetch(
        self, url: str, check_robots: bool = True, allow_query: bool = False, use_cache: bool = True
    ) -> tuple[int, str]:
        path = self._cache_path(url)
        if use_cache and path.exists():
            self.cache_hits += 1
            cached = json.loads(path.read_text(encoding="utf-8"))
            return cached["status"], cached["text"]
        if check_robots and not self.robots_for(url).allowed(url, allow_query=allow_query):
            raise DisallowedUrl(url)
        status, text = self._network_get(url)
        if status < 500:  # do not cache server errors
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps({"url": url, "status": status, "text": text}), "utf-8")
        return status, text

    # -------------------------------------------------------------------------- public

    def get(self, url: str) -> tuple[int, str]:
        """GET a crawled page (from the cache when possible).

        Raises DisallowedUrl (never requested) or StopCollecting.
        """
        if not self.robots_for(url).allowed(url):
            raise DisallowedUrl(url)
        return self._cached_or_fetch(url)

    def get_api(self, url: str) -> tuple[int, str]:
        """GET a documented public API endpoint (query string allowed; robots still checked).

        API results change over time, so they are fetched fresh (and cached for inspection).
        """
        if not self.robots_for(url).allowed(url, allow_query=True):
            raise DisallowedUrl(url)
        return self._cached_or_fetch(url, allow_query=True, use_cache=False)
