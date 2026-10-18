"""Import tavern crafting recipes (V2/Merchant/StockCraft) for the 【工匠】 page.

Each recipe turns materials into one output item, and the same item appears in
several recipes at different qualities (SurgicalKit_2001 -> SurgicalKit_3001 ->
SurgicalKit_4001), so the page groups recipes by folded output name.

Only the importer may read the game extract; every recipe is persisted here so
the export (including CI, which has no extract) stays DB-only.

Recipe -> NPC association, in order of precedence:

1. Recipes that only consume raw ore / coins (``CopperOres`` -> ``CopperPowder``
   and ``CopperIngots``, ``SilverCoin`` -> ``SilverPowder`` and ``SilverIngots``)
   are pure refining and carry no merchant in the game data: they all go to the
   synthetic 【矿类】 tab (``__ores__``).
2. ``Id_StockCraft_<Merchant>_<NN>`` where ``<Merchant>`` is a merchant that
   serves the Craft service (Alchemist, Armourer, Goldsmith, Leathersmith,
   Surgeon, Tailor, Weaponsmith, Woodsman).
3. The recipe's conversation key ``..._StockCraft_Conversation_<Merchant>_...``
   (the coin-bag recipes carry ``Leathersmith_Craft``).
4. Fallback: ``__ores__``.
"""

import json
import re

from config import CRAFT_MERCHANT_DIR, CRAFT_STOCK_DIR

from .._helpers import load_json_dir, ue_asset_base_name

#: Synthetic owner for the ore/coin refining recipes, which carry no merchant.
ORE_MERCHANT = "__ores__"

#: Raw ore item names end with this, and these two are the raw currencies.
_ORE_SUFFIX = "Ores"
_RAW_CURRENCIES = frozenset({"SilverCoin", "GoldCoins"})

#: ``Id_StockCraft_<group>_<NN>``.
_STOCK_ASSET_RE = re.compile(r"^Id_StockCraft_(?P<group>.+?)_(?P<index>\d+)$")
_CONVERSATION_MERCHANT_RE = re.compile(r"_StockCraft_Conversation_(?P<merchant>[A-Za-z]+)(?:_|$)")
_QUALITY_SUFFIX_RE = re.compile(r"_\d{4}$")
_MERCHANT_PREFIX = "Id_Merchant_"

#: Item quality suffix -> rarity key, matching the lootdrop and shop pages.
SUFFIX_RARITY = {
    "1001": "Poor",
    "2001": "Common",
    "3001": "Uncommon",
    "4001": "Rare",
    "5001": "Epic",
    "6001": "Legend",
    "7001": "Unique",
    "8001": "Artifact",
}

#: Requirement slots on a recipe (``RequiredItemId_01`` .. ``_05``).
_REQUIREMENT_SLOTS = 5


def _item_parts(ue_path: str) -> tuple[str, str, str]:
    """Split a recipe item asset path into (raw_name, folded_name, suffix).

    ``/Game/.../Id_Item_VoidBlade_5001.Id_Item_VoidBlade_5001`` becomes
    ``("VoidBlade_5001", "VoidBlade", "5001")``; suffix-less assets fold to
    themselves.
    """
    stem = ue_asset_base_name(ue_path) or ""
    raw_name = stem.removeprefix("Id_Item_")
    match = _QUALITY_SUFFIX_RE.search(raw_name)
    if not match:
        return raw_name, raw_name, ""
    suffix = match.group(0)[1:]
    return raw_name, raw_name[: -len(suffix) - 1], suffix


def _merchant_from_conversation(conversation_key: str) -> str:
    match = _CONVERSATION_MERCHANT_RE.search(conversation_key or "")
    return match.group("merchant") if match else ""


def _is_refining(requirements: list[dict]) -> bool:
    """True when every material is raw ore or a raw coin (pure refining)."""
    return bool(requirements) and all(
        requirement["name"].endswith(_ORE_SUFFIX) or requirement["name"] in _RAW_CURRENCIES
        for requirement in requirements
    )


class CraftsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> dict[str, int]:
        merchants = self._craft_merchants()
        recipes, owners = self._import_recipes(merchants)
        self._import_merchants(merchants, owners)
        self.conn.commit()
        return {"merchants": len(owners), "recipes": recipes}

    def _craft_merchants(self) -> dict[str, tuple[str, int]]:
        """Map merchant token -> (translation_key, tavern order) for Craft NPCs."""
        merchants: dict[str, tuple[str, int]] = {}
        for asset_name, data_list in sorted(load_json_dir(CRAFT_MERCHANT_DIR).items()):
            if not data_list:
                continue
            props = data_list[0].get("Properties") or {}
            services = [str(service) for service in (props.get("ServiceTypes") or [])]
            if not any(service.endswith("Craft") for service in services):
                continue
            token = asset_name.removeprefix(_MERCHANT_PREFIX)
            if not token:
                continue
            merchants[token] = (
                (props.get("Name") or {}).get("Key", "") or "",
                int(props.get("Order") or 0),
            )
        return merchants

    def _import_recipes(self, merchants: dict[str, tuple[str, int]]) -> tuple[int, set[str]]:
        c = self.conn.cursor()
        c.execute("DELETE FROM craft_recipes")
        rows = []
        owners: set[str] = set()
        for asset_name, data_list in sorted(load_json_dir(CRAFT_STOCK_DIR).items()):
            if not data_list:
                continue
            props = data_list[0].get("Properties") or {}
            group_match = _STOCK_ASSET_RE.match(asset_name)
            group = group_match.group("group") if group_match else ""
            for index, entry in enumerate(props.get("StockCraftItemArray") or []):
                if not isinstance(entry, dict):
                    continue
                conversation_key = (entry.get("ConversationText") or {}).get("Key", "") or ""
                output_raw, output_item, output_suffix = _item_parts(
                    (entry.get("ItemId") or {}).get("AssetPathName", "")
                )
                if not output_item:
                    continue
                requirements = []
                for slot in range(1, _REQUIREMENT_SLOTS + 1):
                    required = entry.get(f"RequiredItemId_0{slot}") or {}
                    raw_name, item_name, suffix = _item_parts(required.get("AssetPathName", ""))
                    if not item_name:
                        continue
                    requirements.append(
                        {
                            "name": item_name,
                            "raw_name": raw_name,
                            "rarity": SUFFIX_RARITY.get(suffix, ""),
                            "amount": int(entry.get(f"RequiredAmount0{slot}") or 0) or 1,
                        }
                    )
                merchant_name = self._owner(group, conversation_key, requirements, merchants)
                owners.add(merchant_name)
                rows.append(
                    (
                        f"{asset_name}#{index}",
                        merchant_name,
                        int(entry.get("UniqueID") or 0),
                        output_raw,
                        output_item,
                        SUFFIX_RARITY.get(output_suffix, ""),
                        json.dumps(requirements, ensure_ascii=False, separators=(",", ":")),
                        conversation_key,
                        (entry.get("CraftCompleteText") or {}).get("Key", "") or "",
                    )
                )
        c.executemany(
            "INSERT OR REPLACE INTO craft_recipes"
            " (recipe_id, merchant_name, unique_id, output_raw_name, output_item_name,"
            " output_rarity, requirements_json, conversation_key, craft_complete_key)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        return len(rows), owners

    def _import_merchants(self, merchants: dict[str, tuple[str, int]], owners: set[str]) -> None:
        c = self.conn.cursor()
        c.execute("DELETE FROM craft_merchants")
        rows = []
        for merchant_name in owners:
            if merchant_name == ORE_MERCHANT:
                # Sort the synthetic tab after every real NPC.
                translation_key, order = "", 1000
                kind = "ores"
            else:
                translation_key, order = merchants.get(merchant_name, ("", 0))
                kind = "npc"
            rows.append((merchant_name, kind, translation_key, order))
        rows.sort(key=lambda row: (row[3], row[0]))
        c.executemany(
            "INSERT OR REPLACE INTO craft_merchants (merchant_name, kind, translation_key, sort_order)"
            " VALUES (?, ?, ?, ?)",
            rows,
        )

    @staticmethod
    def _owner(
        group: str,
        conversation_key: str,
        requirements: list[dict],
        merchants: dict[str, tuple[str, int]],
    ) -> str:
        # Pure ore/coin refining belongs to the synthetic 【矿类】 tab even when the
        # asset carries a merchant group (the Alchemist crafts every ore powder).
        if _is_refining(requirements):
            return ORE_MERCHANT
        if group in merchants:
            return group
        conversation_merchant = _merchant_from_conversation(conversation_key)
        if conversation_merchant in merchants:
            return conversation_merchant
        return ORE_MERCHANT
