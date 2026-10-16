from config import PROPS_DIR, TRANSLATION_KEY_ALIAS_MAP

from .._helpers import extract_props_name, load_json_dir


class PropsImporter:
    def __init__(self, conn):
        self.conn = conn

    def import_all(self) -> int:
        c = self.conn.cursor()
        c.execute("DELETE FROM props_entities")
        c.execute("DELETE FROM props_tag_index")
        files = load_json_dir(PROPS_DIR)
        rows = []
        tag_rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            entry = data_list[0]
            props = entry.get("Properties", {}) or {}
            name = props.get("Name") or {}
            name_key = name.get("Key", "")
            name_key = TRANSLATION_KEY_ALIAS_MAP.get(name_key, name_key)
            asset_name = extract_props_name(raw_name)
            rows.append((asset_name, raw_name, name_key))
            for data in data_list:
                properties = data.get("Properties", {}) or {}
                tag_name = (properties.get("IdTag") or {}).get("TagName", "")
                if tag_name:
                    tag_name_key = (properties.get("Name") or {}).get("Key", "")
                    tag_name_key = TRANSLATION_KEY_ALIAS_MAP.get(tag_name_key, tag_name_key)
                    tag_rows.append(
                        (
                            tag_name,
                            tag_name_key,
                            (properties.get("Name") or {}).get("LocalizedString", ""),
                        )
                    )
        c.executemany(
            "INSERT OR REPLACE INTO props_entities (asset_name, raw_name, translation_key) VALUES (?, ?, ?)",
            rows,
        )
        c.executemany(
            "INSERT OR REPLACE INTO props_tag_index (tag_name, translation_key, source_string) VALUES (?, ?, ?)",
            tag_rows,
        )
        self.conn.commit()
        return len(rows)

    def import_environment_lights(self) -> int:
        """Persist light-emitting props (those that carry FuelSeconds).

        Props expose a burn window via ``FuelSeconds`` / ``FuelSecondsMax`` but no
        ``LightAreaRadius``, so they cannot share the item ``light_items`` table.
        They back the 【灯】 page's "环境" tab (braziers, wall lamps, candles, ...).
        """
        c = self.conn.cursor()
        c.execute("DELETE FROM environment_lights")
        files = load_json_dir(PROPS_DIR)
        rows = []
        for raw_name, data_list in files.items():
            if not data_list:
                continue
            properties = data_list[0].get("Properties", {}) or {}
            fuel = properties.get("FuelSeconds")
            if not isinstance(fuel, (int, float)) or fuel <= 0:
                continue
            name = properties.get("Name") or {}
            name_key = TRANSLATION_KEY_ALIAS_MAP.get(name.get("Key", ""), name.get("Key", ""))
            fuel_max = properties.get("FuelSecondsMax")
            if not isinstance(fuel_max, (int, float)):
                fuel_max = fuel
            rows.append(
                (
                    raw_name,
                    name.get("LocalizedString", "") or extract_props_name(raw_name),
                    name_key,
                    float(fuel),
                    float(fuel_max),
                    1 if properties.get("FuelBurnsOnlyInSwarm") else 0,
                )
            )
        c.executemany(
            "INSERT OR REPLACE INTO environment_lights "
            "(raw_name, item_name, translation_key, fuel_seconds, fuel_seconds_max, only_in_swarm) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            rows,
        )
        self.conn.commit()
        return len(rows)
