import json
import os
from urllib import parse

from aiograpi import Client
from tinydb import Query, TinyDB


class ClientStorage:
    def __init__(self, db_path=None, client_factory=Client):
        db_path = db_path or os.getenv("AIOGRAPI_REST_DB_PATH", "./db.json")
        self.db = TinyDB(db_path)
        self.client_factory = client_factory

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

    async def get(self, sessionid: str) -> Client:
        """Get client settings
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
        await cl.get_timeline_feed()
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
