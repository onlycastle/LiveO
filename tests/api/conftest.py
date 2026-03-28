import pytest
from httpx import AsyncClient, ASGITransport
from starlette.testclient import TestClient

from backend.server import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def ws_client():
    """WebSocket 테스트용 동기 TestClient."""
    return TestClient(app)
