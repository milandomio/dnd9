"""Localized search index export for frontend search."""

import json
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
    fallback_translations = db.get_translations_map("zh-Hans")
    exported: list[str] = []
    for lang in SUPPORTED_LANGUAGES:
        translations = db.get_translations_map(lang)
        if not translations:
            raise RuntimeError(f"empty translation table for {lang}")
        localized_index = []
        for entry in base_index:
            localized = dict(entry)
            translation_key = entry.get("translation_key", "")
            localized["translation"] = translations.get(
                translation_key, fallback_translations.get(translation_key, entry.get("translation", ""))
            )
            tag_key = entry.get("tag_translation_key", "")
            if tag_key:
                localized["tag"] = translations.get(tag_key, fallback_translations.get(tag_key, entry.get("tag", "")))
            monster_keys = entry.get("monster_translation_keys") or []
            if monster_keys:
                monster_fallbacks = entry.get("monster_translations") or []
                localized["monster_translations"] = [
                    translations.get(
                        key,
                        fallback_translations.get(
                            key, monster_fallbacks[index] if index < len(monster_fallbacks) else ""
                        ),
                    )
                    for index, key in enumerate(monster_keys)
                ]
            localized_index.append(localized)
        with open(search_dir / f"{lang}.json", "w", encoding="utf-8") as f:
            json.dump(localized_index, f, ensure_ascii=False, separators=(",", ":"))
        exported.append(lang)
    return exported
