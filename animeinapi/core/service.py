from __future__ import annotations

from ..config import Settings
from ..core.cache import Cache, Cached
from ..core.client import HttpClient, UpstreamError
from ..core.constants import (
    TTL_ADS,
    TTL_CHAT,
    TTL_COMMENTS,
    TTL_DETAIL,
    TTL_EPISODES,
    TTL_GENRES,
    TTL_HOME,
    TTL_SCHEDULE,
    TTL_SEARCH,
    TTL_STREAMS,
    TTL_TRAILERS,
)
from ..models import (
    Ad,
    AnimeDetail,
    AnimeSummary,
    ChatData,
    CommentList,
    Episode,
    Genre,
    HomeData,
    SearchResult,
    StreamInfo,
    StreamResponse,
    Trailer,
)


class AnimeinService:
    def __init__(self, http: HttpClient, cache: Cache, settings: Settings) -> None:
        self._http = http
        self._cache = cache
        self._settings = settings

    def _headers(self) -> dict[str, str]:
        return {
            "x-proxy-secret": self._settings.proxy_secret,
            "Referer": self._settings.base_url + "/",
            "Accept": "application/json",
        }

    async def _get(self, path: str, **params: str | int) -> dict:
        url = f"{self._settings.proxy_url}/{path}"
        payload = await self._http.get_json(url, params=params, headers=self._headers())
        if not isinstance(payload, dict):
            raise UpstreamError("Payload upstream bukan objek JSON")
        if payload.get("error") is True or payload.get("status", 200) != 200:
            if payload.get("status") == 404:
                from ..core.client import UpstreamNotFound

                raise UpstreamNotFound(str(payload.get("data", "Not found")))
            raise UpstreamError(f"Upstream error: {payload.get('data')}")
        return payload

    async def _cached(self, parts: tuple[str | int, ...], ttl: float, fetch) -> Cached:
        key = ":".join(map(str, parts))
        return await self._cache.get(key, ttl, fetch, stale_ttl=ttl)

    async def search(
        self, query: str, page: int = 0, sort: str = "views", genre: str = ""
    ) -> SearchResult:
        cached = await self._cached(
            ("search", page, sort, query, genre),
            TTL_SEARCH,
            lambda: self._search(query, page, sort, genre),
        )
        return cached.data

    async def _search(self, query: str, page: int, sort: str, genre: str) -> SearchResult:
        payload = await self._get(
            "3/2/explore/movie", page=page, sort=sort, keyword=query, genre_in=genre
        )
        data = payload.get("data", {})
        movies = data if isinstance(data, list) else (data.get("movies") or data.get("movie") or [])
        items = [AnimeSummary.model_validate(m) for m in movies]
        total = None
        if isinstance(data, dict):
            total = data.get("total_movies") or data.get("total")
        return SearchResult(page=page, total=total or len(items), items=items)

    async def get_genres(self) -> list[Genre]:
        cached = await self._cached(("genres",), TTL_GENRES, self._get_genres)
        return cached.data

    async def _get_genres(self) -> list[Genre]:
        payload = await self._get("3/2/explore/genre")
        data = payload.get("data") or {}
        genres = data.get("genre") if isinstance(data, dict) else data or []
        return [Genre.model_validate(g) for g in genres]

    async def get_home(self, day: str = "RANDOM", limit: int = 16) -> HomeData:
        cached = await self._cached(
            ("home", day, limit), TTL_HOME, lambda: self._get_home(day, limit)
        )
        return cached.data

    async def _get_home(self, day: str, limit: int) -> HomeData:
        payload = await self._get("3/2/home/data", day=day, limit=limit)
        return HomeData.model_validate(payload.get("data") or {})

    async def get_schedule(self, day: str = "RANDOM") -> list[AnimeSummary]:
        cached = await self._cached(
            ("schedule", day), TTL_SCHEDULE, lambda: self._get_schedule(day)
        )
        return cached.data

    async def _get_schedule(self, day: str) -> list[AnimeSummary]:
        payload = await self._get("3/2/schedule/data", day=day)
        data = payload.get("data") or {}
        movies = data.get("movie") if isinstance(data, dict) else data or []
        return [AnimeSummary.model_validate(m) for m in movies]

    async def get_anime(self, anime_id: str) -> AnimeDetail:
        cached = await self._cached(
            ("anime", anime_id), TTL_DETAIL, lambda: self._get_anime(anime_id)
        )
        return cached.data

    async def _get_anime(self, anime_id: str) -> AnimeDetail:
        payload = await self._get(f"3/2/movie/detail/{anime_id}")
        data = payload.get("data") or {}
        movie = data.get("movie") if isinstance(data, dict) else None
        if not movie:
            raise UpstreamError("Detail movie kosong dari upstream")
        return AnimeDetail.model_validate(movie)

    async def get_episodes(self, anime_id: str, page: int = 0) -> list[Episode]:
        cached = await self._cached(
            ("episodes", anime_id, page), TTL_EPISODES, lambda: self._get_episodes(anime_id, page)
        )
        return cached.data

    async def _get_episodes(self, anime_id: str, page: int) -> list[Episode]:
        payload = await self._get(f"3/2/movie/episode/{anime_id}", page=page)
        data = payload.get("data") or []
        episodes = data if isinstance(data, list) else data.get("episode") or []
        items = [Episode.model_validate(ep) for ep in episodes]

        def sort_key(ep: Episode) -> int:
            try:
                return int(ep.index)
            except ValueError:
                return 0

        return sorted(items, key=sort_key)

    async def get_streams(self, episode_id: str) -> StreamResponse:
        cached = await self._cached(
            ("streams", episode_id), TTL_STREAMS, lambda: self._get_streams(episode_id)
        )
        return cached.data

    async def _get_streams(self, episode_id: str) -> StreamResponse:
        payload = await self._get(f"3/2/episode/streamnew/{episode_id}")
        data = payload.get("data", {})
        episode_raw = data.get("episode")
        if not episode_raw:
            raise UpstreamError("Data episode kosong dari upstream")
        episode = Episode.model_validate(episode_raw)

        streams: dict[str, list[StreamInfo]] = {}
        for server in data.get("server") or []:
            info = StreamInfo.model_validate(server)
            streams.setdefault(info.quality, []).append(info)

        episode_next = data.get("episode_next")
        return StreamResponse(
            episode=episode,
            episode_next=Episode.model_validate(episode_next) if episode_next else None,
            streams=streams,
        )

    async def get_trailers(self, anime_id: str) -> list[Trailer]:
        cached = await self._cached(
            ("trailers", anime_id), TTL_TRAILERS, lambda: self._get_trailers(anime_id)
        )
        return cached.data

    async def _get_trailers(self, anime_id: str) -> list[Trailer]:
        payload = await self._get("data/movie/trailer/list", id_movie=anime_id)
        data = payload.get("data") or {}
        trailers = data.get("trailer") if isinstance(data, dict) else data or []
        return [Trailer.model_validate(t) for t in trailers]

    async def get_chat(self, highest_id: str = "", lowest_id: str = "") -> ChatData:
        cached = await self._cached(
            ("chat", highest_id, lowest_id),
            TTL_CHAT,
            lambda: self._get_chat(highest_id, lowest_id),
        )
        return cached.data

    async def _get_chat(self, highest_id: str, lowest_id: str) -> ChatData:
        payload = await self._get("3/2/chat/data", highest_id=highest_id, lowest_id=lowest_id)
        return ChatData.model_validate(payload.get("data") or {})

    async def get_comments(self, episode_id: str, sort: str = "new", page: int = 0) -> CommentList:
        cached = await self._cached(
            ("comments", episode_id, sort, page),
            TTL_COMMENTS,
            lambda: self._get_comments(episode_id, sort, page),
        )
        return cached.data

    async def _get_comments(self, episode_id: str, sort: str, page: int) -> CommentList:
        payload = await self._get("3/2/comment/data", id_episode=episode_id, sort=sort, page=page)
        return CommentList.model_validate(payload.get("data") or {})

    async def get_ads(self, tag: str = "") -> Ad | None:
        cached = await self._cached(("ads", tag), TTL_ADS, lambda: self._get_ads(tag))
        return cached.data

    async def _get_ads(self, tag: str) -> Ad | None:
        payload = await self._get("data/ads/show", tag=tag)
        ad = (payload.get("data") or {}).get("ad")
        return Ad.model_validate(ad) if ad else None
