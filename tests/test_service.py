"""Test service AnimeinService (animeinweb.com) - flow, cache, error, concurrency."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest
import respx
from httpx import Response

from animeinapi.config import Settings
from animeinapi.core.cache import Cache
from animeinapi.core.client import HttpClient, UpstreamError, UpstreamNotFound
from animeinapi.core.service import AnimeinService

pytestmark = pytest.mark.anyio

FIXTURES = Path(__file__).parent / "fixtures"

# (base_url, proxy_url) - sesuai logika di config
BASE_URL = "https://animeinweb.com"
PROXY_URL = f"{BASE_URL}/api/proxy"


def load(name: str) -> dict:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


@pytest.fixture
def settings() -> Settings:
    return Settings(base_url=BASE_URL, proxy_secret="test-secret", timeout=5.0, retries=2)


@pytest.fixture
def service(settings):
    return AnimeinService(HttpClient(settings), Cache(), settings)


async def test_animein_search(service, settings):
    with respx.mock(base_url=PROXY_URL, assert_all_called=True) as mock:
        mock.get("/3/2/explore/movie", params={"keyword": "haikyuu"}).mock(
            return_value=Response(200, json=load("explore.json"))
        )
        result = await service.search("haikyuu")
        assert result.total == 2
        assert len(result.items) == 2
        assert result.items[0].title == "Haikyuu!! Second Season"
        assert result.items[0].genre == "Comedy,Drama,School,Shounen,Sports"


async def test_animein_search_cache_hit(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/movie", params={"keyword": "haikyuu"}).mock(
            return_value=Response(200, json=load("explore.json"))
        )
        first = await service.search("haikyuu")
        second = await service.search("haikyuu")
        assert first.items == second.items
        assert mock.calls.call_count == 1


async def test_animein_catalog_endpoints(service):
    with respx.mock(base_url=PROXY_URL, assert_all_called=True) as mock:
        mock.get("/3/2/explore/genre").mock(return_value=Response(200, json=load("genres.json")))
        mock.get("/3/2/home/data").mock(return_value=Response(200, json=load("home.json")))
        mock.get("/3/2/schedule/data").mock(return_value=Response(200, json=load("schedule.json")))
        mock.get("/data/movie/trailer/list", params={"id_movie": "2073"}).mock(
            return_value=Response(200, json=load("trailers.json"))
        )
        genres = await service.get_genres()
        assert genres and genres[0].name
        home = await service.get_home()
        assert home.hot
        assert home.setup_fyp_name
        schedule = await service.get_schedule()
        assert schedule
        trailers = await service.get_trailers("2073")
        assert trailers and trailers[0].name


async def test_animein_episodes_sorted_and_list_or_dict(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/movie/episode/2073").mock(
            return_value=Response(200, json=load("episodes.json"))
        )
        episodes = await service.get_episodes("2073")
        assert [e.index for e in episodes] == ["1", "25"]
        assert episodes[0].title == "Episode 1"
        assert mock.calls.call_count == 1


async def test_animein_detail_not_found(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/movie/detail/999").mock(return_value=Response(404, text="Not Found"))
        with pytest.raises(UpstreamNotFound):
            await service.get_anime("999")


async def test_animein_negative_cache(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/movie/detail/999").mock(return_value=Response(404, text="Not Found"))
        with pytest.raises(UpstreamNotFound):
            await service.get_anime("999")
        with pytest.raises(UpstreamNotFound):
            await service.get_anime("999")
        assert mock.calls.call_count == 1


async def test_animein_retry_then_success(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/movie", params={"keyword": "wistoria"}).mock(
            side_effect=[Response(500), Response(200, json=load("explore.json"))]
        )
        result = await service.search("wistoria")
        assert len(result.items) == 2


async def test_animein_upstream_error_after_retries(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/movie", params={"keyword": "x"}).mock(
            side_effect=[Response(500), Response(500), Response(500)]
        )
        with pytest.raises(UpstreamError):
            await service.search("x")


async def test_animein_single_flight(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/explore/genre").mock(return_value=Response(200, json=load("genres.json")))
        results = await asyncio.gather(
            service.get_genres(), service.get_genres(), service.get_genres()
        )
        assert all(r == results[0] for r in results)
        assert mock.calls.call_count == 1


async def test_animein_streams_grouped_by_quality(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/episode/streamnew/35969").mock(
            return_value=Response(200, json=load("streams.json"))
        )
        result = await service.get_streams("35969")
        assert result.episode.title == "Episode 25"
        assert set(result.streams) == {"360p", "480p", "720p"}
        assert result.streams["720p"][0].type == "direct"
        assert result.streams["480p"][0].name == "RAPSODI"
        assert result.episode_next is None


async def test_animein_chat(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/chat/data").mock(return_value=Response(200, json=load("chat.json")))
        data = await service.get_chat()
        assert data.refresh == "3000"
        assert len(data.chat) == 2
        top = data.chat[0]
        assert top.user_name == "kingoflegend1"
        assert top.user_pokemon == "136"
        assert top.id_chat_replay == "3728596"
        assert top.text_replay == "kayaknya oke"


async def test_animein_comments(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/3/2/comment/data", params={"id_episode": "5017", "sort": "top", "page": 1}).mock(
            return_value=Response(200, json=load("comments.json"))
        )
        data = await service.get_comments("5017", sort="top", page=1)
        assert data.count == 2
        assert data.id_movie == "341"
        assert data.comment[0].user_name == "Admin"
        assert data.comment[1].like == "3"
        assert data.cover and data.cover[0]["point"] == "10"


async def test_animein_ads(service):
    with respx.mock(base_url=PROXY_URL) as mock:
        mock.get("/data/ads/show", params={"tag": "FIGURE"}).mock(
            return_value=Response(200, json=load("ads.json"))
        )
        ad = await service.get_ads(tag="FIGURE")
        assert ad is not None
        assert ad.name == "Figur One Piece"
        assert ad.url_content_video.endswith(".mp4")
        assert ad.count_click == "4"
