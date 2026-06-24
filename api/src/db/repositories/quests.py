import json
from typing import TypedDict


class QuestItem(TypedDict):
    item_name: str
    item_translation: str
    npc_name: str
    npc_name_cn: str
    quest_number: int
    count: int
    rarity: str
    is_loot: str


class QuestNpc(TypedDict):
    npc_name: str
    npc_name_display: str
    quest_count: int
    category: str
    quests: list[dict]


class ExploreTarget(TypedDict):
    name: str
    module_name: str
    quest_id: str
    quest_title: str
    quest_number: int
    npc_name: str
    npc_name_display: str


class QuestsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_items(self) -> list[QuestItem]:
        c = self.conn.cursor()
        c.execute(
            "SELECT item_name, item_translation, npc_name, npc_name_cn, quest_number, count, rarity, is_loot "
            "FROM quest_items ORDER BY npc_name, quest_number"
        )
        return [dict(r) for r in c.fetchall()]

    def get_npcs(self) -> list[QuestNpc]:
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

    def get_explore_targets(self) -> list[ExploreTarget]:
        c = self.conn.cursor()
        c.execute(
            "SELECT name, module_name, quest_id, quest_title, quest_number, npc_name, npc_name_display "
            "FROM explore_targets ORDER BY quest_number, npc_name"
        )
        return [dict(r) for r in c.fetchall()]
