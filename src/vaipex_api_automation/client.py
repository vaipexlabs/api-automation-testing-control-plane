"""Reusable asynchronous HTTPX client for the reference API contract."""

from collections.abc import Mapping
from types import TracebackType
from typing import Any, Self

import httpx

from vaipex_api_automation.config import ApiEnvironment
from vaipex_api_automation.identities import IdentityProfile, authorization_headers


class ApiClient:
    def __init__(
        self,
        environment: ApiEnvironment,
        identity: IdentityProfile = IdentityProfile.OPERATOR,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.environment = environment
        self.identity = identity
        self._sequence = 0
        self._http = httpx.AsyncClient(
            base_url=environment.base_url,
            timeout=environment.timeout_seconds,
            transport=transport,
        )

    async def __aenter__(self) -> Self:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.aclose()

    async def aclose(self) -> None:
        await self._http.aclose()

    def _headers(
        self,
        *,
        identity: IdentityProfile | None = None,
        failure_mode: str | None = None,
        extra: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        self._sequence += 1
        selected_identity = identity or self.identity
        headers = {
            **authorization_headers(selected_identity),
            "X-Correlation-ID": (
                f"{self.environment.correlation_prefix}-{self._sequence:04d}"
            ),
        }
        if failure_mode:
            headers["X-Vaipex-Failure"] = failure_mode
        if extra:
            headers.update(extra)
        return headers

    async def request(
        self,
        method: str,
        path: str,
        *,
        identity: IdentityProfile | None = None,
        failure_mode: str | None = None,
        headers: Mapping[str, str] | None = None,
        **kwargs: Any,
    ) -> httpx.Response:
        return await self._http.request(
            method,
            path,
            headers=self._headers(
                identity=identity,
                failure_mode=failure_mode,
                extra=headers,
            ),
            **kwargs,
        )

    async def list_orders(self, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", "/v1/orders", **kwargs)

    async def get_order(self, order_id: str, **kwargs: Any) -> httpx.Response:
        return await self.request("GET", f"/v1/orders/{order_id}", **kwargs)

    async def create_order(
        self, payload: Mapping[str, object], **kwargs: Any
    ) -> httpx.Response:
        return await self.request("POST", "/v1/orders", json=payload, **kwargs)

    async def replace_order(
        self, order_id: str, payload: Mapping[str, object], **kwargs: Any
    ) -> httpx.Response:
        return await self.request(
            "PUT", f"/v1/orders/{order_id}", json=payload, **kwargs
        )

    async def patch_order(
        self, order_id: str, payload: Mapping[str, object], **kwargs: Any
    ) -> httpx.Response:
        return await self.request(
            "PATCH", f"/v1/orders/{order_id}", json=payload, **kwargs
        )

    async def delete_order(self, order_id: str, **kwargs: Any) -> httpx.Response:
        return await self.request("DELETE", f"/v1/orders/{order_id}", **kwargs)

    async def head_order(self, order_id: str, **kwargs: Any) -> httpx.Response:
        return await self.request("HEAD", f"/v1/orders/{order_id}", **kwargs)

    async def options_orders(self, **kwargs: Any) -> httpx.Response:
        return await self.request("OPTIONS", "/v1/orders", **kwargs)

    async def reset(self, **kwargs: Any) -> httpx.Response:
        return await self.request(
            "POST",
            "/v1/admin/reset",
            identity=IdentityProfile.ADMIN,
            **kwargs,
        )
