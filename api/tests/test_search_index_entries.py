import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from index_export import (  # noqa: E402
    _iter_craft_search_entries,
    _iter_quest_objective_entries,
    _iter_shop_search_entries,
    build_and_save_indexes,
)

SHOP_INDEX = {
    "merchants": [{"merchant_name": "GoblinSmuggler"}],
    "regions": [
        {
            "region": "Crypts",
            "label_key": "Text_UI_WB_DungeonSlot_TheCrypts_2ndFloor",
            "display": "地穴",
            "item_count": 2,
            "exclusive_count": 1,
        }
    ],
}

SHOP_DETAIL = {
    "region": "Crypts",
    "label_key": "Text_UI_WB_DungeonSlot_TheCrypts_2ndFloor",
    "display": "地穴",
    "difficulties": [
        {
            "difficulty": "N",
            "slots": [
                {
                    "slot": 1,
                    "items": [
                        {
                            "name": "HealingPotion_4001",
                            "page": "HealingPotion",
                            "translation": "治疗药水",
                            "translation_key": "Text_DesignData_Item_Item_HealingPotion_1001",
                        },
                        {
                            "name": "HealingPotion_5001",
                            "page": "HealingPotion",
                            "translation": "治疗药水",
                            "translation_key": "Text_DesignData_Item_Item_HealingPotion_1001",
                        },
                    ],
                }
            ],
        },
        {
            "difficulty": "HR",
            "slots": [
                {
                    "slot": 1,
                    "items": [
                        {
                            "name": "LuckPotion_5001",
                            "page": "LuckPotion",
                            "translation": "幸运药水",
                            "translation_key": "Text_DesignData_Item_Item_LuckPotion",
                        }
                    ],
                }
            ],
        },
    ],
}

CRAFTS_PAYLOAD = {
    "count": 1,
    "merchants": [
        {
            "name": "Alchemist",
            "slug": "alchemist",
            "kind": "npc",
            "translation_key": "Text_DesignData_Merchant_Merchant_Alchemist",
            "display": "炼金术师",
        },
        {"name": "__ores__", "slug": "ores", "kind": "ores", "translation_key": "", "display": ""},
    ],
    "recipes": [
        {
            "merchant": "Alchemist",
            "recipe_id": "Id_StockCraft_Alchemist_12#0",
            "name": "HealingPotion",
            "translation": "治疗药水",
            "translation_key": "Text_DesignData_Item_Item_HealingPotion_1001",
            "requirements": [
                {
                    "name": "Lifeleaf",
                    "translation": "生命之叶",
                    "translation_key": "Text_DesignData_Item_Item_Lifeleaf_1001",
                    "amount": 1,
                }
            ],
        },
        {
            "merchant": "Alchemist",
            "recipe_id": "Id_StockCraft_Alchemist_13#0",
            "name": "HealingPotion",
            "translation": "治疗药水",
            "translation_key": "Text_DesignData_Item_Item_HealingPotion_1001",
        },
        {
            "merchant": "__ores__",
            "recipe_id": "Id_StockCraft_Ores_1#0",
            "name": "IronIngot",
            "translation": "铁锭",
            "translation_key": "Text_DesignData_Item_Item_IronIngot_1001",
        },
    ],
}

QUEST_NPCS = [
    {
        "npc_name": "Goldsmith",
        "npc_name_display": "珠宝匠",
        "translation_key": "Text_DesignData_Merchant_Merchant_Goldsmith",
        "quest_count": 1,
        "category": "装备NPC",
        "quests": [
            {
                "id": "Id_Quest_Goldsmith_06",
                "title": "物资常缺",
                "translation_key": "Text_DesignData_Quest_Goldsmith_Title_06_EAS_11",
                "quest_number": 6,
                "contents": [
                    {
                        "type": "Fetch",
                        "target": "风箱",
                        "translation_key": "Text_DesignData_Item_Item_Bellows",
                        "count": 1,
                    },
                    {"type": "Damage", "target": "Damage", "count": 25},
                ],
                "rewards": [],
                "required": "",
            }
        ],
    }
]


