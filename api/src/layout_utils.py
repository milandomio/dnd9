def load_all_layout_rotations(db=None) -> dict[str, int]:
    """Return rotations already imported into the database."""
    if db is None:
        return {}
    return {
        row["module_name"]: row["rotation"]
        for row in db.get_dungeon_modules()
        if row.get("module_name") and row.get("rotation") is not None
    }


def _extract_module_base(asset_path: str) -> str:
    base = asset_path.split("/")[-1]
    if "." in base:
        base = base.rsplit(".", 1)[0]
    for suffix in ["_A", "_D", "_S", "_HR", "_HR_D"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base
