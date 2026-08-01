import json
import os
import sqlite3
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import main as pipeline_main  # noqa: E402
from db import DatabaseManager  # noqa: E402
from db_freshness import REQUIRED_TABLES, DatabaseDecision, build_source_manifest, inspect_database  # noqa: E402

CORE_TABLES = ("item_entities", "monster_entities", "props_entities", "dungeon_modules")


def _write_complete_db(db_path: Path, manifest: dict | None = None) -> None:
    with sqlite3.connect(db_path) as conn:
        for table in REQUIRED_TABLES:
            conn.execute(f"CREATE TABLE {table} (value TEXT)")
        for table in CORE_TABLES:
            conn.execute(f"INSERT INTO {table} VALUES ('ready')")
        if manifest is not None:
            conn.execute("CREATE TABLE pipeline_meta (key TEXT PRIMARY KEY, value TEXT)")
            conn.executemany(
                "INSERT INTO pipeline_meta VALUES (?, ?)",
                (
                    ("import_complete", "1"),
                    ("source_manifest", json.dumps(manifest, sort_keys=True, separators=(",", ":"))),
                ),
            )


class DatabaseFreshnessTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name)
        self.roots = {name: self.root / name for name in ("localization", "generated_data", "maps")}
        for root in self.roots.values():
            root.mkdir()
            (root / "source.json").write_text("{}", encoding="utf-8")
        self.db_path = self.root / "darkfindv5.db"

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_missing_db_requires_rebuild(self):
        decision = inspect_database(self.db_path, self.roots)
        self.assertEqual(decision.state, "REBUILD_REQUIRED")
        self.assertFalse(self.db_path.exists())

    def test_matching_manifest_is_ready(self):
        manifest, _ = build_source_manifest(self.roots)
        self.assertIsNotNone(manifest)
        _write_complete_db(self.db_path, manifest)

        self.assertEqual(inspect_database(self.db_path, self.roots).state, "DB_READY")

    def test_source_change_requires_rebuild(self):
        manifest, _ = build_source_manifest(self.roots)
        self.assertIsNotNone(manifest)
        _write_complete_db(self.db_path, manifest)
        source = self.roots["maps"] / "source.json"
        source.write_text('{"changed":true}', encoding="utf-8")
        os.utime(source, None)

        self.assertEqual(inspect_database(self.db_path, self.roots).state, "REBUILD_REQUIRED")

    def test_missing_source_reuses_valid_legacy_db_without_mutating_it(self):
        _write_complete_db(self.db_path)
        before = self.db_path.stat()
        for root in self.roots.values():
            for source in root.iterdir():
                source.unlink()
            root.rmdir()

        decision = inspect_database(self.db_path, self.roots)
        after = self.db_path.stat()
        self.assertEqual(decision.state, "DB_ONLY")
        self.assertEqual(
            (before.st_ino, before.st_size, before.st_mtime_ns), (after.st_ino, after.st_size, after.st_mtime_ns)
        )

    def test_missing_source_and_invalid_db_fails_without_creating_a_db(self):
        for root in self.roots.values():
            for source in root.iterdir():
                source.unlink()
            root.rmdir()

        decision = inspect_database(self.db_path, self.roots)
        self.assertEqual(decision.state, "FAIL_FAST")
        self.assertFalse(self.db_path.exists())

    def test_forced_rebuild_requires_available_source(self):
        _write_complete_db(self.db_path)
        for root in self.roots.values():
            for source in root.iterdir():
                source.unlink()
            root.rmdir()

        decision = inspect_database(self.db_path, self.roots, force_rebuild=True)
        self.assertEqual(decision.state, "FAIL_FAST")
        self.assertIn("forced rebuild requires sources", decision.reason)

    def test_metadata_only_db_is_not_usable(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE pipeline_meta (key TEXT PRIMARY KEY, value TEXT)")
            conn.execute("INSERT INTO pipeline_meta VALUES ('import_complete', '1')")

        self.assertEqual(inspect_database(self.db_path, self.roots).state, "REBUILD_REQUIRED")

    def test_db_only_manager_does_not_add_schema_to_legacy_database(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("CREATE TABLE legacy_data (value TEXT)")

        with DatabaseManager(self.db_path, initialize_schema=False):
            pass

        with sqlite3.connect(self.db_path) as conn:
            tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'")}
        self.assertEqual(tables, {"legacy_data"})


class AtomicDatabaseReplacementTest(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = Path(self.temp_dir.name) / "darkfindv5.db"
        self.db_path.write_text("old", encoding="utf-8")

    def tearDown(self):
        self.temp_dir.cleanup()

    def _run_main(self, decision: DatabaseDecision, run_side_effect):
        from unittest.mock import patch

        with ExitStack() as stack:
            stack.enter_context(patch.object(pipeline_main, "DB_PATH", self.db_path))
            stack.enter_context(
                patch.object(pipeline_main, "_parse_args", return_value=type("Args", (), {"rebuild_db": False})())
            )
            stack.enter_context(patch.object(pipeline_main, "inspect_database", return_value=decision))
            stack.enter_context(patch.object(pipeline_main, "_pre_cleanup"))
            stack.enter_context(patch.object(pipeline_main, "_deliver"))
            stack.enter_context(patch.object(pipeline_main, "_validate_images"))
            stack.enter_context(patch.object(pipeline_main, "_cleanup_old_logs"))
            run_mock = stack.enter_context(patch.object(pipeline_main, "run", side_effect=run_side_effect))
            pipeline_main.main()
            return run_mock

    def test_successful_full_import_replaces_db_atomically(self):
        decision = DatabaseDecision("REBUILD_REQUIRED", True, {"digest": "new"}, "stale")

        def fake_run(**kwargs):
            kwargs["db_path"].write_text("new", encoding="utf-8")
            return None

        run_mock = self._run_main(decision, fake_run)
        self.assertEqual(self.db_path.read_text(encoding="utf-8"), "new")
        self.assertFalse(self.db_path.with_name("darkfindv5.db.building").exists())
        self.assertEqual(run_mock.call_args.kwargs["import_required"], True)

    def test_failed_full_import_preserves_existing_db_and_removes_building_file(self):
        decision = DatabaseDecision("REBUILD_REQUIRED", True, {"digest": "new"}, "stale")

        def fake_run(**kwargs):
            kwargs["db_path"].write_text("partial", encoding="utf-8")
            raise RuntimeError("import failed")

        with self.assertRaisesRegex(RuntimeError, "import failed"):
            self._run_main(decision, fake_run)
        self.assertEqual(self.db_path.read_text(encoding="utf-8"), "old")
        self.assertFalse(self.db_path.with_name("darkfindv5.db.building").exists())


if __name__ == "__main__":
    unittest.main()