class ShopSearchEntryTest(unittest.TestCase):
    def test_one_entry_per_folded_region_item(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dungeon_shops").mkdir()
            (root / "dungeon_shops" / "Crypts.json").write_text(json.dumps(SHOP_DETAIL), encoding="utf-8")
            entries = _iter_shop_search_entries(SHOP_INDEX, root)

        # HealingPotion_4001/5001 fold to one page, so two entries total.
        self.assertEqual([e["name"] for e in entries], ["HealingPotion", "LuckPotion"])
        healing = entries[0]
        self.assertEqual(healing["page"], "dungeon_shops")
        self.assertEqual(healing["translation"], "治疗药水")
        self.assertEqual(healing["tag"], "地穴")
        self.assertEqual(healing["tag_translation_key"], "Text_UI_WB_DungeonSlot_TheCrypts_2ndFloor")
        # The UI renders <prefix>-<tag> so a shop hit reads "地牢商店-地穴".
        self.assertEqual(healing["tag_prefix_key"], "ui.nav.dungeon_shops")
        self.assertEqual(healing["url"], "/dungeon_shops/Crypts/?item=HealingPotion")

    def test_missing_region_file_is_skipped(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(_iter_shop_search_entries(SHOP_INDEX, Path(tmp)), [])
        self.assertEqual(_iter_shop_search_entries(None, Path(tmp)), [])


class CraftSearchEntryTest(unittest.TestCase):
    def test_one_entry_per_merchant_item(self):
        entries = _iter_craft_search_entries(CRAFTS_PAYLOAD)
        # Products carry the crafter as tag; materials carry the product they
        # are used for, so "生命之叶" surfaces as "工匠合成-治疗药水".
        self.assertEqual(
            [(e["name"], e.get("tag", "")) for e in entries],
            [
                ("HealingPotion", "炼金术师"),
                ("Lifeleaf", "治疗药水"),
                ("IronIngot", ""),
            ],
        )
        healing = entries[0]
        self.assertEqual(healing["page"], "crafts")
        # The crafter tab is a route now, so the entry links to that tab directly.
        self.assertEqual(healing["url"], "/crafts/alchemist/?item=HealingPotion")
        self.assertEqual(healing["translation_key"], "Text_DesignData_Item_Item_HealingPotion_1001")
        self.assertEqual(healing["tag_translation_key"], "Text_DesignData_Merchant_Merchant_Alchemist")
        # Products read "工匠合成-炼金术师", same prefix as their materials.
        self.assertEqual(healing["tag_prefix_key"], "ui.search.tag.craft_group")
        # The synthetic ore tab gets a readable slug instead of ``__ores__``.
        self.assertEqual(entries[2]["url"], "/crafts/ores/?item=IronIngot")
        material = entries[1]
        self.assertEqual(material["page"], "crafts")
        self.assertEqual(material["tag_prefix_key"], "ui.search.tag.craft_group")
        self.assertEqual(material["tag_translation_key"], "Text_DesignData_Item_Item_HealingPotion_1001")
        self.assertEqual(material["translation_key"], "Text_DesignData_Item_Item_Lifeleaf_1001")
        # Clicking the material opens the recipe card that uses it.
        self.assertEqual(material["url"], "/crafts/alchemist/?item=HealingPotion")

    def test_merchant_without_slug_falls_back_to_name(self):
        payload = {
            "merchants": [{"name": "Alchemist", "kind": "npc"}],
            "recipes": [{"merchant": "Alchemist", "name": "HealingPotion"}],
        }
        self.assertEqual(_iter_craft_search_entries(payload)[0]["url"], "/crafts/Alchemist/?item=HealingPotion")

    def test_empty_payload_yields_nothing(self):
        self.assertEqual(_iter_craft_search_entries(None), [])


class QuestObjectiveEntryTest(unittest.TestCase):
    def test_entry_carries_objective_and_quest_link(self):
        entries = _iter_quest_objective_entries(QUEST_NPCS)
        self.assertEqual(len(entries), 1)
        entry = entries[0]
        self.assertEqual(entry["name"], "Id_Quest_Goldsmith_06")
        self.assertEqual(entry["translation"], "物资常缺")
        self.assertEqual(entry["subtitle"], "风箱")
        self.assertEqual(entry["subtitle_key"], "Text_DesignData_Item_Item_Bellows")
        self.assertEqual(entry["tag"], "珠宝匠")
        # Rendered as "任务-珠宝匠", not a bare NPC name.
        self.assertEqual(entry["tag_prefix_key"], "ui.search.tag.quest")
        self.assertEqual(entry["page"], "quest_npc")
        self.assertEqual(entry["url"], "/quest_npc/Goldsmith/?quest=6")

    def test_placeholder_objectives_are_skipped(self):
        npcs = json.loads(json.dumps(QUEST_NPCS))
        npcs[0]["quests"][0]["contents"] = [{"type": "Damage", "target": "Damage"}]
        self.assertEqual(_iter_quest_objective_entries(npcs), [])


class BuildSearchIndexTest(unittest.TestCase):
    def test_new_pages_land_in_search_and_index_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "dungeon_shops").mkdir()
            (root / "dungeon_shops" / "Crypts.json").write_text(json.dumps(SHOP_DETAIL), encoding="utf-8")
            index_data = build_and_save_indexes(
                [],
                [],
                [],
                [],
                [],
                0,
                1,
                QUEST_NPCS,
                root,
                shop_index=SHOP_INDEX,
                crafts_payload=CRAFTS_PAYLOAD,
            )
            search_index = json.loads((root / "search_index.json").read_text(encoding="utf-8"))

        pages = [e["page"] for e in search_index]
        self.assertEqual(pages.count("dungeon_shops"), 2)
        # Two products + the material each recipe consumes.
        self.assertEqual(pages.count("crafts"), 3)
        # 1 NPC entry + 1 quest objective entry.
        self.assertEqual(pages.count("quest_npc"), 2)
        # 【任务探索表】已归档，不再进入 index.json / search_index.json。
        self.assertNotIn("explore", pages)
        counts = {entry["page"]: entry["count"] for entry in index_data if "page" in entry}
        self.assertEqual(counts["dungeon_shops"], 1)
        self.assertEqual(counts["crafts"], 1)
        self.assertNotIn("explore", counts)


if __name__ == "__main__":
    unittest.main()
