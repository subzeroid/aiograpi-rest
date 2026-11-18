import json

import pytest
from tinydb import Query

from aiograpi_rest.storages import ClientStorage


class FakeClient:
    def __init__(self):
        self.sessionid = "sid"
        self.settings = {"authorization_data": {"sessionid": self.sessionid}}
        self.proxy = None
        self.timeline_called = False

    def set_settings(self, settings):
        self.settings = settings
        return True

    def set_proxy(self, proxy):
        self.proxy = proxy
        return True

    def get_settings(self):
        return self.settings

    async def get_timeline_feed(self):
        self.timeline_called = True
        return {"ok": True}


class FakeClientWithPrivateProxy(FakeClient):
    class Private:
        proxy = "http://private-proxy.example:8080"

    def __init__(self):
        super().__init__()
        self.proxy = "http://public-proxy.example:8080"
        self.private = self.Private()


@pytest.mark.asyncio
async def test_get_restores_settings_and_validates_timeline(tmp_path, monkeypatch):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    storage.db.insert({"sessionid": "sid", "settings": json.dumps({"x": 1})})

    client = await storage.get("sid")

    assert client.settings == {"x": 1}
    assert client.timeline_called is True


def test_set_persists_client_settings(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    assert storage.set(FakeClient()) is True
    row = storage.db.all()[0]
    assert row["sessionid"] == "sid"
    assert json.loads(row["settings"]) == {"authorization_data": {"sessionid": "sid"}}


def test_set_replaces_existing_settings_and_persists_proxy(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    original = FakeClient()
    assert storage.set(original) is True

    updated = FakeClient()
    updated.settings = {"authorization_data": {"sessionid": "sid"}, "locale": "en_US"}
    updated.proxy = "http://proxy.example:8080"
    assert storage.set(updated) is True

    rows = storage.db.search(Query().sessionid == "sid")
    assert len(rows) == 1
    assert json.loads(rows[0]["settings"]) == {"authorization_data": {"sessionid": "sid"}, "locale": "en_US"}
    assert rows[0]["proxy"] == "http://proxy.example:8080"


def test_set_prefers_private_transport_proxy(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClientWithPrivateProxy)

    assert storage.set(FakeClientWithPrivateProxy()) is True

    row = storage.db.all()[0]
    assert row["proxy"] == "http://private-proxy.example:8080"


@pytest.mark.asyncio
async def test_get_restores_persisted_proxy(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    storage.db.insert(
        {
            "sessionid": "sid",
            "settings": json.dumps({"authorization_data": {"sessionid": "sid"}}),
            "proxy": "http://proxy.example:8080",
        }
    )

    client = await storage.get("sid")

    assert client.proxy == "http://proxy.example:8080"
    assert client.timeline_called is True


def test_storage_path_can_come_from_environment(tmp_path, monkeypatch):
    db_path = tmp_path / "env-db.json"
    monkeypatch.setenv("AIOGRAPI_REST_DB_PATH", str(db_path))

    storage = ClientStorage(client_factory=FakeClient)
    storage.db.insert({"sessionid": "sid", "settings": "{}"})

    assert db_path.exists()


@pytest.mark.asyncio
async def test_get_missing_session_raises_helpful_error(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    with pytest.raises(Exception, match="Session not found"):
        await storage.get("missing")


def test_client_factory_produces_configured_client(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    cl = storage.client()
    assert isinstance(cl, FakeClient)
    assert cl.request_timeout == 0.1


def test_close_is_a_no_op(tmp_path):
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    assert storage.close() is None


@pytest.mark.asyncio
async def test_timeline_on_get_always_calls_every_get(tmp_path, monkeypatch):
    monkeypatch.delenv("AIOGRAPI_REST_TIMELINE_ON_GET", raising=False)
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    storage.db.insert({"sessionid": "sid", "settings": json.dumps({"x": 1})})

    first = await storage.get("sid")
    second = await storage.get("sid")

    assert first.timeline_called is True
    assert second.timeline_called is True


@pytest.mark.asyncio
async def test_timeline_on_get_never_skips_warmup(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOGRAPI_REST_TIMELINE_ON_GET", "never")
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    storage.db.insert({"sessionid": "sid", "settings": json.dumps({"x": 1})})

    client = await storage.get("sid")

    assert client.timeline_called is False


@pytest.mark.asyncio
async def test_timeline_on_get_interval_throttles_per_session(tmp_path, monkeypatch):
    monkeypatch.setenv("AIOGRAPI_REST_TIMELINE_ON_GET", "interval")
    monkeypatch.setenv("AIOGRAPI_REST_TIMELINE_INTERVAL_SECONDS", "60")
    storage = ClientStorage(db_path=tmp_path / "db.json", client_factory=FakeClient)
    storage.db.insert({"sessionid": "sid", "settings": json.dumps({"x": 1})})

    timeline_times = [100.0, 100.0, 200.0]
    call_count = [0]

    def fake_monotonic():
        index = min(call_count[0], len(timeline_times) - 1)
        call_count[0] += 1
        return timeline_times[index]

    monkeypatch.setattr("aiograpi_rest.storages.time.monotonic", fake_monotonic)

    first = await storage.get("sid")
    second = await storage.get("sid")
    third = await storage.get("sid")

    assert first.timeline_called is True
    assert second.timeline_called is False
    assert third.timeline_called is True


def test_get_clients_dependency_yields_storage(monkeypatch, tmp_path):
    import aiograpi_rest.storages as storages
    from aiograpi_rest.dependencies import get_clients

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(storages, "Client", FakeClient)

    gen = get_clients()
    storage = next(gen)
    try:
        assert isinstance(storage, storages.ClientStorage)
    finally:
        with pytest.raises(StopIteration):
            next(gen)
