import asyncio
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from app.config import GITHUB_TOKEN, METADATA_CACHE_SECONDS

USER_AGENT = "vigneshwaran-portfolio/1.0"
# After an upstream failure, wait this long before trying again so a GitHub
# outage or rate limit (60 req/h unauthenticated) is not hammered per visitor.
FAILURE_BACKOFF_SECONDS = 300
MAX_LINK_CHECKS = 100
LINK_CHECK_CONCURRENCY = 8

_cache: dict[str, Any] = {"expires": 0.0, "value": None, "retry_after": 0.0}
_lock = asyncio.Lock()


class MetadataUnavailable(RuntimeError):
    pass


def _fetch_json(url: str) -> Any:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if GITHUB_TOKEN and url.startswith("https://api.github.com/"):
        headers["Authorization"] = f"Bearer {GITHUB_TOKEN}"
    request = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


async def _refresh() -> dict[str, Any]:
    repos, pypi = await asyncio.gather(
        asyncio.to_thread(_fetch_json, "https://api.github.com/users/vigneshcj001/repos?sort=updated&per_page=6"),
        asyncio.to_thread(_fetch_json, "https://pypi.org/pypi/glycanbench/json"),
    )
    return {
        "github": [
            {"name": item["name"], "url": item["html_url"], "stars": item["stargazers_count"], "updated_at": item["updated_at"]}
            for item in repos[:6]
            if not item.get("fork")
        ],
        "pypi": {"version": pypi["info"]["version"], "url": pypi["info"]["package_url"]},
        "cached_at": datetime.now(timezone.utc).isoformat(),
    }


async def public_metadata() -> dict[str, Any]:
    now = time.time()
    if _cache["value"] and _cache["expires"] > now:
        return _cache["value"]
    # Single-flight: concurrent cache misses share one upstream refresh.
    async with _lock:
        now = time.time()
        if _cache["value"] and _cache["expires"] > now:
            return _cache["value"]
        if _cache["retry_after"] > now:
            if _cache["value"]:
                return _cache["value"]
            raise MetadataUnavailable("Public metadata temporarily unavailable")
        try:
            value = await _refresh()
        except (urllib.error.URLError, TimeoutError, KeyError, ValueError, TypeError) as exc:
            _cache["retry_after"] = now + FAILURE_BACKOFF_SECONDS
            if _cache["value"]:
                return _cache["value"]  # Serve stale data rather than failing.
            raise MetadataUnavailable("Public metadata temporarily unavailable") from exc
        _cache.update(value=value, expires=now + METADATA_CACHE_SECONDS, retry_after=0.0)
        return value


def _urls(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _urls(item)
    elif isinstance(value, str) and value.startswith("https://"):
        yield value


def _request_status(url: str, method: str) -> int:
    request = urllib.request.Request(url, method=method, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=8) as response:
            return response.status
    except urllib.error.HTTPError as exc:
        return exc.code


def _check_link(url: str) -> dict[str, Any]:
    try:
        status = _request_status(url, "HEAD")
        # Many hosts (LinkedIn, some CDNs) reject HEAD; confirm with GET.
        if status in (403, 405, 501) or status >= 500:
            status = _request_status(url, "GET")
        return {"url": url, "status": status, "ok": status < 400}
    except Exception as exc:
        return {"url": url, "status": None, "ok": False, "error": str(exc)[:160]}


async def check_links(content: dict[str, Any]) -> list[dict[str, Any]]:
    urls = sorted(set(_urls(content)))[:MAX_LINK_CHECKS]
    semaphore = asyncio.Semaphore(LINK_CHECK_CONCURRENCY)

    async def bounded(url: str) -> dict[str, Any]:
        async with semaphore:
            return await asyncio.to_thread(_check_link, url)

    return await asyncio.gather(*(bounded(url) for url in urls))
