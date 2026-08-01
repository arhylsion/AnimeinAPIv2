from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any, Literal

from .client import UpstreamError, UpstreamNotFound

logger = logging.getLogger(__name__)

_NOT_FOUND = object()


@dataclass
class Cached:
    data: Any
    status: Literal["hit", "stale", "miss"]


@dataclass
class _Entry:
    value: Any
    created_at: float
    expires_at: float
    stale_until: float


class Cache:
    def __init__(self, max_size: int = 50_000) -> None:
        self._data: dict[str, _Entry] = {}
        self._pending: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()
        self._max = max_size

    async def get(
        self,
        key: str,
        ttl: float,
        fetch: Callable[[], Awaitable[Any]],
        stale_ttl: float | None = None,
        negative_ttl: float = 60.0,
    ) -> Cached:
        now = time.monotonic()
        entry = self._data.get(key)

        if entry is not None and now < entry.expires_at:
            if entry.value is _NOT_FOUND:
                raise UpstreamNotFound("Negative cache hit")
            return Cached(entry.value, "hit")

        if entry is not None and now < entry.stale_until:
            if entry.value is _NOT_FOUND:
                raise UpstreamNotFound("Negative cache hit")
            asyncio.create_task(self._refresh(key, ttl, stale_ttl, negative_ttl, fetch))
            return Cached(entry.value, "stale")

        return await self._load(key, ttl, stale_ttl, negative_ttl, fetch)

    async def _load(
        self,
        key: str,
        ttl: float,
        stale_ttl: float | None,
        negative_ttl: float,
        fetch: Callable[[], Awaitable[Any]],
    ) -> Cached:
        async with self._lock:
            pending = self._pending.get(key)
            if pending is not None:
                value = await asyncio.shield(pending)
                return Cached(value, "hit")

            future: asyncio.Future = asyncio.get_running_loop().create_future()
            self._pending[key] = future

        try:
            try:
                value = await fetch()
            except UpstreamNotFound:
                await self._put(key, _NOT_FOUND, negative_ttl)
                self._reject(future, UpstreamNotFound("Negative cache hit"))
                raise
            await self._put(key, value, ttl, stale_ttl)
            if not future.done():
                future.set_result(value)
        except Exception:
            self._reject(future, UpstreamError(f"Fetch gagal untuk {key}"))
            raise
        finally:
            self._pending.pop(key, None)

        return Cached(value, "miss")

    @staticmethod
    def _reject(future: asyncio.Future, exc: BaseException) -> None:
        if not future.done():
            future.set_exception(exc)
        if not future.cancelled():
            future.exception()

    async def _refresh(
        self,
        key: str,
        ttl: float,
        stale_ttl: float | None,
        negative_ttl: float,
        fetch: Callable[[], Awaitable[Any]],
    ) -> None:
        try:
            await self._load(key, ttl, stale_ttl, negative_ttl, fetch)
            logger.info("SWR refresh selesai untuk %s", key)
        except Exception:
            logger.exception("SWR refresh gagal untuk %s", key)

    async def _put(self, key: str, value: Any, ttl: float, stale_ttl: float | None = None) -> None:
        now = time.monotonic()
        stale_factor = stale_ttl if stale_ttl is not None else ttl * 2
        entry = _Entry(
            value=value,
            created_at=now,
            expires_at=now + ttl,
            stale_until=now + ttl + stale_factor,
        )
        async with self._lock:
            self._data[key] = entry
            if len(self._data) > self._max:
                self._cleanup()

    def _cleanup(self) -> None:
        now = time.monotonic()
        expired = [k for k, e in self._data.items() if now >= e.expires_at]
        for k in expired:
            del self._data[k]
        if len(self._data) <= self._max:
            return
        oldest = min(self._data, key=lambda k: self._data[k].created_at)
        del self._data[oldest]

    @property
    def size(self) -> int:
        return len(self._data)
