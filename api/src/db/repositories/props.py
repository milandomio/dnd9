from typing import TypedDict

from config import TRANSLATION_KEY_ALIAS_MAP


class PropsEntity(TypedDict):
    asset_name: str
    translation_key: str


class PropsTagInfo(TypedDict):
    tag_name: str
    translation_key: str
    source_string: str


class PropsRepository:
    def __init__(self, conn):
        self.conn = conn

    def get_all(self) -> list[PropsEntity]:
        c = self.conn.cursor()
        c.execute("SELECT asset_name, translation_key FROM props_entities ORDER BY asset_name")
        results = [dict(r) for r in c.fetchall()]
        for result in results:
            result["translation_key"] = TRANSLATION_KEY_ALIAS_MAP.get(
                result["translation_key"], result["translation_key"]
            )
        return results

    def get_tag_info(self, tag_name: str) -> PropsTagInfo | None:
        c = self.conn.cursor()
        c.execute(
            "SELECT tag_name, translation_key, source_string FROM props_tag_index WHERE tag_name = ?",
            (tag_name,),
        )
        row = c.fetchone()
        if not row:
            return None
        result = dict(row)
        result["translation_key"] = TRANSLATION_KEY_ALIAS_MAP.get(result["translation_key"], result["translation_key"])
        return result
