from typing import TypedDict

from config import TRANSLATION_KEY_ALIAS_MAP


class PropsEntity(TypedDict):
    asset_name: str
    translation_key: str


class PropsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[PropsEntity]:
        c = self.conn.cursor()
        c.execute("SELECT asset_name, translation_key FROM props_entities ORDER BY asset_name")
        results = [dict(r) for r in c.fetchall()]
        for result in results:
            result["translation_key"] = TRANSLATION_KEY_ALIAS_MAP.get(
                result["translation_key"], result["translation_key"]
            )
        return results
