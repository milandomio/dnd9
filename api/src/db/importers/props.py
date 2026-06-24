from config import PROPS_DIR

from .._helpers import extract_props_name, load_json_dir


class PropsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM props_entities")
        files = load_json_dir(PROPS_DIR)
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            asset_name = extract_props_name(raw_name)
            rows.append((asset_name, raw_name, name_key))
        c.executemany(
            "INSERT OR REPLACE INTO props_entities (asset_name, raw_name, translation_key) VALUES (?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)
