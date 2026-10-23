import re

from config import (
    INGAME_MERCHANT_DIR,
    INGAME_MERCHANT_SCHEDULE_DIR,
    INGAME_MERCHANT_STOCK_BUY_DIR,
)

from .._helpers import load_json_dir, ue_asset_base_name

# Merchant / Schedule / StockBuy assets share one suffix:
#   Id_InGameMerchant_GoblinSmuggler_Crypts_N
#   Id_InGameMerchantSchedule_GoblinSmuggler_Crypts_N
#   Id_InGameMerchantStockBuy_GoblinSmuggler_Crypts_N_01
_PREFIX_RE = re.compile(r"^Id_InGameMerchant(?:Schedule|StockBuy)?_")
_SUFFIX_RE = re.compile(r"^(?P<merchant>.+)_(?P<region>[A-Za-z]+)_(?P<difficulty>N|HR)$")
_SLOT_RE = re.compile(r"^(?P<base>.+)_(?P<slot>\d+)$")


def parse_asset_name(asset_name: str) -> tuple[str, str, str, int | None]:
    """Split a merchant asset name into (variant_id, region, difficulty, slot).

    ``variant_id`` is difficulty-tagged and shared by the Merchant, Schedule and
    StockBuy assets of one merchant in one region. ``slot`` is None unless the
    asset is a numbered stock-buy slot.
    """
    stripped = _PREFIX_RE.sub("", asset_name)
    slot: int | None = None
    slot_match = _SLOT_RE.match(stripped)
    if slot_match:
        stripped = slot_match.group("base")
        slot = int(slot_match.group("slot"))
    match = _SUFFIX_RE.match(stripped)
    if not match:
        return "", "", "", None
    merchant = match.group("merchant")
    region = match.group("region")
    difficulty = match.group("difficulty")
    return f"{merchant}_{region}_{difficulty}", region, difficulty, slot


def parse_merchant_name(asset_name: str) -> str:
    """Merchant display identity, shared across regions and difficulties."""
    variant_id, _, _, _ = parse_asset_name(asset_name)
    return variant_id.rsplit("_", 2)[0] if variant_id else ""


def _asset_item_name(ue_path: str) -> str:
    """Item/currency name without the `Id_Item_` asset prefix.

    ``ue_asset_base_name`` yields the asset stem (``Id_Item_GoldCoins``) while
    the rest of the pipeline keys entities by the bare name (``GoldCoins``).
    """
    return (ue_asset_base_name(ue_path) or "").removeprefix("Id_Item_")


class InGameMerchantImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> dict[str, int]:
        self._import_merchants()
        variants = self._import_variants()
        stock = self._import_stock()
        self.conn.commit()
        c = self.conn.cursor()
        c.execute("SELECT COUNT(*) FROM ingame_merchants")
        return {"merchants": c.fetchone()[0], "variants": variants, "stock": stock}

    def _import_merchants(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM ingame_merchants")
        rows = {}
        for asset_name, data_list in sorted(load_json_dir(INGAME_MERCHANT_DIR).items()):
            if not data_list:
                continue
            merchant_name = parse_merchant_name(asset_name)
            if not merchant_name:
                continue
            props = data_list[0].get("Properties", {}) or {}
            greetings = props.get("GreetingTexts") or []
            # Every region/difficulty variant repeats the same merchant block but
            # points at its own NPC asset; keep the first deterministically and
            # treat npc_id as one representative instance.
            rows.setdefault(
                merchant_name,
                (
                    merchant_name,
                    (props.get("Name") or {}).get("Key", "") or "",
                    (greetings[0].get("Key", "") if greetings else "") or "",
                    ue_asset_base_name((props.get("NpcId") or {}).get("AssetPathName", "")) or "",
                ),
            )
        c.executemany(
            "INSERT OR REPLACE INTO ingame_merchants (merchant_name, translation_key, greeting_key, npc_id)"
            " VALUES (?, ?, ?, ?)",
            list(rows.values()),
        )
        return len(rows)

    def _import_variants(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM ingame_merchant_variants")
        rows = []
        for asset_name in sorted(load_json_dir(INGAME_MERCHANT_SCHEDULE_DIR)):
            variant_id, region, difficulty, _ = parse_asset_name(asset_name)
            if not variant_id:
                continue
            rows.append((variant_id, parse_merchant_name(asset_name), region, difficulty))
        c.executemany(
            "INSERT OR REPLACE INTO ingame_merchant_variants (variant_id, merchant_name, region, difficulty)"
            " VALUES (?, ?, ?, ?)",
            rows,
        )
        return len(rows)

    def _schedule_stock_refs(self) -> dict[str, list[str]]:
        """Map each Schedule asset to the StockBuy assets it references.

        The Equip stock files are shared by every region: Crypts/Goblin/IceCavern
        schedules all point at the same three Equip_*_N files. Reading the
        reference lists here (instead of trusting the filename) is what lets the
        export attach the shared stock to every region that sells it.
        """
        refs: dict[str, list[str]] = {}
        for asset_name, data_list in sorted(load_json_dir(INGAME_MERCHANT_SCHEDULE_DIR).items()):
            if not data_list:
                continue
            variant_id, _, _, _ = parse_asset_name(asset_name)
            if not variant_id:
                continue
            props = data_list[0].get("Properties", {}) or {}
            buys = [ue_asset_base_name((x or {}).get("AssetPathName", "")) or "" for x in props.get("StockBuy") or []]
            refs[variant_id] = [b for b in buys if b]
        return refs

    def _import_stock(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM ingame_merchant_stock")
        schedule_refs = self._schedule_stock_refs()
        # StockBuy asset -> the region variants that reference it. Regular stock
        # is owned by its own region; Equip_* files are referenced by all three
        # region schedules, so their rows are copied into each region variant.
        ownership: dict[str, list[str]] = {}
        for variant_id, buys in schedule_refs.items():
            for buy in buys:
                ownership.setdefault(buy, [])
                if variant_id not in ownership[buy]:
                    ownership[buy].append(variant_id)
        rows = []
        for asset_name, data_list in sorted(load_json_dir(INGAME_MERCHANT_STOCK_BUY_DIR).items()):
            if not data_list:
                continue
            variant_id, _, _, slot = parse_asset_name(asset_name)
            if not variant_id or slot is None:
                continue
            props = data_list[0].get("Properties", {}) or {}
            # Equip_* 文件没有自己的 region：三个地区 Schedule 都引用它们。
            # 有归属记录时按归属展开（每个地区一份），否则按文件名归属原 variant。
            buy_base = asset_name.rsplit(".", 1)[0].rsplit("/", 1)[-1]
            target_variants = ownership.get(buy_base, []) or [variant_id]
            # Equip 文件名后缀的 01/02/03 是文件序号而不是商店槽位；三个文件内容
            # 完全相同，且槽号 1 会与各地区的治疗药水槽冲突，统一映射到 90。
            display_slot = 90 if "_Equip_" in buy_base else slot
            for entry in props.get("InGameMerchantStockBuyItemArray") or []:
                item_name = _asset_item_name((entry.get("ItemId") or {}).get("AssetPathName", ""))
                if not item_name:
                    continue
                currency = _asset_item_name((entry.get("RequiredItemId_01") or {}).get("AssetPathName", ""))
                for target in target_variants:
                    rows.append(
                        (
                            target,
                            display_slot,
                            item_name,
                            int(entry.get("ItemCount") or 1),
                            int(entry.get("ItemRate") or 0),
                            int(entry.get("Stock") or 0),
                            int(entry.get("RequiredAmount01") or 0),
                            currency,
                        )
                    )
        c.executemany(
            "INSERT OR REPLACE INTO ingame_merchant_stock"
            " (variant_id, slot_index, item_name, item_count, item_rate, stock, price, currency)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            rows,
        )
        return len(rows)
