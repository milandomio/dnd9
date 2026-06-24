from typing import TypedDict


class PropsEntity(TypedDict):
    asset_name: str
    translation_key: str


class PropsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[PropsEntity]:
        c = self.conn.cursor()
        c.execute("SELECT asset_name, translation_key FROM props_entities ORDER BY asset_name")
        return [dict(r) for r in c.fetchall()]
