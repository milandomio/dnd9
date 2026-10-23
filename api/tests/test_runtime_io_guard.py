import unittest
from pathlib import Path

RUNTIME_MODULES = (
    "db/_helpers.py",
    "db/__init__.py",
    "search_engine.py",
    "layout_utils.py",
    "module_builder.py",
    "image_utils.py",
    "locale_builder.py",
    "search_index_builder.py",
    "enrichment.py",
    "collector.py",
    # The shop export reads categories, rarities and prices back from the DB.
    # It must never reach for the unpacked assets: CI does not have them.
    "merchant_builder.py",
)
FORBIDDEN_REFERENCES = (
    "Output/Exports",
    "Localization/Game",
    "MAPS_DIR",
    "LAYOUT_DIR",
    "SPAWNER_DIR",
    "DungeonModuleMapImage",
)


class RuntimeIoGuardTest(unittest.TestCase):
    """Export-phase modules must only read the DB, never the unpacked assets.

    CI has no game assets, so any export-phase reference to an unpack path would
    only fail after the import phase had already populated the DB.
    """

    def test_runtime_modules_do_not_reference_unpack_paths(self):
        src_root = Path(__file__).parents[1] / "src"
        violations = []
        for relative_path in RUNTIME_MODULES:
            path = src_root / relative_path
            text = path.read_text(encoding="utf-8")
            for reference in FORBIDDEN_REFERENCES:
                if reference in text:
                    violations.append(f"{relative_path}: {reference}")
        self.assertFalse(violations, "runtime unpack references found: " + ", ".join(violations))


if __name__ == "__main__":
    unittest.main()
