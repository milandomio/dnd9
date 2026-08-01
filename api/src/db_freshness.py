"""Database freshness and source availability checks.

This module only reads source metadata. Game JSON content remains restricted to
the importer phase.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from config import DATA_DIR, DB_PATH, LOCALIZATION_ROOT, MAPS_DIR

FRESHNESS_SCHEMA_VERSION = "1"
GENERATOR_VERSION = "db-lifecycle-v2-item-type-grouping"

SOURCE_ROOTS: dict[str, Path] = {
    "localization": LOCALIZATION_ROOT,
    "generated_data": DATA_DIR,
    "maps": MAPS_DIR,
}

REQUIRED_TABLES = frozenset(
    {
        "item_entities",
        "monster_entities",
        "props_entities",
        "dungeon_modules",
        "spawners",
        "spawner_entries",
        "lootdrop_groups",
        "lootdrop_rate_items",
        "lootdrop_rate_weights",
        "translations",
    }
)

CORE_TABLES = (
    "item_entities",
    "monster_entities",
    "props_entities",
    "dungeon_modules",
)


@dataclass(frozen=True)
class DatabaseDecision:
    state: str
    source_available: bool
    manifest: dict | None
    reason: str

    @property
    def import_required(self) -> bool:
        return self.state == "REBUILD_REQUIRED"


def build_source_manifest(source_roots: dict[str, Path] | None = None) -> tuple[dict | None, str]:
    """Build a metadata-only manifest and reject incomplete source trees."""
    roots = source_roots or SOURCE_ROOTS
    missing = [name for name, root in roots.items() if not root.is_dir()]
    if missing:
        return None, "missing source roots: " + ", ".join(sorted(missing))

    source_stats: dict[str, dict[str, int]] = {}
    fingerprint_parts: list[str] = []
    latest_mtime_ns = 0
    for name, root in sorted(roots.items()):
        file_count = 0
        total_size = 0
        source_latest_mtime_ns = 0
        files = sorted(path for path in root.rglob("*") if path.is_file())
        for path in files:
            try:
                stat = path.stat()
            except OSError as exc:
                return None, f"cannot stat source file {path}: {exc}"
            relative = path.relative_to(root).as_posix()
            fingerprint_parts.append(f"{name}\0{relative}\0{stat.st_size}\0{stat.st_mtime_ns}\n")
            file_count += 1
            total_size += stat.st_size
            source_latest_mtime_ns = max(source_latest_mtime_ns, stat.st_mtime_ns)
        source_stats[name] = {
            "file_count": file_count,
            "total_size": total_size,
            "max_mtime_ns": source_latest_mtime_ns,
        }
        latest_mtime_ns = max(latest_mtime_ns, source_latest_mtime_ns)

    digest = hashlib.sha256("".join(fingerprint_parts).encode("utf-8")).hexdigest()
    return {
        "schema_version": FRESHNESS_SCHEMA_VERSION,
        "generator_version": GENERATOR_VERSION,
        "latest_mtime_ns": latest_mtime_ns,
        "sources": source_stats,
        "digest": digest,
    }, "source metadata ready"


def _read_pipeline_meta(db_path: Path) -> dict[str, str]:
    """Read metadata without creating or modifying the database."""
    if not db_path.is_file():
        return {}
    uri = f"file:{db_path.resolve()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            rows = conn.execute("SELECT key, value FROM pipeline_meta").fetchall()
    except (sqlite3.DatabaseError, OSError):
        return {}
    return {key: value for key, value in rows}


def has_usable_database(db_path: Path) -> bool:
    """Verify required tables and core exported entities without modifying the DB."""
    if not db_path.is_file():
        return False
    uri = f"file:{db_path.resolve()}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}
            if not REQUIRED_TABLES.issubset(tables):
                return False
            for table in CORE_TABLES:
                if conn.execute(f"SELECT 1 FROM {table} LIMIT 1").fetchone() is None:
                    return False
    except (sqlite3.DatabaseError, OSError):
        return False
    return True


def _is_complete_db(db_path: Path) -> bool:
    meta = _read_pipeline_meta(db_path)
    if not has_usable_database(db_path):
        return False
    # Legacy DBs do not contain pipeline_meta. They are rebuilt when sources are
    # available because their manifest is absent, but remain usable DB-only data
    # when the source tree is unavailable.
    return not meta or meta.get("import_complete") == "1"


def inspect_database(
    db_path: Path = DB_PATH,
    source_roots: dict[str, Path] | None = None,
    force_rebuild: bool = False,
) -> DatabaseDecision:
    """Decide whether to use an existing DB or build a replacement.

    No SQLite connection is opened for a missing DB, and this function never
    deletes or mutates the formal DB path.
    """
    manifest, source_reason = build_source_manifest(source_roots)
    db_exists = db_path.is_file()
    db_complete = _is_complete_db(db_path) if db_exists else False

    if manifest is None:
        if force_rebuild:
            return DatabaseDecision("FAIL_FAST", False, None, source_reason + "; forced rebuild requires sources")
        if db_complete:
            return DatabaseDecision("DB_ONLY", False, None, source_reason)
        return DatabaseDecision("FAIL_FAST", False, None, source_reason)

    if force_rebuild:
        return DatabaseDecision("REBUILD_REQUIRED", True, manifest, "forced rebuild")
    if not db_exists:
        return DatabaseDecision("REBUILD_REQUIRED", True, manifest, "DB missing")
    if not db_complete:
        return DatabaseDecision("REBUILD_REQUIRED", True, manifest, "DB incomplete or legacy")

    meta = _read_pipeline_meta(db_path)
    stored_manifest = meta.get("source_manifest", "")
    try:
        stored = json.loads(stored_manifest) if stored_manifest else None
    except json.JSONDecodeError:
        stored = None
    if stored != manifest:
        return DatabaseDecision("REBUILD_REQUIRED", True, manifest, "source manifest changed")
    if db_path.stat().st_mtime_ns < manifest["latest_mtime_ns"]:
        return DatabaseDecision("REBUILD_REQUIRED", True, manifest, "DB mtime older than source")
    return DatabaseDecision("DB_READY", True, manifest, "DB and source manifest are current")
