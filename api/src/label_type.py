"""Spawner label classification (direct / special / random / other)."""

import re

from translator import QUALITY_RE

LABEL_TYPE_SUFFIX = {
    "direct": "",
    "special": "(特殊)",
    "random": "(随机)",
    "other": "组",
}

# Synthetic props entity: GoldChest special-generator coords only
GOLDCHEST_SPECIAL = "GoldChest_special"
GOLDCHEST_FAMILY = frozenset({"GoldChest", "GoldChest_UnderSea", GOLDCHEST_SPECIAL})


def classify_label(label: str, entity_name: str) -> str:
    if not label:
        return "direct"
    en_base = QUALITY_RE.sub("", entity_name)
    if label == en_base or label.startswith(en_base + "_"):
        return "direct"
    # Fallback: trailing numeric suffix (e.g. Coffin_06 vs Coffin_R)
    en_root = re.sub(r"_\d+$", "", en_base)
    if en_root != en_base and label.startswith(en_root + "_"):
        return "direct"
    if "Random" in label:
        return "random"
    if "Special" in label or label == "ChestLarge" or label.startswith("ChestLarge_"):
        return "special"
    return "other"


def split_goldchest_special_coords(all_coords: dict[str, list]) -> int:
    """Move Special-labeled coords from GoldChest family into all_coords[GoldChest_special].

    Returns number of special coords moved.
    """
    special: list = []
    for key in ("GoldChest", "GoldChest_UnderSea"):
        coords = all_coords.get(key)
        if not coords:
            continue
        keep: list = []
        for c in coords:
            og = c.get("original_keyword") or c.get("keyword") or ""
            if classify_label(og, key) == "special":
                special.append(c)
            else:
                keep.append(c)
        all_coords[key] = keep
    if special:
        existing = all_coords.get(GOLDCHEST_SPECIAL, [])
        # dedupe by position+file
        seen: set[tuple] = set()
        merged: list = []
        for c in existing + special:
            k = (
                c.get("x"),
                c.get("y"),
                c.get("z"),
                c.get("json_filename") or c.get("file"),
                c.get("map_base") or c.get("map"),
            )
            if k in seen:
                continue
            seen.add(k)
            merged.append(c)
        all_coords[GOLDCHEST_SPECIAL] = merged
        return len(merged)
    return 0
