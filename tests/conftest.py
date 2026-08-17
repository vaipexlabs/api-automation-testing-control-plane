import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from vaipex_api_automation.app import create_app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    transport = ASGITransport(app=create_app())
    async with AsyncClient(
        transport=transport, base_url="http://vaipex.test"
    ) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-admin-token"}


@pytest.fixture
def operator_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-operator-token"}
