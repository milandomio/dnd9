import json

from config import ITEM_DIR, ITEM_PROPERTY_DIR, ITEM_PROPERTY_TYPE_DIR
from item_properties import resolve_item_properties


class ItemPropertiesImporter:
    """Persist the stat lines every item asset resolves to.

    An item's numbers (armour rating 19~20, action speed 20 -> 2%, the pool its
    three random rolls draw from) live in separate ItemProperty assets that only
    the import phase may read — CI builds have no game extract at all. The
    resolved summary is therefore stored here and read back by the DB-only
    【工匠】 export (see ``item_properties.py`` for the parsing rules).
    """

    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> dict:
        items, pools = resolve_item_properties(ITEM_DIR, ITEM_PROPERTY_DIR, ITEM_PROPERTY_TYPE_DIR)
        c = self.conn.cursor()
        c.execute("DELETE FROM item_properties")
        c.execute("DELETE FROM item_property_pools")
        c.executemany(
            "INSERT OR REPLACE INTO item_properties"
            " (raw_name, primary_json, secondary_pool, secondary_rolls) VALUES (?, ?, ?, ?)",
            [
                (
                    raw_name,
                    json.dumps(entry["primary"], ensure_ascii=False, separators=(",", ":")),
                    entry["secondary_pool"],
                    entry["secondary_rolls"],
                )
                for raw_name, entry in sorted(items.items())
            ],
        )
        c.executemany(
            "INSERT OR REPLACE INTO item_property_pools (pool_name, entries_json) VALUES (?, ?)",
            [
                (pool_name, json.dumps(rows, ensure_ascii=False, separators=(",", ":")))
                for pool_name, rows in sorted(pools.items())
            ],
        )
        self.conn.commit()
        return {"items": len(items), "pools": len(pools)}
