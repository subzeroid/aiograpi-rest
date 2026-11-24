import json
import os
import time
from urllib import parse

from aiograpi import Client
from tinydb import Query, TinyDB


class ClientStorage:
    def __init__(self, db_path=None, client_factory=Client):
        db_path = db_path or os.getenv("AIOGRAPI_REST_DB_PATH", "./db.json")
        self.db = TinyDB(db_path)
        self.client_factory = client_factory
        self._timeline_last_at: dict[str, float] = {}

    def client(self):
        """Get new client (helper)
        """
        cl = self.client_factory()
        cl.request_timeout = 0.1
        return cl

    @staticmethod
    def _clean_sessionid(sessionid: str) -> str:
        return parse.unquote(sessionid.strip(" \""))

    @staticmethod
    def _client_proxy(cl: Client):
        private = getattr(cl, "private", None)
        if private is not None:
            return getattr(private, "proxy", None)
        return getattr(cl, "proxy", None)

    @staticmethod
    def _timeline_on_get_mode() -> str:
        return (os.getenv("AIOGRAPI_REST_TIMELINE_ON_GET") or "always").strip().lower()

    @staticmethod
    def _timeline_interval_seconds() -> int:
        raw = os.getenv("AIOGRAPI_REST_TIMELINE_INTERVAL_SECONDS", "1800")
        try:
            return max(0, int(raw))
        except ValueError:
            return 1800

    async def _maybe_get_timeline_feed(self, session_key: str, cl: Client) -> None:
        mode = self._timeline_on_get_mode()
        if mode == "never":
            return
        if mode == "interval":
            now = time.monotonic()
            last = self._timeline_last_at.get(session_key)
            interval = self._timeline_interval_seconds()
            if last is not None and (now - last) < interval:
                return
            await cl.get_timeline_feed()
            self._timeline_last_at[session_key] = now
            return
        await cl.get_timeline_feed()

    async def get(self, sessionid: str, warm_timeline: bool = True) -> Client:
        """Get client settings

        ``warm_timeline=False`` restores the client without touching Instagram. Callers that
        are about to replace the proxy need this: the stored proxy may be dead, and warming
        the timeline through it would fail before the new proxy can be applied.
        """
        key = self._clean_sessionid(sessionid)
        rows = self.db.search(Query().sessionid == key)
        if not rows:
            raise Exception('Session not found (e.g. after reload process), please relogin')
        row = rows[0]
        settings = json.loads(row['settings'])
        cl = self.client_factory()
        cl.set_settings(settings)
        if row.get("proxy"):
            cl.set_proxy(row["proxy"])
        if warm_timeline:
            await self._maybe_get_timeline_feed(key, cl)
        return cl

    def set(self, cl: Client) -> bool:
        """Set client settings
        """
        key = self._clean_sessionid(cl.sessionid)
        self.db.upsert(
            {
                "sessionid": key,
                "settings": json.dumps(cl.get_settings()),
                "proxy": self._client_proxy(cl) or "",
            },
            Query().sessionid == key,
        )
        return True

    def close(self):
        pass
