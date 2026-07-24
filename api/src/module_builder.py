"""Module building functions extracted from collector.py."""

import json
import re
from collections import defaultdict
from pathlib import Path

from config import (
    GROUP_TO_ART_DIR,
    HARDCODED_TRANSLATIONS,
    IMG_SRC,
    MODULE_DISPLAY_OVERRIDE,
    MODULE_NAME_OVERRIDE,
    MODULE_OFFSET_MAP,
)
from translator import DEBUG_VARIANT_RE, DUMMY_AS_MONSTER, QUALITY_RE

_dir_cache: dict[Path, list[Path]] = {}


def _list_dir_files(directory: Path) -> list[Path]:
    """Cache directory listing for .png/.webp files."""
    if directory not in _dir_cache:
        try:
            _dir_cache[directory] = [p for p in directory.iterdir() if p.suffix.lower() in (".png", ".webp")]
        except OSError:
            _dir_cache[directory] = []
    return _dir_cache[directory]


def _save(output_dir: Path, filename: str, data: list | dict):
    path = output_dir / filename
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _match_in_dir(directory: Path, sl: str):
    """Match sl against webp/png files in a flat directory using the same logic as _resolve_img."""
    files = _list_dir_files(directory)
    stems_lower = {p.stem.lower(): p.stem for p in files}
    sl_lower = sl.lower()
    # exact
    if sl_lower in stems_lower:
        return stems_lower[sl_lower], "found"
    # tail
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    if tail.lower() in stems_lower:
        return stems_lower[tail.lower()], "found"
    # strip numeric suffix
    sl_stripped = re.sub(r"_\d{2,4}$", "", sl)
    if sl_stripped != sl and sl_stripped.lower() in stems_lower:
        return stems_lower[sl_stripped.lower()], "found"
    tail_stripped = re.sub(r"_\d{2,4}$", "", tail)
    if tail_stripped != tail and tail_stripped.lower() in stems_lower:
        return stems_lower[tail_stripped.lower()], "found"
    # strip _Center/_Corner/_Passage
    sl_center = re.sub(r"_(?:Center|Corner|Passage)(?=_\d|$)", "", sl)
    if sl_center != sl and sl_center.lower() in stems_lower:
        return stems_lower[sl_center.lower()], "found"
    # strip debug suffixes
    sl_debug = re.sub(r"_(?:Resize|Test|BossTest|DistantView)$", "", sl)
    if sl_debug != sl and sl_debug.lower() in stems_lower:
        return stems_lower[sl_debug.lower()], "found"
    # numeric prefix
    if sl_stripped != sl:
        prefix = sl_stripped.lower()
        for s, orig in stems_lower.items():
            if s.startswith(prefix):
                return orig, "found"
    return sl, "not_found"


def _resolve_img(art_root: Path, group: str, sl: str, webp_cache: Path | None = None):
    """Return (resolved_name, status).
    Priority: webp cache first (already processed), then Art directory (raw PNG).
    status: 'found', 'not_found' (searched, no match), 'no_art' (no source available).
    """
    # 1. Always check webp cache first — if a cached webp exists, use it directly
    if webp_cache and webp_cache.exists():
        cached, cache_status = _match_in_dir(webp_cache, sl)
        if cache_status == "found":
            return cached, "found"

    # 2. Fall back to Art directory (raw PNG files)
    if not art_root.exists() or not group:
        return sl, "no_art"
    art_dir_name = GROUP_TO_ART_DIR.get(group, group)
    group_dir = art_root / art_dir_name
    if not group_dir.exists():
        return sl, "no_art"
    # Try exact match (case-insensitive)
    png = group_dir / f"{sl}.png"
    if png.exists():
        return sl, "found"
    for p in _list_dir_files(group_dir):
        if p.stem.lower() == sl.lower():
            return p.stem, "found"
    # Try tail match (part after first underscore)
    tail = sl.split("_", 1)[-1] if "_" in sl else sl
    png = group_dir / f"{tail}.png"
    if png.exists():
        return tail, "found"
    for p in _list_dir_files(group_dir):
        if p.stem.lower() == tail.lower():
            return p.stem, "found"
    # Try stripping numeric suffix (_01, _02 etc.)
    sl_stripped = re.sub(r"_\d{2,4}$", "", sl)
    if sl_stripped != sl:
        for p in _list_dir_files(group_dir):
            if p.stem.lower() == sl_stripped.lower():
                return p.stem, "found"
        tail_stripped = re.sub(r"_\d{2,4}$", "", tail)
        if tail_stripped != tail:
            for p in _list_dir_files(group_dir):
                if p.stem.lower() == tail_stripped.lower():
                    return p.stem, "found"
    # Try stripping _Center / _Corner / _Passage suffix (keep trailing _NN)
    sl_center_stripped = re.sub(r"_(?:Center|Corner|Passage)(?=_\d|$)", "", sl)
    if sl_center_stripped != sl:
        for p in _list_dir_files(group_dir):
            if p.stem.lower() == sl_center_stripped.lower():
                return p.stem, "found"
    # Try stripping _Resize / _Test / _BossTest / _DistantView debug suffixes
    sl_debug_stripped = re.sub(r"_(?:Resize|Test|BossTest|DistantView)$", "", sl)
    if sl_debug_stripped != sl:
        for p in _list_dir_files(group_dir):
            if p.stem.lower() == sl_debug_stripped.lower():
                return p.stem, "found"
    # Try numeric prefix match: after stripping _\d{2,4}$, find any file starting with the stripped prefix
    if sl_stripped != sl:
        prefix = sl_stripped.lower()
        for p in _list_dir_files(group_dir):
            if p.stem.lower().startswith(prefix):
                return p.stem, "found"
    return sl, "not_found"


