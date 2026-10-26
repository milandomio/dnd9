import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from lootdrop_builder import build_and_save_lootdrop_details  # noqa: E402


def _coord(keyword: str, *, x: float, map_base: str = "Crypt_AltarRoomAB") -> dict:
    return {
        "keyword": keyword,
        "original_keyword": keyword,
        "x": x,
        "y": 0.0,
        "z": 0.0,
        "yaw": 0.0,
        "json_filename": f"{map_base}_D",
        "version": "1",
        "map_base": map_base,
        "spawner_type": "monster",
        "group_parent": "",
        "sub_group_parent": "",
        "is_container": 0,
    }


def _entry(name: str, monsters: list[str], translation: str) -> dict:
    return {
        "name": name,
        "translation": translation,
        "translation_key": f"Text_DesignData_Item_Item_{name}",
        "variant_count": 1,
        "raw_name": f"Id_Item_{name}_5001",
        "monsters": monsters,
        "monster_translations": [translation for _ in monsters],
        "monster_translation_keys": [f"Text_DesignData_Monster_Monster_{m}" for m in monsters],
    }


class _FakeDropEngine:
    """Minimal stand-in exposing only what the detail builder reads."""

    def __init__(self) -> None:
        self.map_base_to_group = {"Crypt_AltarRoomAB": "Crypt"}
        self.spawn_rate_cache = {"FrostImp": 100.0}
        self.spawn_rate_detail = {}
        self.spawn_rate_by_mode = {}
        self.entity_spawners = {}

    def get_existing_variant_suffixes(self, base_name: str) -> set[str]:
        return {"5001"}

    def get_group_drop_rates(self, item_name, entity_name, group, profile=None):
        return {"PVE": 10.0, "普通": 10.0, "豪客赛": 100.0}

    def get_variant_group_drop_rates(self, luck_grade, entity_name, group, item_name=""):
        return {}

    def get_combined_spawn_rate(self, entity_name: str) -> float:
        return 100.0


def _build(loot_index: list[dict], all_coords: dict, output_dir: Path) -> list[dict]:
    build_and_save_lootdrop_details(
        loot_index,
        _FakeDropEngine(),
        all_coords,
        lambda name, key, kind: key or name,
        {},
        {},
        {},
        [],
        output_dir,
        translations={},
        entity_page_map=None,
    )
    return json.loads((output_dir / "lootdrops.json").read_text(encoding="utf-8"))


class LootdropIndexPublishTest(unittest.TestCase):
    def test_index_drops_entries_without_detail_files(self):
        loot_index = [
            _entry("Bandage", ["FrostImp"], "绷带"),
            _entry("TidestoneOres", ["Ore_TidestoneOre_High"], "潮汐石矿"),
        ]
        # Only FrostImp resolves to a coordinate; the ore keyword lives in a
        # module outside the collected pool, so no detail file can be written.
        all_coords = {"FrostImp": [_coord("FrostImp", x=100.0)]}

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            saved = _build(loot_index, all_coords, output_dir)

            self.assertTrue((output_dir / "lootdrops" / "Bandage.json").is_file())
            self.assertFalse((output_dir / "lootdrops" / "TidestoneOres.json").exists())
            self.assertEqual([e["name"] for e in saved], ["Bandage"])
            # spawn_rate 100 × 豪客赛 drop 100% / 100
            self.assertEqual(saved[0]["max_score"], 100.0)

    def test_index_keeps_every_entry_that_produced_a_detail(self):
        loot_index = [
            _entry("Bandage", ["FrostImp"], "绷带"),
            _entry("Ale", ["FrostImp"], "麦酒"),
        ]
        all_coords = {"FrostImp": [_coord("FrostImp", x=100.0)]}

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            saved = _build(loot_index, all_coords, output_dir)

            self.assertEqual(sorted(e["name"] for e in saved), ["Ale", "Bandage"])
            self.assertTrue((output_dir / "lootdrops" / "Ale.json").is_file())


if __name__ == "__main__":
    unittest.main()
