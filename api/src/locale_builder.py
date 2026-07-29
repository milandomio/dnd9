"""Locale dictionary export for frontend i18n."""

import json
from pathlib import Path

from config import (
    SUPERHOARD_I18N,
    SUPERHOARD_I18N_KEY,
    hardcoded_locale_entries,
)

SUPPORTED_LANGUAGES = (
    "zh-Hans",
    "en",
    "de",
    "es",
    "fr",
    "ja",
    "ko",
    "pt-BR",
    "ru",
    "zh-Hant",
)

# Always export: drop-rate mode labels (not entity translation_keys)
FILTER_MODE_LOCALE_KEYS = (
    "Text_Code_DCPartyFinderCreateWidget_FilterModePvE",
    "Text_Code_DCPartyFinderCreateWidget_FilterModeNormal",
    "Text_Code_DCPartyFinderCreateWidget_FilterModeHighRoller",
    "Text_Code_DCPartyFinderCreateWidget_FilterModeSquireRoyale",
)


def _collect_keys(obj, used: set[str]):
    """Recursively collect translation_key values from a JSON structure."""
    if isinstance(obj, dict):
        for key in (
            "translation_key",
            "dungeon_translation_key",
            "rarity_translation_key",
        ):
            tk = obj.get(key)
            if tk and isinstance(tk, str):
                used.add(tk)
        for v in obj.values():
            _collect_keys(v, used)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, used)


def _load_used_keys(output_dir: Path, lootdrop_keys: set[str] | None = None) -> set[str]:
    """Load all translation_keys actually used in search_index + entity data files."""
    used: set[str] = set(lootdrop_keys or ())

    si_path = output_dir / "search_index.json"
    if si_path.exists():
        with open(si_path, encoding="utf-8") as f:
            idx = json.load(f)
        for entry in idx:
            tk = entry.get("translation_key")
            if tk:
                used.add(tk)

    subdirs = (
        ("items", "monsters", "props") if lootdrop_keys is not None else ("items", "monsters", "props", "lootdrops")
    )
    for subdir in subdirs:
        dir_path = output_dir / subdir
        if not dir_path.exists():
            continue
        for fpath in dir_path.iterdir():
            if fpath.suffix != ".json":
                continue
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
            except (json.JSONDecodeError, OSError):
                continue
            _collect_keys(data, used)

    dm_path = output_dir / "dungeon_modules.json"
    if dm_path.exists():
        try:
            with open(dm_path, encoding="utf-8") as f:
                dm = json.load(f)
            for m in dm:
                gk = m.get("group_key")
                if gk:
                    used.add(gk)
                gsk = m.get("group_sub_key")
                if gsk:
                    used.add(gsk)
        except (json.JSONDecodeError, OSError):
            pass

    module_coords_dir = output_dir / "dungeon_modules_coords"
    if module_coords_dir.exists():
        for fpath in module_coords_dir.glob("*.json"):
            try:
                with open(fpath, encoding="utf-8") as f:
                    _collect_keys(json.load(f), used)
            except (json.JSONDecodeError, OSError):
                continue

    quest_npc_path = output_dir / "quest_npc.json"
    if quest_npc_path.exists():
        try:
            with open(quest_npc_path, encoding="utf-8") as f:
                _collect_keys(json.load(f), used)
        except (json.JSONDecodeError, OSError):
            pass

    return used


def build_locale_files(db, output_dir: Path, lootdrop_keys: set[str] | None = None) -> list[str]:
    """Export DB translation tables filtered to used keys only."""
    locale_dir = output_dir / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)

    used_keys = _load_used_keys(output_dir, lootdrop_keys)
    used_keys.add(SUPERHOARD_I18N_KEY)
    used_keys.update(FILTER_MODE_LOCALE_KEYS)
    fallback_translations = db.get_translations_map("zh-Hans")

    exported: list[str] = []
    for lang in SUPPORTED_LANGUAGES:
        all_translations = db.get_translations_map(lang)
        if not all_translations:
            raise RuntimeError(f"empty translation table for {lang}")
        if used_keys:
            filtered = {key: all_translations.get(key, fallback_translations.get(key, key)) for key in used_keys}
        else:
            filtered = dict(all_translations)
        # Inject SuperHoard synthetic key (no Game.json entry)
        sh_val = SUPERHOARD_I18N.get(lang) or SUPERHOARD_I18N.get("zh-Hans")
        if sh_val:
            filtered[SUPERHOARD_I18N_KEY] = sh_val
        filtered.update(hardcoded_locale_entries(lang, used_keys))
        dest = locale_dir / f"{lang}.json"
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
