from typing import TypedDict


class ItemEntity(TypedDict):
    item_name: str
    raw_name: str
    translation_key: str
    category: str
    variant_count: int
    item_type: str
    item_category_key: str
    item_subtype_keys: str


class ItemWithMatches(TypedDict):
    item_name: str
    translation_key: str
    category: str
    monster_names: list[str]


class ItemsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[ItemEntity]:
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(item_entities)")
        columns = {row[1] for row in c.fetchall()}
        optional_columns = {
            "item_type": "''",
            "item_category_key": "''",
            "item_subtype_keys": "'[]'",
        }
        selected_optional = ", ".join(
            f"{column} AS {column}" if column in columns else f"{fallback} AS {column}"
            for column, fallback in optional_columns.items()
        )
        c.execute(
            "SELECT item_name, raw_name, translation_key, category, variant_count, "
            f"{selected_optional} FROM item_entities ORDER BY item_name"
        )
        return [dict(r) for r in c.fetchall()]

    def get_with_matches(self) -> list[ItemWithMatches]:
        c = self.conn.cursor()
        c.execute("""
            SELECT e.item_name, e.translation_key, e.category,
                   GROUP_CONCAT(DISTINCT l.monster_name) as monster_names
            FROM item_entities e
            LEFT JOIN lootdrop_items l ON e.item_name = l.item_name
            GROUP BY e.item_name
            ORDER BY e.item_name
        """)
        results = []
        for r in c.fetchall():
            d = dict(r)
            d["monster_names"] = d["monster_names"].split(",") if d["monster_names"] else []
            results.append(d)
        return results
