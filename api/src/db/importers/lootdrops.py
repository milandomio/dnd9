from config import LOOTDROP_DIR, LOOTDROP_GROUP_DIR

from .._helpers import load_json_dir, ue_asset_base_name


class LootdropsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self, spawner_monster_map: dict[str, list[str]] | None = None) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM lootdrop_items")
        groups = load_json_dir(LOOTDROP_GROUP_DIR)
        drops = load_json_dir(LOOTDROP_DIR)

        ld_group: dict[str, list[str]] = {}
        for raw_name, data_list in groups.items():
            if not data_list:
                continue
            entry = data_list[0]
            ldg_name = self._strip_prefix(raw_name, "Id_LootDropGroup_", "ID_LootDropGroup_")
            items = entry.get("Properties", {}).get("LootDropGroupItemArray", []) or []
            for item in items:
                asset = (item.get("LootDropId") or {}).get("AssetPathName", "")
                if not asset:
                    continue
                ld_name = ue_asset_base_name(asset) or ""
                ld_name = self._strip_prefix(ld_name, "Id_Lootdrop_", "ID_Lootdrop_")
                if ld_name not in ld_group:
                    ld_group[ld_name] = []
                ld_group[ld_name].append(ldg_name)

        if spawner_monster_map:
            for ld_name, ldg_names in ld_group.items():
                canonical = set()
                for ldg in ldg_names:
                    mapped = spawner_monster_map.get(ldg)
                    if mapped:
                        canonical.update(mapped)
                if canonical:
                    ld_group[ld_name] = sorted(canonical)

        rows = []
        for raw_name, data_list in drops.items():
            if not data_list:
                continue
            entry = data_list[0]
            ld_name = self._strip_prefix(raw_name, "Id_Lootdrop_", "ID_Lootdrop_")
            monsters = ld_group.get(ld_name, [])
            items_arr = entry.get("Properties", {}).get("LootDropItemArray", []) or []
            for drop_item in items_arr:
                item_asset = (drop_item.get("ItemId") or {}).get("AssetPathName", "")
                if not item_asset:
                    continue
                item_name = ue_asset_base_name(item_asset) or ""
                item_name = self._strip_prefix(item_name, "Id_Item_", "Id_Props_")
                for mon in monsters:
                    if item_name == mon:
                        continue
                    rows.append((item_name, mon, ld_name))
        seen = set()
        deduped = []
        for r in rows:
            key = (r[0], r[1])
            if key not in seen:
                seen.add(key)
                deduped.append(r)
        c.executemany(
            "INSERT OR REPLACE INTO lootdrop_items (item_name, monster_name, lootdrop_name) VALUES (?, ?, ?)",
            deduped,
        )
        self.conn.commit()
        return len(deduped)

    @staticmethod
    def _strip_prefix(name: str, *prefixes: str) -> str:
        for p in sorted(prefixes, key=len, reverse=True):
            if name.lower().startswith(p.lower()):
                return name[len(p) :]
        return name
