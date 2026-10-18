from typing import TypedDict


class CraftMerchant(TypedDict):
    merchant_name: str
    kind: str
    translation_key: str
    sort_order: int


class CraftRecipe(TypedDict):
    recipe_id: str
    merchant_name: str
    unique_id: int
    output_raw_name: str
    output_item_name: str
    output_rarity: str
    requirements_json: str
    conversation_key: str
    craft_complete_key: str


class CraftsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_merchants(self) -> list[CraftMerchant]:
        c = self.conn.cursor()
        c.execute(
            "SELECT merchant_name, kind, translation_key, sort_order "
            "FROM craft_merchants ORDER BY sort_order, merchant_name"
        )
        return [dict(r) for r in c.fetchall()]

    def get_recipes(self) -> list[CraftRecipe]:
        c = self.conn.cursor()
        c.execute(
            "SELECT recipe_id, merchant_name, unique_id, output_raw_name, output_item_name,"
            " output_rarity, requirements_json, conversation_key, craft_complete_key "
            "FROM craft_recipes ORDER BY unique_id, recipe_id"
        )
        return [dict(r) for r in c.fetchall()]
