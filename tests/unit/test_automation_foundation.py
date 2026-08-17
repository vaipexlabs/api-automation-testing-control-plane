import httpx
import pytest

from vaipex_api_automation.app import create_app
from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.config import ApiEnvironment
from vaipex_api_automation.identities import IdentityProfile, authorization_headers
from vaipex_api_automation.test_data import OrderPayloadFactory


def test_environment_defaults_are_safe_and_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for variable in (
        "VAIPEX_API_BASE_URL",
        "VAIPEX_API_TIMEOUT_SECONDS",
        "VAIPEX_API_CORRELATION_PREFIX",
    ):
        monkeypatch.delenv(variable, raising=False)

    environment = ApiEnvironment.from_env()

    assert environment.base_url == "http://127.0.0.1:8080"
    assert environment.timeout_seconds == 5.0
    assert environment.correlation_prefix == "vaipex-api-test"


def test_environment_overrides_are_validated(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAIPEX_API_BASE_URL", "https://api.example.test/")
    monkeypatch.setenv("VAIPEX_API_TIMEOUT_SECONDS", "2.5")
    monkeypatch.setenv("VAIPEX_API_CORRELATION_PREFIX", "ci-run")

    environment = ApiEnvironment.from_env()

    assert environment == ApiEnvironment(
        base_url="https://api.example.test",
        timeout_seconds=2.5,
        correlation_prefix="ci-run",
    )


@pytest.mark.parametrize(
    ("base_url", "timeout", "message"),
    [
        ("localhost:8080", 5.0, "absolute HTTP"),
        ("ftp://example.test", 5.0, "absolute HTTP"),
        ("https://example.test", 0, "greater than zero"),
    ],
)
def test_invalid_environment_is_rejected(
    base_url: str, timeout: float, message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        ApiEnvironment(base_url=base_url, timeout_seconds=timeout)


def test_identity_helper_keeps_anonymous_requests_credential_free() -> None:
    assert authorization_headers(IdentityProfile.ANONYMOUS) == {}
    assert authorization_headers(IdentityProfile.ADMIN) == {
        "Authorization": "Bearer demo-admin-token"
    }


def test_payload_factory_is_deterministic_and_covers_boundaries() -> None:
    factory = OrderPayloadFactory()

    assert factory.minimum() == {
        "product_id": "product-401",
        "quantity": 1,
        "priority": "standard",
    }
    assert factory.maximum() == {
        "product_id": "product-402",
        "quantity": 100,
        "priority": "expedited",
    }
    assert factory.malformed()["unexpected"] is True


async def test_shared_client_adds_identity_and_correlation_evidence() -> None:
    transport = httpx.ASGITransport(app=create_app())
    environment = ApiEnvironment(
        base_url="http://vaipex.test", correlation_prefix="unit"
    )

    async with ApiClient(environment, transport=transport) as client:
        first = await client.list_orders()
        second = await client.list_orders(identity=IdentityProfile.OTHER_OPERATOR)

    assert first.status_code == 200
    assert first.headers["X-Correlation-ID"] == "unit-0001"
    assert first.json()["items"][0]["owner_id"] == "user-001"
    assert second.headers["X-Correlation-ID"] == "unit-0002"
    assert second.json()["items"][0]["owner_id"] == "user-002"


async def test_shared_client_carries_controlled_failure_context() -> None:
    transport = httpx.ASGITransport(app=create_app())
    environment = ApiEnvironment(base_url="http://vaipex.test")

    async with ApiClient(environment, transport=transport) as client:
        response = await client.list_orders(failure_mode="dependency")

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "dependency_unavailable"
