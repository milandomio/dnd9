import json

from config import ITEM_ABILITY_DIR
from consumable_effects import (
    build_effect_index,
    load_fixed_effects,
    resolve_item_effects,
)


class ItemEffectsImporter:
    """Persist consumable effect summaries resolved from gameplay assets.

    The numbers behind a consumable (``LuckPotion_5001`` -> ``+100~200``,
    ``ProtectionPotion_5001`` -> 30 shield for 24s) exist only in the unpacked
    gameplay-effect assets, which the import phase alone may read. Exports must
    stay DB-only, and CI has no game extract at all, so the resolved summary is
    stored here and read back by the shop export.
    """

    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM item_effects")
        # Every item whose numbers a page must show needs an effect summary: the
        # shop goods a merchant sells, plus everything a crafter can build (the
        # Protection potions are crafted but never sold). Both exports look the
        # summary up by the same quality-suffixed item name.
        wanted: set[str] = set()
        c.execute("SELECT DISTINCT item_name FROM ingame_merchant_stock")
        wanted.update(row[0] for row in c.fetchall())
        c.execute("SELECT DISTINCT output_raw_name FROM craft_recipes WHERE output_raw_name != ''")
        wanted.update(row[0] for row in c.fetchall())
        effects = resolve_item_effects(
            wanted,
            build_effect_index(),
            ITEM_ABILITY_DIR,
            fixed_index=load_fixed_effects(),
        )
        c.executemany(
            "INSERT OR REPLACE INTO item_effects (item_name, effect_json) VALUES (?, ?)",
            [(name, json.dumps(summary, ensure_ascii=False)) for name, summary in sorted(effects.items())],
        )
        self.conn.commit()
        return len(effects)
