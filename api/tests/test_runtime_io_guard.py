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
)
FORBIDDEN_REFERENCES = (
    "Output/Exports",
    "Localization/Game",
    "MAPS_DIR",
    "LAYOUT_DIR",
    "SPAWNER_DIR",
    "DungeonModuleMapImage",
)


def test_runtime_modules_do_not_reference_unpack_paths():
    src_root = Path(__file__).parents[1] / "src"
    violations = []
    for relative_path in RUNTIME_MODULES:
        path = src_root / relative_path
        text = path.read_text(encoding="utf-8")
        for reference in FORBIDDEN_REFERENCES:
            if reference in text:
                violations.append(f"{relative_path}: {reference}")
    assert not violations, "runtime unpack references found: " + ", ".join(violations)
