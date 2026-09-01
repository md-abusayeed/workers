from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Any, Mapping

import httpx


@dataclass(frozen=True, slots=True)
class Config:
    endpoint: str
    token: str | None
    timeout: float = 30.0
    retries: int = 3
    backoff: float = 0.5


class WorkerClient:
    __slots__ = ("_config", "_client")

    def __init__(self, config: Config) -> None:
        self._config = config
        self._client = httpx.AsyncClient(
            base_url=config.endpoint.rstrip("/"),
            headers={
                "accept": "application/json",
                "content-type": "application/json",
                **(
                    {"authorization": f"Bearer {config.token}"}
                    if config.token
                    else {}
                ),
            },
            timeout=httpx.Timeout(config.timeout),
            limits=httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
            ),
            http2=True,
            follow_redirects=False,
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> WorkerClient:
        return self

    async def __aexit__(self, *_: object) -> None:
        await self.close()

    async def request(
        self,
        method: str,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
        payload: Any = None,
    ) -> Any:
        last_error: Exception | None = None

        for attempt in range(self._config.retries + 1):
            try:
                response = await self._client.request(
                    method,
                    path,
                    params=params,
                    json=payload,
                )

                if response.status_code < 500:
                    response.raise_for_status()
                    return self._decode(response)

                last_error = WorkerError(
                    f"upstream returned {response.status_code}: "
                    f"{response.text[:1024]}"
                )

            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc

            if attempt < self._config.retries:
                await asyncio.sleep(
                    self._config.backoff * (2**attempt)
                )

        raise WorkerError(
            "request failed after retries"
        ) from last_error

    @staticmethod
    def _decode(response: httpx.Response) -> Any:
        content_type = response.headers.get("content-type", "")

        if "application/json" in content_type:
            return response.json()

        return response.text

    async def get(
        self,
        path: str,
        *,
        params: Mapping[str, Any] | None = None,
    ) -> Any:
        return await self.request(
            "GET",
            path,
            params=params,
        )

    async def post(
        self,
        path: str,
        *,
        payload: Any = None,
    ) -> Any:
        return await self.request(
            "POST",
            path,
            payload=payload,
        )


class WorkerError(RuntimeError):
    pass


async def main() -> None:
    endpoint = os.environ["WORKER_URL"]
    token = os.getenv("WORKER_TOKEN")

    async with WorkerClient(
        Config(
            endpoint=endpoint,
            token=token,
        )
    ) as worker:
        result = await worker.get("/api/status")
        print(result)


if __name__ == "__main__":
    asyncio.run(main())
