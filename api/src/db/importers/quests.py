class QuestsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_items(self, items: list[dict]) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM quest_items")
        rows = [
            (
                qi.get("item_name", ""),
                qi.get("item_translation", ""),
                qi.get("npc_name", ""),
                qi.get("npc_name_cn", ""),
                qi.get("quest_number", 0),
                qi.get("count", 1),
                qi.get("rarity", ""),
                qi.get("is_loot", ""),
            )
            for qi in items
        ]
        c.executemany(
            "INSERT INTO quest_items (item_name, item_translation, npc_name, npc_name_cn, quest_number, count, rarity, is_loot) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def import_npcs(self, npcs: list[dict]) -> int:
        import json as _json

        c = self.conn.cursor()
        c.execute("DELETE FROM quest_npcs")
        rows = [
            (
                npc.get("npc_name", ""),
                npc.get("npc_name_display", ""),
                npc.get("quest_count", 0),
                npc.get("category", ""),
                _json.dumps(npc.get("quests", []), ensure_ascii=False),
            )
            for npc in npcs
        ]
        c.executemany(
            "INSERT OR REPLACE INTO quest_npcs (npc_name, npc_name_display, quest_count, category, quests_json) VALUES (?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)

    def import_explore_targets(self, targets: list[dict]) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM explore_targets")
        rows = [
            (
                t.get("name", ""),
                t.get("module_name", ""),
                t.get("quest_id", ""),
                t.get("quest_title", ""),
                t.get("quest_number", 0),
                t.get("npc_name", ""),
                t.get("npc_name_display", ""),
            )
            for t in targets
        ]
        c.executemany(
            "INSERT INTO explore_targets (name, module_name, quest_id, quest_title, quest_number, npc_name, npc_name_display) VALUES (?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)
