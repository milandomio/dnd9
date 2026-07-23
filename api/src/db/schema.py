import sqlite3


class SchemaManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def create_tables(self):
        c = self.conn.cursor()
        c.executescript("""
            CREATE TABLE IF NOT EXISTS item_entities (
                item_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT '',
                variant_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS monster_entities (
                monster_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS props_entities (
                asset_name TEXT PRIMARY KEY,
                raw_name TEXT NOT NULL,
                translation_key TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS dungeon_modules (
                module_name TEXT PRIMARY KEY,
                translation_key TEXT NOT NULL DEFAULT '',
                module_group TEXT NOT NULL DEFAULT '',
                size_x INTEGER DEFAULT 1,
                size_y INTEGER DEFAULT 1,
                sl_base_name TEXT NOT NULL DEFAULT '',
                map_image_name TEXT NOT NULL DEFAULT '',
                aliases TEXT NOT NULL DEFAULT '[]',
                rotation REAL DEFAULT 270
            );

            CREATE TABLE IF NOT EXISTS lootdrop_items (
                item_name TEXT NOT NULL,
                monster_name TEXT NOT NULL,
                lootdrop_name TEXT NOT NULL DEFAULT '',
                PRIMARY KEY (item_name, monster_name)
            );

            CREATE TABLE IF NOT EXISTS spawners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                keyword TEXT NOT NULL,
                original_keyword TEXT NOT NULL DEFAULT '',
                spawner_type TEXT NOT NULL DEFAULT 'unknown',
                has_lootdrop INTEGER NOT NULL DEFAULT 0,
                x REAL NOT NULL,
                y REAL NOT NULL,
                z REAL NOT NULL,
                yaw REAL NOT NULL DEFAULT 0.0,
                json_filename TEXT NOT NULL,
                module_type TEXT DEFAULT '',
                version TEXT NOT NULL DEFAULT '',
                map_base TEXT NOT NULL DEFAULT '',
                group_parent TEXT NOT NULL DEFAULT ''
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS items_fts USING fts5(
                item_name, translation_key, category,
                content='item_entities',
                content_rowid='rowid',
                tokenize='unicode61'
            );

            CREATE VIRTUAL TABLE IF NOT EXISTS monsters_fts USING fts5(
                monster_name, translation_key,
                content='monster_entities',
                content_rowid='rowid',
                tokenize='unicode61'
            );

            CREATE TABLE IF NOT EXISTS translations (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS quest_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_name TEXT NOT NULL,
                item_translation TEXT NOT NULL DEFAULT '',
                npc_name TEXT NOT NULL,
                npc_name_cn TEXT NOT NULL DEFAULT '',
                quest_number INTEGER NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 1,
                rarity TEXT NOT NULL DEFAULT '',
                is_loot TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS quest_npcs (
                npc_name TEXT PRIMARY KEY,
                npc_name_display TEXT NOT NULL DEFAULT '',
                quest_count INTEGER NOT NULL DEFAULT 0,
                category TEXT NOT NULL DEFAULT '',
                quests_json TEXT NOT NULL DEFAULT '[]'
            );

            CREATE TABLE IF NOT EXISTS explore_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL DEFAULT '',
                module_name TEXT NOT NULL DEFAULT '',
                quest_id TEXT NOT NULL DEFAULT '',
                quest_title TEXT NOT NULL DEFAULT '',
                quest_number INTEGER NOT NULL DEFAULT 0,
                npc_name TEXT NOT NULL DEFAULT '',
                npc_name_display TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS spawner_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                spawner_keyword TEXT NOT NULL,
                entity_name TEXT NOT NULL DEFAULT '',
                spawn_rate REAL NOT NULL DEFAULT 100.0,
                dungeon_grades TEXT NOT NULL DEFAULT '[]',
                lootdrop_group_id TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS lootdrop_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id TEXT NOT NULL,
                dungeon_grade INTEGER NOT NULL DEFAULT 0,
                lootdrop_id TEXT NOT NULL DEFAULT '',
                lootdrop_rate_id TEXT NOT NULL DEFAULT '',
                drop_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS lootdrop_rate_items (
                lootdrop_id TEXT NOT NULL,
                item_name TEXT NOT NULL,
                luck_grade INTEGER NOT NULL DEFAULT 0,
                drop_count INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS lootdrop_rate_weights (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                rate_id TEXT NOT NULL,
                luck_grade INTEGER NOT NULL DEFAULT 0,
                weight INTEGER NOT NULL DEFAULT 0
            );
            CREATE INDEX IF NOT EXISTS idx_lrw_rate_grade ON lootdrop_rate_weights (rate_id, luck_grade);

            CREATE TABLE IF NOT EXISTS mutually_exclusive_groups (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                map_base TEXT NOT NULL,
                json_filename TEXT NOT NULL,
                group_name TEXT NOT NULL,
                search_term TEXT NOT NULL DEFAULT '',
                spawner_count INTEGER NOT NULL DEFAULT 0
            );
        """)
        self._migrate_spawners_table()
        self.conn.commit()

    def _migrate_spawners_table(self):
        c = self.conn.cursor()
        c.execute("PRAGMA table_info(spawners)")
        columns = [row[1] for row in c.fetchall()]
        if "has_lootdrop" not in columns:
            c.execute("ALTER TABLE spawners ADD COLUMN has_lootdrop INTEGER NOT NULL DEFAULT 0")
        if "group_parent" not in columns:
            c.execute("ALTER TABLE spawners ADD COLUMN group_parent TEXT NOT NULL DEFAULT ''")
        if "sub_group_parent" not in columns:
            c.execute("ALTER TABLE spawners ADD COLUMN sub_group_parent TEXT NOT NULL DEFAULT ''")
