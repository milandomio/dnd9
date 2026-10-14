from typing import TypedDict


class MerchantInfo(TypedDict):
    merchant_name: str
    translation_key: str
    greeting_key: str
    npc_id: str


class MerchantVariant(TypedDict):
    variant_id: str
    merchant_name: str
    region: str
    difficulty: str


class MerchantStockItem(TypedDict):
    variant_id: str
    slot_index: int
    item_name: str
    item_count: int
    item_rate: int
    stock: int
    price: int
    currency: str


class InGameMerchantRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_merchants(self) -> list[MerchantInfo]:
        c = self.conn.cursor()
        c.execute(
            "SELECT merchant_name, translation_key, greeting_key, npc_id FROM ingame_merchants ORDER BY merchant_name"
        )
        return [dict(r) for r in c.fetchall()]

    def get_variants(self) -> list[MerchantVariant]:
        c = self.conn.cursor()
        c.execute(
            "SELECT variant_id, merchant_name, region, difficulty FROM ingame_merchant_variants"
            " ORDER BY merchant_name, region, difficulty"
        )
        return [dict(r) for r in c.fetchall()]

    def get_stock(self) -> list[MerchantStockItem]:
        c = self.conn.cursor()
        c.execute(
            "SELECT variant_id, slot_index, item_name, item_count, item_rate, stock, price, currency"
            " FROM ingame_merchant_stock ORDER BY variant_id, slot_index, item_name"
        )
        return [dict(r) for r in c.fetchall()]
