import json


class ModulesRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT module_name, translation_key, module_group, size_x, size_y, sl_base_name, map_image_name, aliases, rotation FROM dungeon_modules ORDER BY module_name"
        )
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["aliases"] = json.loads(d.get("aliases", "[]") or "[]")
            results.append(d)
        return results
