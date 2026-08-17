import pytest
from pydantic import ValidationError

from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.models import Order
from vaipex_api_automation.test_data import OrderPayloadFactory

pytestmark = pytest.mark.contract


async def test_openapi_publishes_governed_order_operations(
    api_client: ApiClient,
) -> None:
    response = await api_client.request("GET", "/openapi.json")
    document = response.json()

    assert response.status_code == 200
    assert document["info"]["title"] == "Vaipex API Automation Reference Service"
    assert set(document["paths"]["/v1/orders"]) >= {"get", "post", "options"}
    assert set(document["paths"]["/v1/orders/{order_id}"]) >= {
        "get",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    }


async def test_success_response_satisfies_the_published_order_model(
    api_client: ApiClient,
) -> None:
    response = await api_client.get_order("order-001")
    order = Order.model_validate(response.json())

    assert response.status_code == 200
    assert order.order_id == "order-001"
    assert order.version == 1


@pytest.mark.parametrize("quantity", [1, 100])
async def test_quantity_boundaries_are_accepted(
    api_client: ApiClient, quantity: int
) -> None:
    response = await api_client.create_order(
        OrderPayloadFactory().valid(quantity=quantity)
    )

    assert response.status_code == 201
    assert response.json()["quantity"] == quantity


@pytest.mark.parametrize("quantity", [0, 101])
async def test_quantity_outside_contract_is_rejected(
    api_client: ApiClient, quantity: int
) -> None:
    response = await api_client.create_order(
        OrderPayloadFactory().valid(quantity=quantity)
    )

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


async def test_unknown_fields_and_invalid_enums_are_rejected(
    api_client: ApiClient,
) -> None:
    payload = OrderPayloadFactory().valid()
    payload.update(priority="urgent", internal_approval=True)
    response = await api_client.create_order(payload)

    assert response.status_code == 422
    locations = {item["loc"][-1] for item in response.json()["error"]["details"]}
    assert locations == {"priority", "internal_approval"}


async def test_response_model_rejects_contract_drift(api_client: ApiClient) -> None:
    payload = (await api_client.get_order("order-001")).json()
    payload.pop("owner_id")

    with pytest.raises(ValidationError):
        Order.model_validate(payload)


async def test_pagination_filtering_and_sorting(admin_api_client: ApiClient) -> None:
    page = await admin_api_client.request(
        "GET", "/v1/orders", params={"page": 1, "page_size": 2, "sort": "-quantity"}
    )
    filtered = await admin_api_client.request(
        "GET", "/v1/orders", params={"priority": "expedited"}
    )

    assert page.status_code == 200
    assert page.json()["total"] == 3
    assert page.json()["count"] == 2
    assert [item["quantity"] for item in page.json()["items"]] == [4, 2]
    assert filtered.json()["count"] == 1
    assert filtered.json()["items"][0]["order_id"] == "order-002"


@pytest.mark.parametrize(
    ("parameter", "value"),
    [("page", 0), ("page_size", 0), ("page_size", 101), ("sort", "owner_id")],
)
async def test_invalid_collection_controls_are_rejected(
    api_client: ApiClient, parameter: str, value: object
) -> None:
    response = await api_client.request("GET", "/v1/orders", params={parameter: value})

    assert response.status_code == 422


async def test_conditional_get_returns_not_modified(api_client: ApiClient) -> None:
    first = await api_client.get_order("order-001")
    cached = await api_client.get_order(
        "order-001", headers={"If-None-Match": first.headers["ETag"]}
    )

    assert first.headers["Cache-Control"] == "private, max-age=0, must-revalidate"
    assert cached.status_code == 304
    assert cached.content == b""
    assert cached.headers["ETag"] == first.headers["ETag"]
