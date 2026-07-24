"""Locale dictionary export for frontend i18n."""

import json
from pathlib import Path

from db._helpers import discover_languages


def build_locale_files(db, output_dir: Path) -> list[str]:
    """Export DB translation tables to data/json/locale/{lang}.json."""
    locale_dir = output_dir / "locale"
    locale_dir.mkdir(parents=True, exist_ok=True)

    exported: list[str] = []
    for lang in discover_languages():
        translations = db.get_translations_map(lang)
        if not translations:
            continue
        dest = locale_dir / f"{lang}.json"
        with open(dest, "w", encoding="utf-8") as f:
            json.dump(translations, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
