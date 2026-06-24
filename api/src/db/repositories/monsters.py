from typing import TypedDict


class MonsterEntity(TypedDict):
    monster_name: str
    translation_key: str


class MonstersRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[MonsterEntity]:
        c = self.conn.cursor()
        c.execute("SELECT monster_name, translation_key FROM monster_entities ORDER BY monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_name_map(self) -> dict[str, str]:
        c = self.conn.cursor()
        c.execute("SELECT monster_name FROM monster_entities")
        result = {}
        for row in c.fetchall():
            name = row["monster_name"]
            result[name.lower()] = name
        return result
