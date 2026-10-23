import json
from typing import TypedDict


class DungeonModule(TypedDict):
    module_name: str
    translation_key: str
    module_group: str
    size_x: int
    size_y: int
    sl_base_name: str
    map_image_name: str
    aliases: list[str]
    rotation: float
    is_edge: bool
    is_corner: bool
    is_rare: bool


class ModulesRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[DungeonModule]:
        c = self.conn.cursor()
        c.execute(
            "SELECT module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation, is_edge, is_corner, is_rare FROM dungeon_modules ORDER BY module_name"
        )
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["aliases"] = json.loads(d.get("aliases", "[]") or "[]")
            d["is_edge"] = bool(d.get("is_edge"))
            d["is_corner"] = bool(d.get("is_corner"))
            d["is_rare"] = bool(d.get("is_rare"))
            results.append(d)
        return results