def build_modules_map(db, resolve_name, module_rotations: dict | None = None) -> dict[str, dict]:
    """Build modules_map from DB dungeon modules. Rotation is read from DB."""
    modules = db.get_dungeon_modules()
    art_root = (
        Path(__file__).parent.parent.parent.parent
        / "Output"
        / "Exports"
        / "DungeonCrawler"
        / "Content"
        / "DungeonCrawler"
        / "Data"
        / "Art"
        / "DungeonModuleMapImage"
    )
    modules_map: dict[str, dict] = {}
    for r in modules:
        override = MODULE_DISPLAY_OVERRIDE.get(r["module_name"], {})
        sx = override.get("size_x", r["size_x"])
        sy = override.get("size_y", r["size_y"])
        custom_range = override.get("range", 0)
        offset_x, offset_y = MODULE_OFFSET_MAP.get(r["module_name"], (0, 0))
        rotate = r["rotation"] if r.get("rotation") is not None else 270
        sl = r["sl_base_name"]
        map_image = r.get("map_image_name", "")
        module_name = r["module_name"]
        PLACEHOLDERS = ("RareModule_1x1", "UnderConstruction_1x1")  # noqa: N806

        def _try_resolve(name: str):
            """Return (resolved_name, status). status: 'found'|'not_found'|'no_art'."""
            resolved, status = _resolve_img(art_root, r["module_group"], name, IMG_SRC)  # noqa: B023
            if resolved in PLACEHOLDERS:  # noqa: B023
                return resolved, status  # placeholder — don't accept
            return resolved, status

        # Priority: try module-name-specific image first (if name differs from sl),
        # fall back to shared sl_base image, then MapImage.
        if module_name != sl:
            img_name, art_status = _try_resolve(module_name)
            if art_status != "found":
                img_name, art_status = _try_resolve(sl)
        else:
            img_name, art_status = _try_resolve(sl)

        # If result is still a placeholder, try MapImage
        if img_name in PLACEHOLDERS and map_image and map_image not in PLACEHOLDERS:
            candidate, _ = _try_resolve(map_image)
            if candidate not in PLACEHOLDERS:
                img_name = candidate

        # Fallback: strip variant suffixes (_D, _A, _S) from module_name and check IMG_SRC for .webp
        if art_status in ("not_found", "no_art") and img_name not in PLACEHOLDERS:  # noqa: SIM102
            if not (IMG_SRC / f"{img_name}.webp").exists() and module_name:
                stripped = re.sub(r"_[A-Z]$", "", module_name)
                if stripped != module_name and (IMG_SRC / f"{stripped}.webp").exists():
                    img_name = stripped

        # Final fallback: if nothing matched and the only candidate was a placeholder,
        # keep the placeholder so the frontend shows RareModule_1x1.webp.
        # Only when Art was searched (not_found) AND sl == module_name (single source) AND MapImage was a placeholder.
        if not img_name or img_name in PLACEHOLDERS:
            img_name = module_name or ""
        elif art_status == "not_found" and img_name == module_name == sl and map_image in PLACEHOLDERS:
            img_name = map_image
        has_img = (IMG_SRC / f"{img_name}.webp").exists()
        # Final fallback: no image found → use placeholder so frontend shows a fallback
        if not has_img:
            img_name = "RareModule_1x1"
            has_img = True
        aliases = r.get("aliases", []) or []
        modules_map[r["module_name"]] = {
            "name": r["module_name"],
            "translation_key": r["translation_key"],
            "translation": resolve_name(r["module_name"], r["translation_key"], "module"),
            "group": r["module_group"],
            "size_x": sx,
            "size_y": sy,
            "sl_base_name": sl,
            "img_name": img_name,
            "has_img": has_img,
            "offset_x": offset_x,
            "offset_y": offset_y,
            "rotate": rotate,
            "range": custom_range,
            "aliases": aliases,
        }
    for override_name, override_translation in MODULE_NAME_OVERRIDE.items():
        if override_name not in modules_map:
            resolved_name, _ = _resolve_img(art_root, "", override_name, IMG_SRC)
            modules_map[override_name] = {
                "name": override_name,
                "translation": override_translation,
                "group": "",
                "size_x": 1,
                "size_y": 1,
                "sl_base_name": override_name,
                "img_name": resolved_name,
                "has_img": (IMG_SRC / f"{resolved_name}.webp").exists(),
                "offset_x": 0,
                "offset_y": 0,
                "rotate": 270,
                "range": 0,
            }
    return modules_map


