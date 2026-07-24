"""Locale dictionary export for frontend i18n."""

import json
from pathlib import Path

from db._helpers import discover_languages


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
            tk = data.get("translation_key") if isinstance(data, dict) else None
            if tk:
                used.add(tk)
            monsters = data.get("monsters") if isinstance(data, dict) else None
            if monsters and isinstance(monsters, list):
                for m in monsters:
                    mtk = m.get("translation_key") if isinstance(m, dict) else None
                    if mtk:
                        used.add(mtk)
            gdi = data.get("group_drop_info") if isinstance(data, dict) else None
            if gdi and isinstance(gdi, dict):
                for entries in gdi.values():
                    if isinstance(entries, list):
                        for e in entries:
                            etk = e.get("translation_key") if isinstance(e, dict) else None
                            if etk:
                                used.add(etk)

    return used


def build_locale_files(db, output_dir: Path) -> list[str]:
    """Export DB translation tables filtered to used keys only."""
    locale_dir = output_dir / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)

    used_keys = _load_used_keys(output_dir)

    exported: list[str] = []
    for lang in discover_languages():
        all_translations = db.get_translations_map(lang)
        if not all_translations:
            continue
        if used_keys:
            filtered = {k: v for k, v in all_translations.items() if k in used_keys}
        else:
            filtered = dict(all_translations)
        dest = locale_dir / f"{lang}.json"
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(filtered, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
