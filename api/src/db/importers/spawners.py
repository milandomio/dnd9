import json
import re

from config import LOOTDROP_DIR, LOOTDROP_GROUP_DIR, LOOTDROP_RATE_DIR, SPAWNER_DIR
from drop_rate import _round_rate

from .._helpers import load_json_dir, ue_asset_base_name

_SPAWNER_PREFIXES = [
    "Id_Spawner_New_Monster_",
    "Id_Spawner_New_Props_",
    "Id_Spawner_New_LootDrop_",
    "Id_Spawner_New_Lootdrop_",
    "Id_Spawner_Monster_",
    "Id_Spawner_Props_",
    "Id_Spawner_LootDrop_",
    "Id_Spawner_Lootdrop_",
    "Id_Spawner_New_NPC_",
    "Id_Spawner_NPC_",
    "Id_Spawner_New_",
    "Id_Spawner_",
]


class SpawnersImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_spawner_fallback_entities(self) -> dict[str, int]:
        c = self.conn.cursor()
        c.execute("SELECT item_name FROM item_entities")
        existing_items = {r["item_name"] for r in c.fetchall()}
        c.execute("SELECT monster_name FROM monster_entities")
        existing_monsters = {r["monster_name"] for r in c.fetchall()}
        c.execute("SELECT asset_name FROM props_entities")
        existing_props = {r["asset_name"] for r in c.fetchall()}
        c.execute(
            "SELECT DISTINCT keyword, spawner_type FROM spawners WHERE spawner_type IN ('item', 'monster', 'props')"
        )
        spawner_keywords = c.fetchall()
        added = {"item": 0, "monster": 0, "props": 0}
        item_rows = []
        monster_rows = []
        props_rows = []
        for row in spawner_keywords:
            keyword = row["keyword"]
            stype = row["spawner_type"]
            if stype == "item" and keyword not in existing_items:
                item_rows.append((keyword, keyword, ""))
                existing_items.add(keyword)
            elif stype == "monster" and keyword not in existing_monsters:
                monster_rows.append((keyword, keyword, ""))
                existing_monsters.add(keyword)
            elif stype == "props" and keyword not in existing_props:
                props_rows.append((keyword, keyword, ""))
                existing_props.add(keyword)
        if item_rows:
            c.executemany(
                "INSERT OR IGNORE INTO item_entities (item_name, raw_name, translation_key) VALUES (?, ?, ?)",
                item_rows,
            )
            added["item"] = len(item_rows)
        if monster_rows:
            c.executemany(
                "INSERT OR IGNORE INTO monster_entities (monster_name, raw_name, translation_key) VALUES (?, ?, ?)",
                monster_rows,
            )
            added["monster"] = len(monster_rows)
        if props_rows:
            c.executemany(
                "INSERT OR IGNORE INTO props_entities (asset_name, raw_name, translation_key) VALUES (?, ?, ?)",
                props_rows,
            )
            added["props"] = len(props_rows)
        self.conn.commit()
        if added["item"] > 0:
            self._rebuild_fts("items_fts")
        if added["monster"] > 0:
            self._rebuild_fts("monsters_fts")
        return added

    def import_spawner_entries(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM spawner_entries")
        rows = []
        if not SPAWNER_DIR.exists():
            return 0
        for fp in sorted(SPAWNER_DIR.glob("*.json")):
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if not isinstance(data, list) or not data:
                continue
            entry = data[0]
            if entry.get("Type") != "DCSpawnerDataAsset":
                continue
            name = entry.get("Name", "")
            if not name:
                continue
            keyword = name
            for prefix in _SPAWNER_PREFIXES:
                if keyword.startswith(prefix):
                    keyword = keyword[len(prefix) :]
                    break
            props = entry.get("Properties", {}) or {}
            items = props.get("SpawnerItemArray", []) or []
            _total_pool = max(sum(item.get("SpawnRate", 10000) for item in items), 1)
            _suffix_totals: dict[tuple[int, int], int] = {}
            for item in items:
                dg_list = item.get("DungeonGrades", []) or []
                if dg_list:
                    suffixes = set()
                    for g in dg_list:
                        mode_id = g // 1000 if g >= 1000 else 1
                        suffixes.add((mode_id, g % 1000))
                    sr = item.get("SpawnRate", 10000)
                    for s in suffixes:
                        _suffix_totals[s] = _suffix_totals.get(s, 0) + sr
            for item in items:
                ldg = item.get("LootDropGroupId", {}) or {}
                ldg_path = ldg.get("AssetPathName", "")
                if not ldg_path:
                    continue
                raw_rate = item.get("SpawnRate", 10000)
                dungeon_grades = item.get("DungeonGrades", []) or []
                if dungeon_grades:
                    _suffixes = set()
                    for g in dungeon_grades:
                        mode_id = g // 1000 if g >= 1000 else 1
                        _suffixes.add((mode_id, g % 1000))
                    _rates = [100 * raw_rate / _suffix_totals[s] for s in _suffixes]
                    spawn_rate = _round_rate(min(_rates))
                elif len(items) > 1:
                    spawn_rate = _round_rate(100 * raw_rate / _total_pool)
                else:
                    spawn_rate = _round_rate(100 * raw_rate / 10000)
                spawn_rate = min(spawn_rate, 100.0)
                ldg_id = ue_asset_base_name(ldg_path) or ""
                entity_name = ""
                for id_key in ("MonsterId", "PropsId"):
                    id_path = (item.get(id_key, {}) or {}).get("AssetPathName", "")
                    if id_path:
                        raw = ue_asset_base_name(id_path) or ""
                        entity_name = raw.removeprefix("Id_Monster_").removeprefix("Id_Props_")
                        break
                rows.append((keyword, entity_name, spawn_rate, json.dumps(dungeon_grades), ldg_id))
        c.executemany(
            "INSERT INTO spawner_entries (spawner_keyword, entity_name, spawn_rate, dungeon_grades, lootdrop_group_id) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def import_lootdrop_groups(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_groups")
        rows = []
        files = load_json_dir(LOOTDROP_GROUP_DIR)
        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            group_items = props.get("LootDropGroupItemArray", []) or []
            for gi in group_items:
                ld_path = (gi.get("LootDropId", {}) or {}).get("AssetPathName", "")
                lr_path = (gi.get("LootDropRateId", {}) or {}).get("AssetPathName", "")
                if not ld_path:
                    continue
                ld_id = ue_asset_base_name(ld_path) or ""
                lr_id = ue_asset_base_name(lr_path) if lr_path else ""
                grade = gi.get("DungeonGrade", 0)
                count = gi.get("LootDropCount", 1)
                rows.append((stem, grade, ld_id, lr_id, count))
        c.executemany(
            "INSERT INTO lootdrop_groups (group_id, dungeon_grade, lootdrop_id, lootdrop_rate_id, drop_count) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def import_lootdrop_rate_items(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_rate_items")
        rows = []
        files = load_json_dir(LOOTDROP_DIR)
        _variant_re = re.compile(r"_\d{4}$")
        _variant_priority = {"_5001": 0, "_4001": 1, "_3001": 2}

        def _variant_rank(name: str) -> int:
            m = _variant_re.search(name)
            if m:
                return _variant_priority.get(m.group(0), 99)
            return 100

        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            ld_items = props.get("LootDropItemArray", []) or []
            for li in ld_items:
                item_path = (li.get("ItemId", {}) or {}).get("AssetPathName", "")
                if not item_path:
                    continue
                raw_name = ue_asset_base_name(item_path) or ""
                item_name = raw_name.removeprefix("Id_Item_")
                luck_grade = li.get("LuckGrade", 0)
                count = li.get("ItemCount", 1)
                rows.append((stem, item_name, luck_grade, count))
        seen: dict[tuple[str, str], int] = {}
        filtered = []
        for _i, (stem, item_name, luck_grade, count) in enumerate(rows):
            base = _variant_re.sub("", item_name)
            key = (stem, item_name) if item_name.endswith("_8001") else (stem, base)
            if base == item_name:
                seen[key] = len(filtered)
                filtered.append((stem, item_name, luck_grade, count))
            elif key in seen:
                existing_idx = seen[key]
                existing_name = filtered[existing_idx][1]
                if _variant_rank(item_name) < _variant_rank(existing_name):
                    filtered[existing_idx] = (stem, item_name, luck_grade, count)
            else:
                seen[key] = len(filtered)
                filtered.append((stem, item_name, luck_grade, count))
        c.executemany(
            "INSERT INTO lootdrop_rate_items (lootdrop_id, item_name, luck_grade, drop_count) VALUES (?, ?, ?, ?)",
            filtered,
        )
        self.conn.commit()
        return len(filtered)

    def import_lootdrop_rate_weights(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_rate_weights")
        rows = []
        files = load_json_dir(LOOTDROP_RATE_DIR)
        for stem, data_list in files.items():
            if not data_list:
                continue
            props = data_list[0].get("Properties", {}) or {}
            rate_items = props.get("LootDropRateItemArray", []) or []
            for ri in rate_items:
                grade = ri.get("LuckGrade", 0)
                weight = ri.get("DropRate", 0)
                rows.append((stem, grade, weight))
        c.executemany(
            "INSERT INTO lootdrop_rate_weights (rate_id, luck_grade, weight) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def _rebuild_fts(self, fts_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()
