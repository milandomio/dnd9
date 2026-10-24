import json
from typing import TypedDict


class LootdropRelation(TypedDict):
    item_name: str
    monster_name: str


class SpawnerEntry(TypedDict):
    spawner_keyword: str
    entity_name: str
    spawn_rate: float
    dungeon_grades: list[int]
    lootdrop_group_id: str
    session_spawn_limit: int


class LootdropsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_relationships(self) -> list[LootdropRelation]:
        c = self.conn.cursor()
        c.execute("SELECT item_name, monster_name FROM lootdrop_items ORDER BY item_name, monster_name")
        return [dict(r) for r in c.fetchall()]

    def get_spawner_entries_for_keyword(self, keyword: str) -> list[SpawnerEntry]:
        c = self.conn.cursor()
        c.execute(
            "SELECT spawner_keyword, entity_name, spawn_rate, dungeon_grades, lootdrop_group_id, "
            "COALESCE(session_spawn_limit, 0) AS session_spawn_limit "
            "FROM spawner_entries WHERE spawner_keyword = ? OR entity_name = ?",
            (keyword, keyword),
        )
        results = []
        for r in c.fetchall():
            results.append(
                {
                    "spawner_keyword": r["spawner_keyword"],
                    "entity_name": r["entity_name"],
                    "spawn_rate": r["spawn_rate"],
                    "dungeon_grades": json.loads(r["dungeon_grades"]),
                    "lootdrop_group_id": r["lootdrop_group_id"],
                    "session_spawn_limit": r["session_spawn_limit"],
                }
            )
        return results

    def get_all_spawner_entries(self) -> list[SpawnerEntry]:
        c = self.conn.cursor()
        c.execute(
            "SELECT spawner_keyword, entity_name, spawn_rate, dungeon_grades, lootdrop_group_id, "
            "COALESCE(session_spawn_limit, 0) AS session_spawn_limit FROM spawner_entries"
        )
        results = []
        for r in c.fetchall():
            results.append(
                {
                    "spawner_keyword": r["spawner_keyword"],
                    "entity_name": r["entity_name"],
                    "spawn_rate": r["spawn_rate"],
                    "dungeon_grades": json.loads(r["dungeon_grades"]),
                    "lootdrop_group_id": r["lootdrop_group_id"],
                    "session_spawn_limit": r["session_spawn_limit"],
                }
            )
        return results

    def get_self_placed_item_keywords(self) -> set[str]:
        """Spawner keywords that place the lootdrop itself on the ground.

        A spawner entry with an empty `entity_name` means the spawner is not
        tied to a monster/prop and its group is the placed entity itself
        (e.g. `Id_Spawner_Lootdrop_BronzeScale`). Props-type spawners are
        excluded because those entities are exported to /props.
        """
        c = self.conn.cursor()
        # Only keywords with a real map spawner count: an entry without one
        # never places anything on the ground (it is a loot table only).
        # Some entries are `Spawn_`-prefixed while the spawner row is not
        # (`Spawn_FrostWyvernEgg` → `FrostWyvernEgg`).
        c.execute(
            "SELECT DISTINCT s.keyword AS kw "
            "FROM spawner_entries se "
            "JOIN spawners s ON s.keyword = se.spawner_keyword "
            "WHERE se.entity_name = '' AND s.spawner_type != 'props'"
        )
        result = {row["kw"] for row in c.fetchall()}
        c.execute(
            "SELECT DISTINCT s.keyword AS kw "
            "FROM spawner_entries se "
            "JOIN spawners s ON s.keyword = substr(se.spawner_keyword, ?) "
            "WHERE se.entity_name = '' "
            "AND substr(se.spawner_keyword, 1, ?) = ? "
            "AND s.spawner_type != 'props'",
            (len("Spawn_") + 1, len("Spawn_"), "Spawn_"),
        )
        result.update(row["kw"] for row in c.fetchall())
        return result

    def get_session_spawn_limits(self) -> dict[str, int]:
        """Max per-session spawn limit per entity name (0 = unlimited)."""
        c = self.conn.cursor()
        c.execute(
            "SELECT entity_name, MAX(COALESCE(session_spawn_limit, 0)) AS limit_value "
            "FROM spawner_entries WHERE entity_name != '' GROUP BY entity_name"
        )
        return {r["entity_name"]: r["limit_value"] for r in c.fetchall() if r["limit_value"] > 0}

    def get_item_drop_rate(self, lootdrop_group_id: str, item_name: str, full_grade: int) -> float:
        c = self.conn.cursor()
        for grade in (full_grade, 0):
            c.execute(
                "SELECT lg.lootdrop_id, lg.lootdrop_rate_id, lg.drop_count "
                "FROM lootdrop_groups lg "
                "WHERE lg.group_id = ? AND lg.dungeon_grade = ?",
                (lootdrop_group_id, grade),
            )
            rows = c.fetchall()
            if not rows:
                continue
            total_weight = 0.0
            found_any = False
            for r in rows:
                ld_id = r["lootdrop_id"]
                lr_id = r["lootdrop_rate_id"]
                group_count = r["drop_count"]
                c.execute(
                    "SELECT luck_grade, drop_count FROM lootdrop_rate_items WHERE lootdrop_id = ? AND item_name = ?",
                    (ld_id, item_name),
                )
                items = c.fetchall()
                if not items:
                    continue
                found_any = True
                for item_row in items:
                    lg = item_row["luck_grade"]
                    item_count = item_row["drop_count"]
                    c.execute(
                        "SELECT COALESCE(SUM(weight), 0) as total FROM lootdrop_rate_weights WHERE rate_id = ? AND luck_grade = ?",
                        (lr_id, lg),
                    )
                    w_row = c.fetchone()
                    if w_row:
                        total_weight += w_row["total"] * group_count * item_count
            if found_any:
                return total_weight / 10000
        return 0.0
