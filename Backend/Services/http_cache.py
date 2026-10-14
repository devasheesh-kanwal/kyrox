# Backend/Services/http_cache.py
"""
Shared upstream HTTP access with caching, request coalescing and retries.

Every data tool (Open-Meteo, INCOIS, GDACS, Overpass, geocoding) goes through
`cached_get_json` so that:
  * identical requests made at the same moment share ONE upstream call
    (the dashboard, chat and heatmap often ask for the same point together);
  * responses are reused for `ttl` seconds instead of hammering free APIs,
    which is what previously caused intermittent "weather unavailable";
  * a transient 429/5xx is retried once with a short backoff;
  * if the upstream is down, the last good response may be served for up to
    `stale_ttl` seconds - and the caller is told it is stale, never silently.
"""
import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

import httpx

logger = logging.getLogger(__name__)

USER_AGENT = "KyroX-ORCA-Marine-AI/3.0 (+https://github.com/)"
DEFAULT_TIMEOUT = httpx.Timeout(12.0, connect=6.0)
RETRY_STATUS = {429, 500, 502, 503, 504}
MAX_CACHE_ENTRIES = 5000

_client: Optional[httpx.AsyncClient] = None


@dataclass
class CachedResponse:
    data: Any
    fetched_at: float
    stale: bool = False

    @property
    def age_seconds(self) -> int:
        return int(time.time() - self.fetched_at)


class UpstreamError(Exception):
    """Raised when an upstream source cannot be reached and no usable cache exists."""


_cache: Dict[str, Tuple[float, Any]] = {}
_inflight: Dict[str, "asyncio.Future[CachedResponse]"] = {}


def _client_instance() -> httpx.AsyncClient:
    global _client
    if _client is None or _client.is_closed:
        _client = httpx.AsyncClient(
            timeout=DEFAULT_TIMEOUT,
            headers={"User-Agent": USER_AGENT},
            follow_redirects=True,
        )
    return _client


async def close_client() -> None:
    global _client
    if _client is not None and not _client.is_closed:
        await _client.aclose()
    _client = None


def _cache_key(url: str, params: Optional[dict]) -> str:
    items = sorted((params or {}).items())
    return url + "?" + "&".join(f"{k}={v}" for k, v in items)


def _evict_if_needed() -> None:
    if len(_cache) <= MAX_CACHE_ENTRIES:
        return
    # Drop the oldest quarter; simple and good enough for a single process.
    for key, _ in sorted(_cache.items(), key=lambda kv: kv[1][0])[: MAX_CACHE_ENTRIES // 4]:
        _cache.pop(key, None)


async def _fetch(url: str, params: Optional[dict], timeout: Optional[httpx.Timeout]) -> Any:
    client = _client_instance()
    last_exc: Optional[Exception] = None
    for attempt in range(2):
        try:
            response = await client.get(url, params=params, timeout=timeout or DEFAULT_TIMEOUT)
            if response.status_code in RETRY_STATUS and attempt == 0:
                await asyncio.sleep(0.8)
                continue
            response.raise_for_status()
            if response.status_code == 204 or not response.content.strip():
                return None
            return response.json()
        except (httpx.TimeoutException, httpx.TransportError) as exc:
            last_exc = exc
            if attempt == 0:
                await asyncio.sleep(0.5)
                continue
        except httpx.HTTPStatusError as exc:
            # Log upstream details server-side only; never echo them to clients.
            logger.warning("Upstream %s returned %s", url, exc.response.status_code)
            raise UpstreamError(f"Upstream returned status {exc.response.status_code}") from exc
        except ValueError as exc:
            raise UpstreamError("Upstream returned invalid JSON") from exc
    raise UpstreamError(f"Upstream unreachable: {type(last_exc).__name__}") from last_exc


async def cached_get_json(
    url: str,
    params: Optional[dict] = None,
    ttl: float = 600.0,
    stale_ttl: float = 3600.0,
    timeout: Optional[httpx.Timeout] = None,
) -> CachedResponse:
    """GET `url` as JSON with TTL caching, in-flight coalescing and stale fallback."""
    key = _cache_key(url, params)
    now = time.time()

    cached = _cache.get(key)
    if cached and now - cached[0] < ttl:
        return CachedResponse(cached[1], cached[0])

    pending = _inflight.get(key)
    if pending is not None:
        return await asyncio.shield(pending)

    loop = asyncio.get_running_loop()
    future: "asyncio.Future[CachedResponse]" = loop.create_future()
    _inflight[key] = future
    try:
        data = await _fetch(url, params, timeout)
        fetched_at = time.time()
        _cache[key] = (fetched_at, data)
        _evict_if_needed()
        result = CachedResponse(data, fetched_at)
        future.set_result(result)
        return result
    except Exception as exc:
        if cached and now - cached[0] < stale_ttl:
            logger.warning("Serving stale data for %s after upstream failure: %s", url, exc)
            result = CachedResponse(cached[1], cached[0], stale=True)
            future.set_result(result)
            return result
        error = exc if isinstance(exc, UpstreamError) else UpstreamError(str(exc))
        future.set_exception(error)
        # Mark the exception as retrieved when nobody else awaited this future.
        future.exception()
        raise error from exc
    finally:
        _inflight.pop(key, None)


def clear_cache() -> None:
    """Testing helper."""
    _cache.clear()
