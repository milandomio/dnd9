import json

from config import ITEM_ABILITY_DIR
from consumable_effects import build_effect_index, resolve_item_effects


class ItemEffectsImporter:
    """Persist consumable effect summaries resolved from gameplay assets.

    The numbers behind a consumable (``LuckPotion_5001`` -> ``+100~200``) exist
    only in the unpacked gameplay-effect assets, which the import phase alone may
    read. Exports must stay DB-only, and CI has no game extract at all, so the
    resolved summary is stored here and read back by the shop export.
    """

    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM item_effects")
        # Only goods the merchant actually sells need an effect summary; the
        # export looks them up by the same quality-suffixed item name.
        c.execute("SELECT DISTINCT item_name FROM ingame_merchant_stock")
        sold = {row[0] for row in c.fetchall()}
        effects = resolve_item_effects(sold, build_effect_index(), ITEM_ABILITY_DIR)
        c.executemany(
            "INSERT OR REPLACE INTO item_effects (item_name, effect_json) VALUES (?, ?)",
            [(name, json.dumps(summary, ensure_ascii=False)) for name, summary in sorted(effects.items())],
        )
        self.conn.commit()
        return len(effects)
