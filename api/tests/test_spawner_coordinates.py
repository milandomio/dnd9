import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from db.importers.spawner_coordinates import extract_all_spawners, extract_spawners  # noqa: E402
from db.repositories.coordinates import CoordinatesRepository  # noqa: E402


def _object_path(index: int) -> str:
    return f"Maps/Test/Test_D.{index}"


def _outer(actor_name: str, index: int) -> dict:
    return {
        "ObjectName": f"BP_GameSpawner_C'Test_D:PersistentLevel.{actor_name}'",
        "ObjectPath": _object_path(index),
    }


def _spawner(actor_name: str, keyword: str, component_index: int) -> dict:
    return {
        "Type": "BP_GameSpawner_C",
        "Name": actor_name,
        "Properties": {
            "SpawnerDataAsset": {"ObjectName": f"DCSpawnerDataAsset'Id_Spawner_Monster_{keyword}'"},
            "PreviewData": {"AssetPathName": f"/Game/V2/Monster/Id_Monster_{keyword}.Id_Monster_{keyword}"},
            "RootComponent": {"ObjectPath": _object_path(component_index)},
        },
    }


class SpawnerCoordinatesTest(unittest.TestCase):
    def _fixture(self) -> list[dict | None]:
        data: list[dict | None] = [None] * 304
        data[46] = _spawner("BP_GameSpawner_C_46", "BlazeToad", 282)
        data[47] = _spawner("BP_GameSpawner_C_47", "FlameBeetle", 283)
        data[76] = {
            "Type": "BP_GameSpawnerGroup_C",
            "Name": "BP_GameSpawnerGroup_C_3",
        }
        data[79] = {
            "Type": "BP_SubGroup_C",
            "Name": "BP_SubGroup_C_1",
            "Properties": {"RootComponent": {"ObjectPath": _object_path(303)}},
        }
        data[241] = {
            "Type": "SceneComponent",
            "Name": "DefaultSceneRoot",
            "Outer": {
                "ObjectName": "BP_GameSpawnerGroup_C'Test_D:PersistentLevel.BP_GameSpawnerGroup_C_3'",
                "ObjectPath": _object_path(76),
            },
            "Properties": {"RelativeLocation": {"X": 100.0, "Y": 50.0, "Z": 10.0}},
        }
        data[282] = {
            "Type": "SphereComponent",
            "Name": "SceneComponent",
            "Outer": _outer("BP_GameSpawner_C_46", 46),
            "Properties": {
                "AttachParent": {"ObjectPath": _object_path(303)},
                "RelativeLocation": {"X": 10.0, "Y": 0.0, "Z": 2.0},
            },
        }
        data[283] = {
            "Type": "SphereComponent",
            "Name": "SceneComponent",
            "Outer": _outer("BP_GameSpawner_C_47", 47),
            "Properties": {
                "AttachParent": {"ObjectPath": _object_path(303)},
                "RelativeLocation": {"X": 0.0, "Y": 10.0, "Z": 2.0},
            },
        }
        data[303] = {
            "Type": "StaticMeshComponent",
            "Name": "StaticMeshComponent0",
            "Outer": {
                "ObjectName": "BP_SubGroup_C'Test_D:PersistentLevel.BP_SubGroup_C_1'",
                "ObjectPath": _object_path(79),
            },
            "Properties": {
                "AttachParent": {"ObjectPath": _object_path(241)},
                "RelativeLocation": {"X": 0.0, "Y": 20.0, "Z": 3.0},
                "RelativeRotation": {"Yaw": 90.0},
            },
        }
        return data

    def test_component_outer_fallback_preserves_group_and_subgroup_parents(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "Test_D.json"
            path.write_text(json.dumps(self._fixture()), encoding="utf-8")
            rows = extract_spawners(path, spawner_data_map={"BlazeToad": True, "FlameBeetle": True})

        by_keyword = {row["keyword"]: row for row in rows}
        blaze_toad = by_keyword["BlazeToad"]
        flame_beetle = by_keyword["FlameBeetle"]
        for row in (blaze_toad, flame_beetle):
            self.assertEqual(row["group_parent"], "BP_GameSpawnerGroup_C_3")
            self.assertEqual(row["sub_group_parent"], "BP_SubGroup_C_1")
        self.assertEqual(
            (blaze_toad["x"], blaze_toad["y"], blaze_toad["z"], blaze_toad["yaw"]),
            (100.0, 80.0, 15.0, 90.0),
        )
        self.assertEqual(
            (flame_beetle["x"], flame_beetle["y"], flame_beetle["z"], flame_beetle["yaw"]),
            (90.0, 70.0, 15.0, 90.0),
        )

        conn = sqlite3.connect(":memory:")
        conn.row_factory = sqlite3.Row
        conn.execute(
            "CREATE TABLE spawners (map_base TEXT, json_filename TEXT, group_parent TEXT, "
            "original_keyword TEXT, has_lootdrop INTEGER)"
        )
        conn.executemany(
            "INSERT INTO spawners VALUES (?, ?, ?, ?, ?)",
            [(row["map_base"], row["json_filename"], row["group_parent"], row["original_keyword"], 1) for row in rows],
        )
        variant_counts = CoordinatesRepository(conn).get_variant_counts()
        self.assertEqual(
            variant_counts[("Test", "Test_D.json", "BP_GameSpawnerGroup_C_3")],
            (2, ["BlazeToad", "FlameBeetle"]),
        )


def _row(keyword: str, x: float, y: float, z: float, map_base: str, *, hr: bool = False) -> dict:
    return {
        "keyword": keyword,
        "original_keyword": keyword,
        "spawner_type": "monster",
        "preview_name": keyword,
        "has_lootdrop": True,
        "is_container": False,
        "x": x,
        "y": y,
        "z": z,
        "yaw": 0.0,
        "json_filename": f"{map_base}_HR_D.json" if hr else f"{map_base}_D.json",
        "map_base": map_base,
        "version": "" if hr else "(D)",
        "group_parent": "",
        "sub_group_parent": "",
    }


class CrossFloorDedupTest(unittest.TestCase):
    """D 与 HR_D 去重必须同时比对 Z，否则跨楼层的不同生成点会被误删。"""

    def _extract(self, hr_rows: list[dict], d_rows: list[dict], map_base: str = "IceAbyss_DeepFlow") -> list[dict]:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / f"{map_base}_HR_D.json").write_text("[]", encoding="utf-8")
            (root / f"{map_base}_D.json").write_text("[]", encoding="utf-8")

            def fake_extract(path, **_):
                return hr_rows if path.stem.endswith("_HR_D") else d_rows

            with patch("db.importers.spawner_coordinates.extract_spawners", side_effect=fake_extract):
                return extract_all_spawners(root)

    def test_spawner_on_another_floor_is_kept(self):
        # 同一 X/Y，Z 相差 515：寒渊之流两层的不同生成点，不能合并
        hr = [_row("IceGiantSpider", -727.4, 782.7, 415.0, "IceAbyss_DeepFlow", hr=True)]
        d = [_row("GoblinSmuggler", -632.90204, 716.92523, -100.0, "IceAbyss_DeepFlow")]
        rows = self._extract(hr, d)
        self.assertEqual(sorted(r["keyword"] for r in rows), ["GoblinSmuggler", "IceGiantSpider"])

    def test_same_floor_duplicate_is_dropped(self):
        hr = [_row("IceGiantSpider", -727.4, 782.7, 415.0, "IceAbyss_DeepFlow", hr=True)]
        d = [_row("IceGiantSpider", -700.0, 760.0, 415.0, "IceAbyss_DeepFlow")]
        rows = self._extract(hr, d)
        # 只保留 HR_D 那一条
        self.assertEqual([r["keyword"] for r in rows], ["IceGiantSpider"])
        self.assertEqual([r["json_filename"] for r in rows], ["IceAbyss_DeepFlow_HR_D.json"])

    def test_spawner_on_another_floor_without_hr_sibling_is_kept(self):
        # HR_D 中根本没有该层生成点，去重不适用
        d = [_row("GoblinSmuggler", -632.90204, 716.92523, -100.0, "IceAbyss_DeepFlow")]
        rows = self._extract([], d)
        self.assertEqual([r["keyword"] for r in rows], ["GoblinSmuggler"])


if __name__ == "__main__":
    unittest.main()
