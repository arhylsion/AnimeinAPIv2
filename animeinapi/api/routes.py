from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request

from ..core.client import UpstreamError, UpstreamNotFound
from ..core.constants import SORTS
from ..core.service import AnimeinService
from ..models import (
    Ad,
    AnimeDetail,
    AnimeSummary,
    ChatData,
    CommentList,
    Episode,
    ErrorResponse,
    Genre,
    HomeData,
    SearchResult,
    StreamResponse,
    Trailer,
)

router = APIRouter(prefix="/api", responses={502: {"model": ErrorResponse}})

DAY_PATTERN = "^(MINGGU|SENIN|SELASA|RABU|KAMIS|JUMAT|SABTU|RANDOM)$"


def get_service(request: Request) -> AnimeinService:
    return request.app.state.service


Svc = Annotated[AnimeinService, Depends(get_service)]


def _err(exc: UpstreamError) -> HTTPException:
    if isinstance(exc, UpstreamNotFound):
        return HTTPException(status_code=404, detail=str(exc))
    return HTTPException(status_code=502, detail=f"Upstream error: {exc}")


@router.get("/search")
async def search(
    service: Svc,
    q: str = Query(""),
    page: int = Query(0, ge=0),
    sort: str = Query("views", pattern=f"^({'|'.join(SORTS)})$"),
    genre: str = Query(""),
) -> SearchResult:
    try:
        return await service.search(q, page=page, sort=sort, genre=genre)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/genres")
async def genres(service: Svc) -> list[Genre]:
    try:
        return await service.get_genres()
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/home")
async def home(
    service: Svc,
    day: str | None = Query(None, pattern=DAY_PATTERN),
    limit: int = Query(16, ge=1, le=100),
) -> HomeData:
    try:
        return await service.get_home(day=day or _today(), limit=limit)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/schedule")
async def schedule(
    service: Svc,
    day: str | None = Query(None, pattern=DAY_PATTERN),
) -> list[AnimeSummary]:
    try:
        return await service.get_schedule(day=day or _today())
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/anime/{anime_id}")
async def anime_detail(service: Svc, anime_id: str) -> AnimeDetail:
    try:
        return await service.get_anime(anime_id)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/anime/{anime_id}/episodes")
async def anime_episodes(
    service: Svc,
    anime_id: str,
    page: int = Query(0, ge=0),
) -> list[Episode]:
    try:
        return await service.get_episodes(anime_id, page=page)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/anime/{anime_id}/trailers")
async def anime_trailers(service: Svc, anime_id: str) -> list[Trailer]:
    try:
        return await service.get_trailers(anime_id)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/episode/{episode_id}/streams")
async def episode_streams(service: Svc, episode_id: str) -> StreamResponse:
    try:
        return await service.get_streams(episode_id)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/chat")
async def chat(
    service: Svc,
    highest_id: str = Query(""),
    lowest_id: str = Query(""),
) -> ChatData:
    try:
        return await service.get_chat(highest_id=highest_id, lowest_id=lowest_id)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/episode/{episode_id}/comments")
async def episode_comments(
    service: Svc,
    episode_id: str,
    sort: str = Query("new", pattern="^(top|new)$"),
    page: int = Query(0, ge=0),
) -> CommentList:
    try:
        return await service.get_comments(episode_id, sort=sort, page=page)
    except UpstreamError as exc:
        raise _err(exc) from exc


@router.get("/ads")
async def ads(
    service: Svc,
    tag: str = Query(""),
) -> Ad | None:
    try:
        return await service.get_ads(tag=tag)
    except UpstreamError as exc:
        raise _err(exc) from exc


def _today() -> str:
    from datetime import datetime, timedelta, timezone

    from ..core.constants import WEEKDAY_INDONESIAN

    wib = datetime.now(timezone(timedelta(hours=7)))
    return WEEKDAY_INDONESIAN[wib.weekday()]
