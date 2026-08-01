from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class AnimeSummary(BaseModel):
    id: str
    title: str
    synopsis: str | None = None
    synonyms: str | None = None
    image_poster: str | None = None
    image_cover: str | None = None
    type: str | None = None
    year: str | None = None
    day: str | None = None
    status: str | None = None
    views: str | None = None
    favorites: str | None = None
    genre: str | None = None
    time: str | None = None
    key_time: str | None = None


class AnimeDetail(AnimeSummary):
    day: str | None = None
    aired_start: str | None = None
    aired_end: str | None = None
    studio: str | None = None
    time: str | None = None
    key_status: str | None = None


class Episode(BaseModel):
    id: str
    index: str
    title: str
    views: str | None = None
    id_movie: str | None = None
    key_time: str | None = None
    image: str | None = None
    is_new: bool | str | None = None


class StreamInfo(BaseModel):
    id: str
    link: str
    quality: str
    key_file_size: str | float | None = None
    name: str | None = None
    type: str | None = None
    domain: str | None = None
    username: str | None = None
    server_id: str | None = None


class StreamResponse(BaseModel):
    episode: Episode
    episode_next: Episode | None = None
    streams: dict[str, list[StreamInfo]] = Field(default_factory=dict)


class SearchResult(BaseModel):
    page: int
    total: int | None = None
    items: list[AnimeSummary]


class Genre(BaseModel):
    id: str
    name: str
    image: str | None = None
    group: str | None = None


class Slider(BaseModel):
    id: str
    link: str | None = None
    image: str | None = None
    type: str | None = None


class Trailer(BaseModel):
    id: str
    name: str | None = None
    url_youtube: str | None = None
    thumbnail: str | None = None
    time: str | None = None
    is_new: bool | str | None = None


class ChatMessage(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    user_pokemon: str | None = None
    image_masukotto: str | None = None
    image_url: str | None = None
    image_url_replay: str | None = None
    user_name_replay: str | None = None
    text: str | None = None
    text_replay: str | None = None
    time: str | None = None
    time_hour: str | None = None
    time_iso: str | None = None
    time_updated: str | None = None
    id_chat_replay: str | None = None
    type: str | None = None
    pro: int | None = None
    rank: int | None = None
    movie: Any = None


class ChatData(BaseModel):
    chat: list[ChatMessage] = Field(default_factory=list)
    chat_update: list[ChatMessage] = Field(default_factory=list)
    news: Any = None
    refresh: str | None = None


class Comment(BaseModel):
    id: str
    user_id: str | None = None
    user_name: str | None = None
    user_pokemon: str | None = None
    text: str | None = None
    time: str | None = None
    time_updated: str | None = None
    like: str | None = None
    dislike: str | None = None
    score: str | None = None
    replay: Any = None
    is_like: str | None = None
    pro: int | None = None
    rank: int | None = None


class CommentList(BaseModel):
    comment: list[Comment] = Field(default_factory=list)
    cover: list[Any] = Field(default_factory=list)
    poster: list[Any] = Field(default_factory=list)
    count: str | int | None = None
    id_movie: str | None = None


class Ad(BaseModel):
    id: str | int
    name: str | None = None
    tag: str | None = None
    url_content_video: str | None = None
    url_content_image: str | None = None
    url_redirect: str | None = None
    count_view: str | int | None = None
    count_click: str | int | None = None


class HomeData(BaseModel):
    slider: list[Slider] = Field(default_factory=list)
    hot: list[AnimeSummary] = Field(default_factory=list)
    new: list[AnimeSummary] = Field(default_factory=list)
    today: list[AnimeSummary] = Field(default_factory=list)
    popular: list[AnimeSummary] = Field(default_factory=list)
    waiting: list[AnimeSummary] = Field(default_factory=list)
    random: list[AnimeSummary] = Field(default_factory=list)
    trailer: list[AnimeSummary] = Field(default_factory=list)
    setup_fyp_flag: str | None = None
    setup_fyp_name: str | None = None


class ErrorResponse(BaseModel):
    detail: str
