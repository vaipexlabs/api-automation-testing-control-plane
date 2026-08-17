import pytest

from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.test_data import OrderPayloadFactory

pytestmark = pytest.mark.functional


async def test_get_collection_and_resource_contract(api_client: ApiClient) -> None:
    collection = await api_client.list_orders()
    resource = await api_client.get_order("order-001")

    assert collection.status_code == 200
    assert collection.json()["count"] == 1
    assert collection.json()["items"][0]["order_id"] == "order-001"
    assert resource.status_code == 200
    assert resource.json()["owner_id"] == "user-001"
    assert resource.headers["X-Service-Version"] == "0.1.0"


async def test_get_unknown_resource_has_standard_error(api_client: ApiClient) -> None:
    response = await api_client.get_order("order-999")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "not_found", "message": "Order was not found."}
    }


async def test_post_creates_retrievable_resource(api_client: ApiClient) -> None:
    payload = OrderPayloadFactory().valid(quantity=7)

    created = await api_client.create_order(payload)
    order_id = created.json()["order_id"]
    retrieved = await api_client.get_order(order_id)

    assert created.status_code == 201
    assert created.headers["Location"] == f"/v1/orders/{order_id}"
    assert created.json() == retrieved.json()
    assert created.json()["owner_id"] == "user-001"
    assert created.json()["status"] == "pending"
    assert created.json()["version"] == 1


async def test_post_rejects_malformed_resource(api_client: ApiClient) -> None:
    response = await api_client.create_order(OrderPayloadFactory.malformed())

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"
    locations = {tuple(item["loc"]) for item in response.json()["error"]["details"]}
    assert ("body", "product_id") in locations
    assert ("body", "quantity") in locations
    assert ("body", "priority") in locations
    assert ("body", "unexpected") in locations


async def test_put_completely_replaces_resource_and_is_idempotent(
    api_client: ApiClient,
) -> None:
    payload = OrderPayloadFactory().replacement()

    first = await api_client.replace_order("order-001", payload)
    second = await api_client.replace_order("order-001", payload)

    assert first.status_code == 200
    assert first.json()["product_id"] == payload["product_id"]
    assert first.json()["status"] == "processing"
    assert first.json()["version"] == 2
    assert second.json() == first.json()


async def test_put_requires_the_complete_resource_contract(
    api_client: ApiClient,
) -> None:
    response = await api_client.replace_order(
        "order-001", {"quantity": 9, "status": "processing"}
    )

    assert response.status_code == 422
    missing_fields = {
        item["loc"][-1]
        for item in response.json()["error"]["details"]
        if item["type"] == "missing"
    }
    assert missing_fields == {"product_id"}


async def test_patch_changes_only_supplied_fields(api_client: ApiClient) -> None:
    before = await api_client.get_order("order-001")
    updated = await api_client.patch_order(
        "order-001", OrderPayloadFactory.patch(quantity=9)
    )

    assert updated.status_code == 200
    assert updated.json()["quantity"] == 9
    assert updated.json()["product_id"] == before.json()["product_id"]
    assert updated.json()["priority"] == before.json()["priority"]
    assert updated.json()["version"] == before.json()["version"] + 1


async def test_delete_removes_resource_and_defines_repetition(
    api_client: ApiClient,
) -> None:
    first = await api_client.delete_order("order-001")
    second = await api_client.delete_order("order-001")
    retrieved = await api_client.get_order("order-001")

    assert first.status_code == 204
    assert first.content == b""
    assert second.status_code == 404
    assert retrieved.status_code == 404


async def test_head_returns_representation_headers_without_body(
    api_client: ApiClient,
) -> None:
    response = await api_client.head_order("order-001")

    assert response.status_code == 200
    assert response.content == b""
    assert response.headers["ETag"] == '"order-001-v1"'
    assert response.headers["X-Resource-Owner"] == "user-001"


async def test_options_advertises_the_supported_method_contract(
    api_client: ApiClient,
) -> None:
    response = await api_client.options_orders()
    expected = "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS"

    assert response.status_code == 204
    assert response.content == b""
    assert response.headers["Allow"] == expected
    assert response.headers["Access-Control-Allow-Methods"] == expected


async def test_admin_can_read_resources_across_ownership_boundaries(
    admin_api_client: ApiClient,
) -> None:
    response = await admin_api_client.list_orders()

    assert response.status_code == 200
    assert response.json()["count"] == 3
    assert {item["owner_id"] for item in response.json()["items"]} == {
        "user-001",
        "user-002",
        "user-003",
    }
