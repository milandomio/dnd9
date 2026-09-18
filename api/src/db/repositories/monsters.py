from typing import TypedDict


class MonsterEntity(TypedDict):
    monster_name: str
    translation_key: str
    class_type: str
    race: str


class MonstersRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[MonsterEntity]:
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(monster_entities)")
        columns = {row[1] for row in c.fetchall()}
        class_expr = "class_type" if "class_type" in columns else "'' AS class_type"
        race_expr = "race" if "race" in columns else "'' AS race"
        c.execute(
            f"SELECT monster_name, translation_key, {class_expr}, {race_expr} FROM monster_entities ORDER BY monster_name"
        )
        return [dict(r) for r in c.fetchall()]

    def get_name_map(self) -> dict[str, str]:
        c = self.conn.cursor()
        c.execute("SELECT monster_name FROM monster_entities")
        result = {}
        for row in c.fetchall():
            name = row["monster_name"]
            result[name.lower()] = name
        return result
