import json
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from enrichment import enrich_all_entities  # noqa: E402


class EnrichmentInMemoryTest(unittest.TestCase):
    def test_uses_in_memory_lootdrop_group_info_and_writes_entity_once(self):
        drop_engine = SimpleNamespace(
            spawner_ldg={},
            ore_ldg={},
            map_base_to_group={},
            spawn_rate_cache={},
            spawn_rate_detail={},
            entity_spawners={},
        )
        group_drop_info = {
            "Crypt": [
                {
                    "translation": "Bandage",
                    "translation_key": "Text_DesignData_Item_Item_Bandage",
                    "spawn_rate": 100,
                    "drop_rates": {"PVE": 10.0},
                }
            ]
        }
        entity_data_by_type = {
            "items": {
                "Bandage": {
                    "name": "Bandage",
                    "translation": "Bandage",
                    "translation_key": "Text_DesignData_Item_Item_Bandage",
                    "coords": [],
                }
            },
            "monsters": {},
            "props": {},
        }

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            enrich_all_entities(
                drop_engine,
                [{"name": "Bandage"}],
                entity_data_by_type,
                {"Bandage": group_drop_info},
                output_dir,
            )

            output_path = output_dir / "items" / "Bandage.json"
            self.assertTrue(output_path.exists())
            self.assertFalse((output_dir / "lootdrops" / "Bandage.json").exists())
            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8"))["group_drop_info"], group_drop_info)


if __name__ == "__main__":
    unittest.main()
