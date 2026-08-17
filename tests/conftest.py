import httpx
import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from vaipex_api_automation.app import create_app
from vaipex_api_automation.client import ApiClient
from vaipex_api_automation.config import ApiEnvironment
from vaipex_api_automation.identities import IdentityProfile


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest_asyncio.fixture
async def client(app: FastAPI) -> AsyncClient:
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport, base_url="http://vaipex.test"
    ) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def api_client(app: FastAPI) -> ApiClient:
    environment = ApiEnvironment(base_url="http://vaipex.test")
    transport = httpx.ASGITransport(app=app)
    async with ApiClient(environment, transport=transport) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def admin_api_client(app: FastAPI) -> ApiClient:
    environment = ApiEnvironment(base_url="http://vaipex.test")
    transport = httpx.ASGITransport(app=app)
    async with ApiClient(
        environment,
        identity=IdentityProfile.ADMIN,
        transport=transport,
    ) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-admin-token"}


@pytest.fixture
def operator_headers() -> dict[str, str]:
    return {"Authorization": "Bearer demo-operator-token"}
