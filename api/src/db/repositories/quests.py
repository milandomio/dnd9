import json


class QuestsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_items(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT item_name, item_translation, npc_name, npc_name_cn, quest_number, count, rarity, is_loot "
            "FROM quest_items ORDER BY npc_name, quest_number"
        )
        return [dict(r) for r in c.fetchall()]

    def get_npcs(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT npc_name, npc_name_display, quest_count, category, quests_json FROM quest_npcs ORDER BY npc_name"
        )
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["quests"] = json.loads(d.pop("quests_json", "[]") or "[]")
            results.append(d)
        return results

    def get_explore_targets(self) -> list[dict]:
        c = self.conn.cursor()
        c.execute(
            "SELECT name, module_name, quest_id, quest_title, quest_number, npc_name, npc_name_display "
            "FROM explore_targets ORDER BY quest_number, npc_name"
        )
        return [dict(r) for r in c.fetchall()]
