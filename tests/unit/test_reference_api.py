from httpx import AsyncClient


async def test_health_contract_and_correlation(client: AsyncClient) -> None:
    response = await client.get(
        "/health/ready", headers={"X-Correlation-ID": "test-correlation-001"}
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "service": "vaipex-api-quality-reference",
        "version": "0.1.0",
    }
    assert response.headers["X-Correlation-ID"] == "test-correlation-001"
    assert response.headers["X-Service-Version"] == "0.1.0"


async def test_openapi_describes_resource_and_security_contract(
    client: AsyncClient,
) -> None:
    document = (await client.get("/openapi.json")).json()

    assert document["info"]["title"] == "Vaipex API Automation Reference Service"
    assert "VaipexDemoBearer" in document["components"]["securitySchemes"]
    assert set(document["paths"]["/v1/orders/{order_id}"]) >= {
        "get",
        "put",
        "patch",
        "delete",
        "head",
        "options",
    }


async def test_order_routes_require_authentication(client: AsyncClient) -> None:
    response = await client.get("/v1/orders")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "unauthorized"
    assert response.headers["WWW-Authenticate"] == "Bearer"


async def test_operator_sees_only_owned_resources(
    client: AsyncClient, operator_headers: dict[str, str]
) -> None:
    collection = await client.get("/v1/orders", headers=operator_headers)
    hidden = await client.get("/v1/orders/order-002", headers=operator_headers)

    assert collection.status_code == 200
    assert collection.json()["count"] == 1
    assert collection.json()["items"][0]["owner_id"] == "user-001"
    assert hidden.status_code == 404


async def test_viewer_cannot_modify_owned_resource(client: AsyncClient) -> None:
    response = await client.patch(
        "/v1/orders/order-003",
        headers={"Authorization": "Bearer demo-viewer-token"},
        json={"quantity": 5},
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden"


async def test_admin_reset_restores_deterministic_seed(
    client: AsyncClient, admin_headers: dict[str, str]
) -> None:
    deleted = await client.delete("/v1/orders/order-001", headers=admin_headers)
    reset = await client.post("/v1/admin/reset", headers=admin_headers)
    collection = await client.get("/v1/orders", headers=admin_headers)

    assert deleted.status_code == 204
    assert reset.json() == {"restored_orders": 3, "status": "reset"}
    assert collection.json()["count"] == 3


async def test_controlled_failures_are_explicit(
    client: AsyncClient, operator_headers: dict[str, str]
) -> None:
    expectations = {
        "dependency": (503, "dependency_unavailable"),
        "rate-limit": (429, "rate_limited"),
        "timeout": (504, "dependency_timeout"),
    }

    for mode, (status_code, error_code) in expectations.items():
        response = await client.get(
            "/v1/orders",
            headers={**operator_headers, "X-Vaipex-Failure": mode},
        )
        assert response.status_code == status_code
        assert response.json()["error"]["code"] == error_code

    limited = await client.get(
        "/v1/orders",
        headers={**operator_headers, "X-Vaipex-Failure": "rate-limit"},
    )
    assert limited.headers["Retry-After"] == "30"
