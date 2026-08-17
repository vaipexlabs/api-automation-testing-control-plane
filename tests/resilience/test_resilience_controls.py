import asyncio

import httpx
import pytest

from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.config import ApiEnvironment
from vaipex_api_automation.test_data import OrderPayloadFactory

pytestmark = pytest.mark.resilience


@pytest.mark.parametrize(
    ("mode", "status", "code"),
    [
        ("rate-limit", 429, "rate_limited"),
        ("dependency", 503, "dependency_unavailable"),
        ("timeout", 504, "dependency_timeout"),
    ],
)
async def test_controlled_failures_are_explicit_and_correlated(
    api_client: ApiClient, mode: str, status: int, code: str
) -> None:
    response = await api_client.list_orders(failure_mode=mode)

    assert response.status_code == status
    assert response.json()["error"]["code"] == code
    assert response.headers["X-Correlation-ID"]
    if status == 429:
        assert response.headers["Retry-After"] == "30"


async def test_retry_policy_recovers_from_transient_failures() -> None:
    attempts = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            return httpx.Response(503, json={"error": {"code": "unavailable"}})
        return httpx.Response(200, json={"status": "recovered"})

    environment = ApiEnvironment(base_url="http://vaipex.test")
    async with ApiClient(environment, transport=httpx.MockTransport(handler)) as client:
        response, used_attempts = await client.request_with_retry(
            "GET", "/dependency", max_attempts=3
        )

    assert response.status_code == 200
    assert response.json()["status"] == "recovered"
    assert used_attempts == 3


async def test_retry_policy_stops_at_the_configured_limit() -> None:
    transport = httpx.MockTransport(lambda request: httpx.Response(504))
    environment = ApiEnvironment(base_url="http://vaipex.test")
    async with ApiClient(environment, transport=transport) as client:
        response, attempts = await client.request_with_retry(
            "GET", "/dependency", max_attempts=2
        )

    assert response.status_code == 504
    assert attempts == 2


async def test_concurrent_idempotent_posts_create_one_resource(
    api_client: ApiClient,
) -> None:
    payload = OrderPayloadFactory().valid()
    responses = await asyncio.gather(
        *[
            api_client.create_order(
                payload, headers={"Idempotency-Key": "checkout-attempt-001"}
            )
            for _ in range(10)
        ]
    )

    assert {response.status_code for response in responses} == {201}
    assert len({response.json()["order_id"] for response in responses}) == 1
    assert (
        sum(
            response.headers["Idempotency-Replayed"] == "false"
            for response in responses
        )
        == 1
    )


async def test_idempotency_keys_are_scoped_to_identity(
    api_client: ApiClient, admin_api_client: ApiClient
) -> None:
    payload = OrderPayloadFactory().valid()
    operator = await api_client.create_order(
        payload, headers={"Idempotency-Key": "shared-client-key"}
    )
    admin = await admin_api_client.create_order(
        payload, headers={"Idempotency-Key": "shared-client-key"}
    )

    assert operator.json()["order_id"] != admin.json()["order_id"]
