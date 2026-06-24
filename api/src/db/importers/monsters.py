from config import MONSTER_DIR, SPAWNER_DIR

from .._helpers import MONSTER_SUBTYPE_RE, QUALITY_RE, extract_monster_name, load_json_dir


class MonstersImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM monster_entities")
        files = load_json_dir(MONSTER_DIR)
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            name_key = MONSTER_SUBTYPE_RE.sub("", name_key)
            monster_name = extract_monster_name(raw_name)
            rows.append((monster_name, raw_name, name_key))
        seen_lower: dict[str, int] = {}
        deduped = []
        for r in rows:
            key = r[0].lower()
            if key not in seen_lower:
                seen_lower[key] = len(deduped)
                deduped.append(r)
            else:
                idx = seen_lower[key]
                existing = deduped[idx]
                if r[2] and (
                    not existing[2]
                    or (r[2].startswith("Text_DesignData_") and not existing[2].startswith("Text_DesignData_"))
                ):
                    deduped[idx] = (existing[0], existing[1], r[2])
        spawner_files = load_json_dir(SPAWNER_DIR)
        for raw_name, data_list in spawner_files.items():
            if not data_list:
                continue
            raw = raw_name.removeprefix("Id_Spawner_Monster_")
            if raw.lower() not in seen_lower:
                seen_lower[raw.lower()] = len(deduped)
                entry = data_list[0]
                props = entry.get("Properties", {}) or {}
                name_key = (props.get("Name") or {}).get("Key", "")
                name_key = MONSTER_SUBTYPE_RE.sub("", name_key)
                deduped.append((raw, raw_name, name_key))
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            raw_stripped = raw_name.removeprefix("Id_Monster_")
            qm = QUALITY_RE.search(raw_stripped)
            if not qm:
                continue
            quality_name = raw_stripped
            base_name = QUALITY_RE.sub("", quality_name)
            if base_name == quality_name:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name_key = (props.get("Name") or {}).get("Key", "")
            name_key = MONSTER_SUBTYPE_RE.sub("", name_key)
            base_tk = next((dr[2] for dr in deduped if dr[0].lower() == base_name.lower()), "")
            if name_key and base_tk and name_key != base_tk:
                key = quality_name.lower()
                if key not in seen_lower:
                    seen_lower[key] = len(deduped)
                    deduped.append((quality_name, raw_name, name_key))
        c.executemany(
            "INSERT OR REPLACE INTO monster_entities (monster_name, raw_name, translation_key) VALUES (?, ?, ?)",
            deduped,
        )
        self._rebuild_fts("monsters_fts", "monster_entities")
        self.conn.commit()
        return len(deduped)

    def _rebuild_fts(self, fts_table: str, content_table: str):
        c = self.conn.cursor()
        c.execute(f"INSERT INTO {fts_table}({fts_table}) VALUES('rebuild')")
        self.conn.commit()
