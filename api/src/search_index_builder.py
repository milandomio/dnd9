"""Localized search index export for frontend search."""

import json
import sqlite3
from pathlib import Path

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


def build_search_index_files(db, output_dir: Path) -> list[str]:
    """Export one search index per language using each entry's translation key."""
    source = output_dir / "search_index.json"
    if not source.exists():
        return []

    with open(source, encoding="utf-8") as f:
        base_index = json.load(f)

    search_dir = output_dir / "search_index"
    search_dir.mkdir(parents=True, exist_ok=True)
    exported: list[str] = []
    for lang in SUPPORTED_LANGUAGES:
        try:
            translations = db.get_translations_map(lang)
        except sqlite3.OperationalError:
            continue
        localized_index = [
            {
                **entry,
                "translation": translations.get(entry.get("translation_key", ""), entry.get("translation", "")),
            }
            for entry in base_index
        ]
        with open(search_dir / f"{lang}.json", "w", encoding="utf-8") as f:
            json.dump(localized_index, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