def build_map_mappings(modules_map: dict[str, dict]) -> tuple[dict[str, str], dict[str, set[str]]]:
    """Build module name ↔ map name bidirectional mappings."""
    # map_base → module_name（正向：地图名查模块名）
    map_to_module: dict[str, str] = {}
    # module_name → {关联的所有 map_base}（反向：模块名查地图名）
    module_to_maps: dict[str, set[str]] = {}
    # 第一遍：建立直接映射 (module_name → module_name)
    for mn in modules_map:
        map_to_module[mn] = mn
        module_to_maps.setdefault(mn, set()).add(mn)
    # 第二遍：建立 sl_base 映射 (sl_base → module_name)
    # DungeonModule JSON 定义的模块名优先于地图文件名，允许覆盖直接映射
    # 但如果 sl 已经自映射（自身就是该 sublevel 的主模块），则保留自映射不被覆盖
    for mn, mod in modules_map.items():
        sl = mod["sl_base_name"]
        if sl and sl != mn:
            if map_to_module.get(sl) != sl:
                map_to_module[sl] = mn
            if sl not in modules_map:
                module_to_maps.setdefault(mn, set()).add(sl)
    return map_to_module, module_to_maps


def build_and_save_module_coords(
    db,
    modules_map: dict[str, dict],
    map_to_module: dict[str, str],
    resolve_name,
    items: list[dict],
    monsters: list[dict],
    props: list[dict],
    output_dir: Path,
) -> dict[str, dict]:
    """Build and save module coordinates. Returns merged_coords."""
    # Build entity classification index from DB (ground truth type)
    entity_class = db.get_entity_classification()
    # _Dummy 实体同时也是怪物，补全 monster 翻译键
    for name in DUMMY_AS_MONSTER:
        if name in entity_class:
            if "monster" not in entity_class[name]["types"]:
                entity_class[name]["types"].append("monster")
            if not entity_class[name]["translation_key"]:
                base = QUALITY_RE.sub("", name)
                if base != name:
                    entity_class[name]["translation_key"] = "Text_DesignData_Monster_Monster_" + base
        else:
            base = QUALITY_RE.sub("", name)
            entity_class[name] = {
                "types": ["props", "monster"],
                "translation_key": "Text_DesignData_Monster_Monster_" + base,
            }
    # SuperHoard 类 spawner 作为独立 props 实体注入（无 DB entity 记录）
    for _sh_name in ("SuperHoard01_9", "SuperHoardChest01_9"):
        if _sh_name not in entity_class:
            entity_class[_sh_name] = {"types": ["props"], "translation_key": ""}
    _save(
        output_dir,
        "entity_index.json",
        [
            {"name": n, "types": v["types"], "translation_key": v["translation_key"]}
            for n, v in sorted(entity_class.items())
        ],
    )

    # Build translation lookup from DB entity tables (covers all names including props variants)
    trans_lookup = {}
    for r in items:
        trans_lookup[r["item_name"]] = resolve_name(r["item_name"], r["translation_key"], "item")
    for r in monsters:
        trans_lookup[r["monster_name"]] = resolve_name(r["monster_name"], r["translation_key"], "monster")
    for r in props:
        trans_lookup[r["asset_name"]] = resolve_name(r["asset_name"], r["translation_key"], "props")

    _MODULE_COLORS = [  # noqa: N806
        "#E74C3C",
        "#3498DB",
        "#2ECC71",
        "#F39C12",
        "#9B59B6",
        "#1ABC9C",
        "#E67E22",
        "#2980B9",
        "#27AE60",
        "#D35400",
        "#8E44AD",
        "#16A085",
        "#C0392B",
        "#2C3E50",
        "#7F8C8D",
        "#FF6B35",
        "#00BFFF",
        "#FFD700",
        "#FF69B4",
        "#32CD32",
        "#FF4500",
        "#9370DB",
        "#00FA9A",
        "#DC143C",
        "#00CED1",
    ]
    rows = (
        db.connect()
        .execute(
            "SELECT keyword, original_keyword, spawner_type, has_lootdrop, x, y, z, yaw, version, map_base, group_parent, sub_group_parent FROM spawners ORDER BY map_base, keyword"
        )
        .fetchall()
    )
    module_coords: dict[str, dict] = {}
    color_idx = 0
    for row in rows:
        mb = row["map_base"]
        if not mb:
            continue
        if mb not in module_coords:
            module_coords[mb] = {"map_base": mb, "entities": {}}
        ek = row["keyword"]
        if ek not in module_coords[mb]["entities"]:
            cls = entity_class.get(ek, {})
            st = row["spawner_type"]
            has_ld = row["has_lootdrop"]
            # Determine entity type: decoration (no lootdrop), item (lootdrop type), or props/monster
            if st == "lootdrop":
                mapped_st = "item"
            elif st == "props" and has_ld == 0:
                mapped_st = "decoration"
            else:
                mapped_st = st
            if cls:
                types = cls.get("types", [])
                # If mapped_st is decoration, always use it (overrides props classification)
                if mapped_st == "decoration":
                    entity_type = "decoration"
                else:
                    entity_type = mapped_st if mapped_st in types else types[0]
            else:
                entity_type = mapped_st
            translation = trans_lookup.get(ek) or resolve_name(ek, None, entity_type)
            module_coords[mb]["entities"][ek] = {
                "name": ek,
                "translation": translation,
                "type": entity_type,
                "color": _MODULE_COLORS[color_idx % len(_MODULE_COLORS)],
                "coords": [],
            }
            color_idx += 1
        try:
            gp = row["group_parent"] or ""
        except (KeyError, IndexError):
            gp = ""
        try:
            sgp = row["sub_group_parent"] or ""
        except (KeyError, IndexError):
            sgp = ""
        module_coords[mb]["entities"][ek]["coords"].append(
            {
                "x": row["x"],
                "y": row["y"],
                "z": row["z"],
                "yaw": row["yaw"],
                "version": row["version"] or "",
                "label": HARDCODED_TRANSLATIONS.get(row["original_keyword"], row["original_keyword"]),
                "group_parent": gp,
                "sub_group_parent": sgp,
            }
        )
    # 按模块名合并坐标并保存（处理多个 map_base 映射到同一模块的情况）
    merged_coords: dict[str, dict] = {}
    for mb, data in module_coords.items():
        target = map_to_module.get(mb, mb)
        if target not in merged_coords:
            merged_coords[target] = {"map_base": target, "entities": {}}
        for ek, entity in data["entities"].items():
            if ek not in merged_coords[target]["entities"]:
                merged_coords[target]["entities"][ek] = entity
            else:
                merged_coords[target]["entities"][ek]["coords"].extend(entity["coords"])
    # 按 (translation, type) 合并同翻译实体（如 GlowingCoralRoaster01_On/02/03 → 灯架子）
    for target_name, data in merged_coords.items():
        merge_groups: dict[tuple, list[dict]] = {}
        for entity in data["entities"].values():
            key = (entity["translation"], entity["type"])
            merge_groups.setdefault(key, []).append(entity)
        merged_entities = []
        for (_trans, _type), group in merge_groups.items():
            if len(group) == 1:
                entity = group[0]
                coords = entity["coords"]
                gps = {c.get("group_parent", "") for c in coords}
                if len(gps) == 1 and "" not in gps and len(coords) > 1:
                    entity["mutually_exclusive"] = True
                else:
                    entity["mutually_exclusive"] = False
                merged_entities.append(entity)
                continue
            canonical = min(group, key=lambda e: len(e["name"]))
            seen: set[tuple] = set()
            deduped = []
            for e in group:
                for c in e["coords"]:
                    ck = (c["x"], c["y"], c["z"], c.get("label", ""))
                    if ck not in seen:
                        seen.add(ck)
                        deduped.append(c)
            all_group_parents = {c.get("group_parent", "") for e in group for c in e["coords"]}
            is_mutex = len(all_group_parents) == 1 and "" not in all_group_parents and len(deduped) > 1
            merged_entities.append(
                {
                    "name": canonical["name"],
                    "translation": _trans,
                    "type": _type,
                    "color": canonical["color"],
                    "coords": deduped,
                    "mutually_exclusive": is_mutex,
                    "group_size": len(deduped) if is_mutex else None,
                }
            )
        _save(
            output_dir,
            f"dungeon_modules_coords/{target_name}.json",
            {
                "map_base": target_name,
                "entities": merged_entities,
            },
        )
    # 清理孤立坐标文件（旧 map_base 命名残留）
    coord_dir = output_dir / "dungeon_modules_coords"
    if coord_dir.exists():
        expected = set(merged_coords.keys())
        for p in coord_dir.iterdir():
            if p.suffix == ".json" and p.stem not in expected:
                p.unlink()
    print(f"  module coords: {len(merged_coords)} modules with coordinates")
    return merged_coords


