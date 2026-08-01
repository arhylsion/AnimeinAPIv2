from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)

RETRYABLE_STATUS = {408, 425, 429, 500, 502, 503, 504}


class UpstreamError(Exception):
    pass


class UpstreamNotFound(UpstreamError):
    pass


class HttpClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        }
        self._client = httpx.AsyncClient(
            headers=self._headers,
            timeout=httpx.Timeout(settings.timeout),
            follow_redirects=True,
        )

    async def __aenter__(self) -> HttpClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._client.aclose()

    async def get_text(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> str:
        return await self._request("GET", url, params=params, headers=headers)

    async def get_json(
        self, url: str, params: dict[str, Any] | None = None, headers: dict[str, str] | None = None
    ) -> Any:
        text = await self._request("GET", url, params=params, headers=headers)
        try:
            return httpx.Response(200, content=text).json()
        except ValueError as exc:
            raise UpstreamError(f"Respons bukan JSON dari {url}") from exc

    async def post_form(
        self,
        url: str,
        data: dict[str, Any],
        headers: dict[str, str] | None = None,
    ) -> str:
        return await self._request("POST", url, data=data, headers=headers)

    async def _request(
        self,
        method: str,
        url: str,
        params: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> str:
        last_error: Exception | None = None
        for attempt in range(self._settings.retries + 1):
            try:
                resp = await self._client.request(
                    method, url, params=params, data=data, headers=headers
                )
                resp.raise_for_status()
                return resp.text
            except (httpx.HTTPStatusError, httpx.TransportError) as exc:
                last_error = exc
                status = getattr(exc, "response", None)
                status_code = status.status_code if status is not None else None
                if status_code == 404:
                    raise UpstreamNotFound(f"Upstream {url} -> HTTP 404") from exc
                if status_code is not None and status_code not in RETRYABLE_STATUS:
                    raise UpstreamError(f"Upstream {url} -> HTTP {status_code}") from exc
                logger.warning(
                    "Percobaan %d/%d untuk %s: %s",
                    attempt + 1,
                    self._settings.retries + 1,
                    url,
                    exc,
                )
                await asyncio.sleep(0.5 * (2**attempt))
        raise UpstreamError(f"Upstream {url} gagal setelah retry") from last_error
