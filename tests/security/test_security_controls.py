import httpx
import pytest
from fastapi import FastAPI

from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.identities import IdentityProfile
from vaipex_api_automation.test_data import OrderPayloadFactory

pytestmark = pytest.mark.security


@pytest.mark.parametrize("method", ["TRACE", "CONNECT"])
async def test_unsafe_transport_methods_are_explicitly_disabled(
    api_client: ApiClient, method: str
) -> None:
    response = await api_client.request(method, "/v1/orders")

    assert response.status_code == 405
    assert response.json() == {
        "error": {
            "code": "method_not_allowed",
            "message": f"{method} is disabled by API policy.",
        }
    }
    assert response.headers["Allow"] == ("GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS")
    assert method not in response.headers["Allow"]
    assert response.headers["X-Correlation-ID"]


@pytest.mark.parametrize(
    "headers",
    [
        {},
        {"Authorization": "Bearer unknown-token"},
        {"Authorization": "Basic ZGVtbzpkZW1v"},
    ],
)
async def test_missing_invalid_and_wrong_scheme_credentials_are_rejected(
    app: FastAPI, headers: dict[str, str]
) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport, base_url="http://vaipex.test"
    ) as client:
        response = await client.get("/v1/orders", headers=headers)

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.headers["Cache-Control"] == "no-store"
    assert "unknown-token" not in response.text


async def test_viewer_reads_owned_resource_but_cannot_modify(
    api_client: ApiClient,
) -> None:
    read = await api_client.get_order("order-003", identity=IdentityProfile.VIEWER)
    create = await api_client.create_order(
        OrderPayloadFactory().valid(), identity=IdentityProfile.VIEWER
    )
    patch = await api_client.patch_order(
        "order-003", {"quantity": 8}, identity=IdentityProfile.VIEWER
    )
    delete = await api_client.delete_order("order-003", identity=IdentityProfile.VIEWER)

    assert read.status_code == 200
    for response in (create, patch, delete):
        assert response.status_code == 403
        assert response.json()["error"]["code"] == "forbidden"
        assert response.headers["Cache-Control"] == "no-store"


async def test_cross_owner_resource_is_indistinguishable_from_unknown(
    api_client: ApiClient,
) -> None:
    replacement = OrderPayloadFactory().replacement()
    responses = [
        await api_client.get_order("order-002"),
        await api_client.replace_order("order-002", replacement),
        await api_client.patch_order("order-002", {"quantity": 8}),
        await api_client.delete_order("order-002"),
        await api_client.head_order("order-002"),
    ]
    unknown = await api_client.get_order("order-999")

    for response in responses:
        assert response.status_code == 404
        if response.request.method != "HEAD":
            assert response.json() == unknown.json()
    assert responses[-1].content == b""


async def test_admin_can_modify_resource_across_ownership_boundary(
    admin_api_client: ApiClient,
) -> None:
    response = await admin_api_client.patch_order("order-002", {"quantity": 12})

    assert response.status_code == 200
    assert response.json()["owner_id"] == "user-002"
    assert response.json()["quantity"] == 12


async def test_options_is_public_without_advertising_disabled_methods(
    api_client: ApiClient,
) -> None:
    response = await api_client.options_orders(identity=IdentityProfile.ANONYMOUS)

    assert response.status_code == 204
    assert "TRACE" not in response.headers["Allow"]
    assert "CONNECT" not in response.headers["Allow"]


async def test_non_admin_cannot_reset_shared_state(api_client: ApiClient) -> None:
    response = await api_client.request("POST", "/v1/admin/reset")

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"
    assert response.headers["Cache-Control"] == "no-store"