def build_and_save_modules_data(
    modules_map: dict[str, dict],
    module_to_maps: dict[str, set[str]],
    merged_coords: dict[str, dict],
    output_dir: Path,
) -> list[dict]:
    """Build and save modules_data list."""
    # ── dungeon_modules.json（在坐标构建之后保存，过滤无坐标模块）──
    # 合并使用相同翻译键（相同地图）的模块
    translation_groups: dict[str, list[dict]] = defaultdict(list)
    for mod in modules_map.values():
        tk = mod.get("translation_key", "")
        if tk:
            translation_groups[tk].append(mod)
        else:
            # 无翻译键的模块单独处理
            translation_groups[mod["name"]].append(mod)

    merged_modules: list[dict] = []
    for _tk, group in translation_groups.items():
        if len(group) == 1:
            # 单个模块，直接使用
            mod = group[0].copy()
            # 收集所有名称：主名称 + 别名
            all_names = [mod["name"]] + mod.get("aliases", [])
            mod["names"] = list(dict.fromkeys(all_names))  # 去重保序
            merged_modules.append(mod)
        else:
            # 多个模块共享同一翻译，合并
            primary = group[0].copy()
            # 收集所有名称：所有模块主名称 + 所有别名
            all_names = []
            for m in group:
                all_names.append(m["name"])
                all_names.extend(m.get("aliases", []))
            primary["names"] = list(dict.fromkeys(all_names))  # 去重保序
            # 合并 sl_base_name 列表
            all_sl_bases = list(dict.fromkeys(m["sl_base_name"] for m in group if m["sl_base_name"]))
            primary["all_sl_base_names"] = all_sl_bases
            merged_modules.append(primary)

    modules_data = sorted(merged_modules, key=lambda x: x["name"])
    modules_data = [m for m in modules_data if not DEBUG_VARIANT_RE.search(m["name"])]
    # 过滤无坐标模块（详情页无数据的模块从列表中剔除）
    # 仅当模块自身名字在 merged_coords 中才算有坐标（排除 sl_base 指向其他模块的别名）
    modules_with_coords = {mn for mn in modules_map if mn in merged_coords}
    exempt = set(MODULE_NAME_OVERRIDE.keys())
    before_count = len(modules_data)
    modules_data = [m for m in modules_data if m["name"] in modules_with_coords or m["name"] in exempt]
    # 标记是否含有物品/怪物坐标（仅 props 的模块在列表页默认隐藏）
    for m in modules_data:
        # 合并后的模块检查所有相关地图
        maps = set()
        for name in m.get("names", [m["name"]]):
            maps.update(module_to_maps.get(name, {name}))
        has_useful = False
        for mk in maps:
            if mk in merged_coords:
                for e in merged_coords[mk]["entities"].values():
                    if e["type"] in ("item", "monster"):
                        has_useful = True
                        break
            if has_useful:
                break
        m["has_useful_entities"] = has_useful
    filtered_count = before_count - len(modules_data)
    if filtered_count:
        print(f"  filtered {filtered_count} modules without coordinates")
    _save(output_dir, "dungeon_modules.json", modules_data)
    return modules_data
