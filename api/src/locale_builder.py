"""Locale dictionary export for frontend i18n."""

import json
from pathlib import Path

from config import SUPERHOARD_I18N, SUPERHOARD_I18N_KEY
from db._helpers import discover_languages

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
        tk = obj.get("translation_key")
        if tk and isinstance(tk, str):
            used.add(tk)
        for v in obj.values():
            _collect_keys(v, used)
    elif isinstance(obj, list):
        for item in obj:
            _collect_keys(item, used)


def _load_used_keys(output_dir: Path) -> set[str]:
    """Load all translation_keys actually used in search_index + entity data files."""
    used: set[str] = set()

    si_path = output_dir / "search_index.json"
    if si_path.exists():
        with open(si_path, encoding="utf-8") as f:
            idx = json.load(f)
        for entry in idx:
            tk = entry.get("translation_key")
            if tk:
                used.add(tk)

    for subdir in ("items", "monsters", "props", "lootdrops"):
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

    return used


def build_locale_files(db, output_dir: Path) -> list[str]:
    """Export DB translation tables filtered to used keys only."""
    locale_dir = output_dir / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)

    used_keys = _load_used_keys(output_dir)
    used_keys.add(SUPERHOARD_I18N_KEY)
    used_keys.update(FILTER_MODE_LOCALE_KEYS)

    exported: list[str] = []
    for lang in discover_languages():
        all_translations = db.get_translations_map(lang)
        if not all_translations:
            continue
        if used_keys:
            filtered = {k: v for k, v in all_translations.items() if k in used_keys}
        else:
            filtered = dict(all_translations)
        # Inject SuperHoard synthetic key (no Game.json entry)
        sh_val = SUPERHOARD_I18N.get(lang) or SUPERHOARD_I18N.get("zh-Hans")
        if sh_val:
            filtered[SUPERHOARD_I18N_KEY] = sh_val
        dest = locale_dir / f"{lang}.json"
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
