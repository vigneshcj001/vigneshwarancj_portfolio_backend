import asyncio
import json
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from typing import Any

from app.config import METADATA_CACHE_SECONDS

_cache: dict[str, Any] = {"expires": 0, "value": None}


class MetadataUnavailable(RuntimeError):
    pass


def _fetch_json(url: str) -> Any:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "vigneshwaran-portfolio/1.0", "Accept": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=8) as response:
        return json.load(response)


async def public_metadata() -> dict[str, Any]:
    now = time.time()
    if _cache["value"] and _cache["expires"] > now:
        return _cache["value"]
    try:
        repos, pypi = await asyncio.gather(
            asyncio.to_thread(_fetch_json, "https://api.github.com/users/vigneshcj001/repos?sort=updated&per_page=6"),
            asyncio.to_thread(_fetch_json, "https://pypi.org/pypi/glycanbench/json"),
        )
        value = {
            "github": [
                {"name": item["name"], "url": item["html_url"], "stars": item["stargazers_count"], "updated_at": item["updated_at"]}
                for item in repos[:6]
            ],
            "pypi": {"version": pypi["info"]["version"], "url": pypi["info"]["package_url"]},
            "cached_at": datetime.now(timezone.utc).isoformat(),
        }
        _cache.update(value=value, expires=now + METADATA_CACHE_SECONDS)
        return value
    except (urllib.error.URLError, TimeoutError, KeyError, ValueError) as exc:
        if _cache["value"]:
            return _cache["value"]
        raise MetadataUnavailable("Public metadata temporarily unavailable") from exc


def _urls(value: Any):
    if isinstance(value, dict):
        for item in value.values():
            yield from _urls(item)
    elif isinstance(value, list):
        for item in value:
            yield from _urls(item)
    elif isinstance(value, str) and value.startswith("https://"):
        yield value


def _check_link(url: str) -> dict[str, Any]:
    try:
        request = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "vigneshwaran-portfolio/1.0"})
        with urllib.request.urlopen(request, timeout=8) as response:
            return {"url": url, "status": response.status, "ok": response.status < 400}
    except Exception as exc:
        return {"url": url, "status": None, "ok": False, "error": str(exc)[:160]}


async def check_links(content: dict[str, Any]) -> list[dict[str, Any]]:
    urls = sorted(set(_urls(content)))[:100]
    return await asyncio.gather(*(asyncio.to_thread(_check_link, url) for url in urls))
