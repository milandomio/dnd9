from typing import TypedDict


class SpawnerCoord(TypedDict):
    keyword: str
    x: float
    y: float
    z: float
    yaw: float
    json_filename: str
    version: str
    map_base: str
    original_keyword: str
    spawner_type: str
    group_parent: str


class CoordinatesRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> dict[str, list[SpawnerCoord]]:
        c = self.conn.cursor()
        c.execute("""
            SELECT s.keyword, s.x, s.y, s.z, s.yaw, s.json_filename,
                   s.version, s.map_base, s.original_keyword, s.spawner_type,
                   s.group_parent
            FROM spawners s
            ORDER BY s.keyword, s.map_base, s.json_filename
        """)
        result: dict[str, list[SpawnerCoord]] = {}
        for row in c.fetchall():
            term = row["keyword"]
            if term not in result:
                result[term] = []
            coord = dict(row)
            dup_key = (coord["x"], coord["y"], coord["z"], coord["json_filename"])
            coord["_dup_key"] = dup_key
            existing_keys = {item["_dup_key"] for item in result[term]}
            if dup_key not in existing_keys:
                result[term].append(coord)
        for term in result:
            for item in result[term]:
                item.pop("_dup_key", None)
        return result

    def get_variant_counts(self) -> dict[tuple[str, str, str], tuple[int, list[str]]]:
        c = self.conn.cursor()
        result: dict[tuple[str, str, str], tuple[int, list[str]]] = {}
        for row in c.execute(
            "SELECT map_base, json_filename, group_parent, "
            "COUNT(DISTINCT original_keyword) as cnt, "
            "COUNT(*) as total, "
            "GROUP_CONCAT(DISTINCT original_keyword) as keywords "
            "FROM spawners WHERE group_parent != '' "
            "GROUP BY map_base, json_filename, group_parent HAVING cnt > 1"
        ):
            names = row["keywords"].split(",")
            result[(row["map_base"], row["json_filename"], row["group_parent"])] = (
                row["cnt"],
                names,
            )
        for row in c.execute(
            "SELECT map_base, json_filename, group_parent, "
            "COUNT(*) as total "
            "FROM spawners WHERE group_parent != '' "
            "GROUP BY map_base, json_filename, group_parent "
            "HAVING COUNT(DISTINCT original_keyword) = 1 AND COUNT(*) > 1"
        ):
            key = (row["map_base"], row["json_filename"], row["group_parent"])
            if key not in result:
                result[key] = (row["total"], [])
        return result
