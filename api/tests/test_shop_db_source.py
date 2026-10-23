import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.schema import SchemaManager  # noqa: E402
from merchant_builder import EQUIPMENT_SLOT, build_shop_data  # noqa: E402


class ShopReadsFromDatabaseTest(unittest.TestCase):
    """The shop export must take categories, rarities and prices from the DB.

    The importer writes them, the export reads them back — never the unpacked
    assets. Rotating a value in SQLite and re-exporting has to change the JSON,
    otherwise a DB-only run (CI, patch deploys) would ship stale shop data.
    """

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmp.name) / "shop.db"
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        SchemaManager(conn).create_tables()
        conn.executemany(
            "INSERT INTO ingame_merchant_stock (variant_id, slot_index, item_name, item_count, item_rate, stock, price, currency)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("GoblinSmuggler_Crypts_N", EQUIPMENT_SLOT, "GrimveilCloak_5001", 1, 105, 1, 500, "GoldCoins"),
                ("GoblinSmuggler_Crypts_N", EQUIPMENT_SLOT, "Buckler_5001", 1, 300, 1, 200, "GoldCoins"),
            ],
        )
        conn.execute(
            "INSERT INTO ingame_merchant_variants (variant_id, merchant_name, region, difficulty)"
            " VALUES ('GoblinSmuggler_Crypts_N', 'GoblinSmuggler', 'Crypts', 'N')"
        )
        conn.execute(
            "INSERT INTO ingame_merchants (merchant_name, translation_key, greeting_key, npc_id)"
            " VALUES ('GoblinSmuggler', 'Text_DesignData_InGameMerchant_InGameMerchant_GoblinSmuggler', '', '')"
        )
        conn.executemany(
            "INSERT INTO item_entities (item_name, raw_name, translation_key, category, variant_count,"
            " item_type, item_category_key, item_subtype_keys, item_slot_key) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "GrimveilCloak",
                    "Id_Item_GrimveilCloak_5001",
                    "Text_DesignData_Item_Item_GrimveilCloak_5001",
                    "",
                    1,
                    "Armor",
                    "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor",
                    "",
                    "",
                ),
                (
                    "Buckler",
                    "Id_Item_Buckler_5001",
                    "Text_DesignData_Item_Item_Buckler_5001",
                    "",
                    1,
                    "Weapon",
                    "Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon",
                    "",
                    "",
                ),
            ],
        )
        conn.executemany(
            "INSERT INTO translations (key, value) VALUES (?, ?)",
            [
                ("Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Armor", "护甲"),
                ("Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon", "武器"),
                ("Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_Epic", "史诗"),
                ("Text_Code_DCDataBlueprintLibrary_Type_Item_Rarity_Rare", "罕见"),
            ],
        )
        conn.commit()
        self.conn = conn

    def tearDown(self):
        self.conn.close()
        self._tmp.cleanup()

    def _export(self):
        rows = self.conn.execute("SELECT * FROM ingame_merchant_stock").fetchall()
        variants = self.conn.execute("SELECT * FROM ingame_merchant_variants").fetchall()
        merchants = self.conn.execute("SELECT * FROM ingame_merchants").fetchall()
        entities = self.conn.execute("SELECT * FROM item_entities").fetchall()
        translations = {row["key"]: row["value"] for row in self.conn.execute("SELECT key, value FROM translations")}
        categories = {
            row["item_name"]: {
                "item_type": row["item_type"],
                "item_category_key": row["item_category_key"],
            }
            for row in entities
        }
        item_index = {
            row["item_name"]: {"page": row["item_name"], "translation": "", "translation_key": ""} for row in entities
        }
        return build_shop_data(
            {
                "merchants": [dict(row) for row in merchants],
                "variants": [dict(row) for row in variants],
                "stock": [dict(row) for row in rows],
            },
            translations,
            item_index,
            {"Crypts": "废墟地穴"},
            categories,
        )

    def _items(self, payload):
        detail = payload["details"]["Crypts"]["difficulties"][0]
        slot = next(s for s in detail["slots"] if s["slot"] == EQUIPMENT_SLOT)
        return {item["name"]: item for item in slot["items"]}

    def test_price_is_read_from_the_db(self):
        before = self._items(self._export())["GrimveilCloak_5001"]
        self.assertEqual(before["price"], 500)

        self.conn.execute("UPDATE ingame_merchant_stock SET price = 7777 WHERE item_name = 'GrimveilCloak_5001'")
        self.conn.commit()

        after = self._items(self._export())["GrimveilCloak_5001"]
        self.assertEqual(after["price"], 7777)

    def test_category_is_read_from_the_db(self):
        before = self._items(self._export())["GrimveilCloak_5001"]
        self.assertEqual(before["item_category_label"], "护甲")

        self.conn.execute(
            "UPDATE item_entities SET item_category_key = 'Text_Code_DCDataBlueprintLibrary_Type_Item_Category_Weapon'"
            " WHERE item_name = 'GrimveilCloak'"
        )
        self.conn.commit()

        after = self._items(self._export())["GrimveilCloak_5001"]
        self.assertEqual(after["item_category_label"], "武器")

    def test_rarity_label_is_read_from_the_db(self):
        items = self._items(self._export())
        self.assertEqual(items["GrimveilCloak_5001"]["rarity_label"], "史诗")
        # 5001 is Epic too; only the 4001 quality suffix is Rare.
        self.assertEqual(items["Buckler_5001"]["rarity_label"], "史诗")

    def test_mini_artifact_pool_comes_from_the_stock_rate(self):
        items = self._items(self._export())
        self.assertEqual(items["GrimveilCloak_5001"]["pool"], "mini_artifact")
        self.assertEqual(items["Buckler_5001"]["pool"], "tier")


if __name__ == "__main__":
    unittest.main()
