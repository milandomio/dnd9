from collections import Counter

from config import ITEM_DIR

from .._helpers import extract_item_name, load_json_dir


class ItemsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM item_entities")
        files = load_json_dir(ITEM_DIR)
        variant_counts: Counter = Counter()
        seen: set[str] = set()
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = ""
            if "Name" in props:
                name_key = (props["Name"] or {}).get("Key", "")
            item_name = extract_item_name(raw_name)
            variant_counts[item_name] += 1
            if item_name not in seen:
                seen.add(item_name)
                rows.append((item_name, raw_name, name_key, ""))
        deduped = [r + (variant_counts.get(r[0], 1),) for r in rows]
        c.executemany(
            "INSERT OR REPLACE INTO item_entities (item_name, raw_name, translation_key, category, variant_count) VALUES (?, ?, ?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("items_fts")
        self.conn.commit()
        return len(deduped)

    def _rebuild_fts(self, fts_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()
