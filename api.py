
import httpx
from config import IPTV_BASE_URL

PLAYLIST_ID = 0

# Shared client to reuse connections and avoid repeated DNS/connection issues
_http_client: httpx.AsyncClient | None = None


def _get_client() -> httpx.AsyncClient:
    global _http_client
    if _http_client is None:
        _http_client = httpx.AsyncClient(
            timeout=httpx.Timeout(60.0),
            limits=httpx.Limits(max_keepalive_connections=4),
        )
    return _http_client


async def _request(path: str, params: dict) -> dict:
    """GET JSON from IPTV backend. Raises httpx.HTTPError on failure."""
    client = _get_client()
    r = await client.get(f"{IPTV_BASE_URL}{path}", params=params)
    r.raise_for_status()
    return r.json()


async def search_movies(q: str) -> dict:
    """Search VOD movies by name. Returns JSON with success, data, count."""
    return await _request(
        "/api/xtream/vod/search",
        {"q": q, "playlist_id": PLAYLIST_ID},
    )


async def get_movie_stream_url(vod_id: str) -> dict:
    """Get stream URL(s) for a movie. Returns JSON with recommended_url etc."""
    return await _request(
        "/api/xtream/vod/stream-url",
        {"vod_id": vod_id, "playlist_id": PLAYLIST_ID},
    )


async def search_series(q: str) -> dict:
    """Search series by name. Returns JSON with success, data, count."""
    return await _request(
        "/api/xtream/series/search",
        {"q": q, "playlist_id": PLAYLIST_ID},
    )


async def get_series_info(series_id: str) -> dict:
    """Get series details including seasons and episodes."""
    return await _request(
        "/api/xtream/series/info",
        {"series_id": series_id, "playlist_id": PLAYLIST_ID},
    )


async def get_episode_stream_url(
    series_id: str, season_number: str, episode_number: str
) -> dict:
    """Get stream URL(s) for a series episode."""
    return await _request(
        "/api/xtream/series/episode/stream-url",
        {
            "series_id": series_id,
            "season_number": season_number,
            "episode_number": episode_number,
            "playlist_id": PLAYLIST_ID,
        },
    )
