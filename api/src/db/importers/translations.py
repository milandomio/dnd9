import json
import logging
import re
from pathlib import Path

from config import GAME_JSON, LOCALIZATION_ROOT

log = logging.getLogger(__name__)
_CRACKED_RE = re.compile(r"（裂开）")


class TranslationsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        data = self._load_game_json(GAME_JSON)
        if not data:
            return 0

        c = self.conn.cursor()
        c.execute("DELETE FROM translations")
        rows = [(key, _CRACKED_RE.sub("", value)) for key, value in data.items() if key and value]
        c.executemany("INSERT OR REPLACE INTO translations (key, value) VALUES (?, ?)", rows)
        total = len(rows)

        for lang in self._discover_languages():
            if lang == "zh-Hans":
                continue
            lang_data = self._load_game_json(LOCALIZATION_ROOT / lang / "Game.json")
            if not lang_data:
                continue
            table_name = self._ensure_translation_table(lang)
            c.execute(f"DELETE FROM {table_name}")
            lang_rows = [(key, value) for key, value in lang_data.items() if key and value]
            c.executemany(f"INSERT OR REPLACE INTO {table_name} (key, value) VALUES (?, ?)", lang_rows)
            total += len(lang_rows)

        self.conn.commit()
        return total

    def _ensure_translation_table(self, lang: str) -> str:
        table_name = f"translations_{lang.replace('-', '_')}"
        c = self.conn.cursor()
        c.execute(f"""
            CREATE TABLE IF NOT EXISTS {table_name} (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            )
            """)
        return table_name

    @staticmethod
    def _load_game_json(path: Path) -> dict[str, str]:
        if not path.exists():
            return {}
        try:
            with open(path, encoding="utf-8") as f:
                raw = json.load(f)
            if not isinstance(raw, dict):
                return {}
            if isinstance(raw.get("DC"), dict):
                return raw["DC"]
            for value in raw.values():
                if isinstance(value, dict):
                    return value
        except Exception as exc:
            log.warning("failed to load game JSON %s: %s", path, exc)
        return {}

    @staticmethod
    def _discover_languages() -> list[str]:
        if not LOCALIZATION_ROOT.exists():
            return []
        return sorted(
            path.name for path in LOCALIZATION_ROOT.iterdir() if path.is_dir() and (path / "Game.json").exists()
        )
