import pytest
from httpx import ASGITransport, AsyncClient

from aiograpi_rest.dependencies import get_clients
from aiograpi_rest.main import app


class FakeClient:
    def __init__(self):
        self.calls = []

    async def insights_account(self):
        self.calls.append(("insights_account",))
        return {"accounts_reached": 1}

    async def insights_media_feed_all(self, post_type, time_frame, data_ordering, count, sleep=2):
        self.calls.append(
            ("insights_media_feed_all", post_type, time_frame, data_ordering, count, sleep)
        )
        return [{"pk": "1", "post_type": post_type}]

    async def insights_media(self, media_pk):
        self.calls.append(("insights_media", media_pk))
        return {"media_pk": media_pk, "reach": 5}


class FakeStorage:
    def __init__(self):
        self.client = FakeClient()

    async def get(self, sessionid):
        return self.client

    def close(self):
        pass


@pytest.fixture
def storage():
    fake = FakeStorage()
    app.dependency_overrides[get_clients] = lambda: fake
    yield fake
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_insights_account_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/insights/account", params={"sessionid": "sid"})
    assert response.status_code == 200
    assert response.json() == {"accounts_reached": 1}


@pytest.mark.asyncio
async def test_insights_media_feed_all_uses_defaults_and_awaits(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/insights/media/feed/all", params={"sessionid": "sid"})
    assert response.status_code == 200
    assert response.json()[0]["pk"] == "1"
    call = next(c for c in storage.client.calls if c[0] == "insights_media_feed_all")
    assert call[1:] == ("ALL", "TWO_YEARS", "REACH_COUNT", 0, 2)


@pytest.mark.asyncio
async def test_insights_media_awaits_client(storage):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get(
            "/insights/media", params={"sessionid": "sid", "media_pk": "1"}
        )
    assert response.status_code == 200
    assert response.json() == {"media_pk": 1, "reach": 5}
