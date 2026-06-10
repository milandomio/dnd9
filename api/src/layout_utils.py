import json
import math
import os
from pathlib import Path

from config import LAYOUT_DIR


def load_all_layout_rotations() -> dict[str, int]:
    if not LAYOUT_DIR.exists():
        return {}
    rotations: dict[str, int] = {}
    for dirpath, _, filenames in os.walk(LAYOUT_DIR):
        for fn in filenames:
            if not fn.endswith(".json"):
                continue
            fp = Path(dirpath) / fn
            try:
                with open(fp, encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                continue
            if not isinstance(data, list):
                continue
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                if entry.get("Type") != "LevelStreamingAlwaysLoaded":
                    continue
                props = entry.get("Properties", {}) or {}
                asset = (props.get("WorldAsset") or {}).get("AssetPathName", "")
                if not asset:
                    continue
                rot = (props.get("LevelTransform") or {}).get("Rotation", {}) or {}
                z = rot.get("Z", 0)
                w = rot.get("W", 1)
                yaw_rad = 2 * math.atan2(z, w)
                yaw_deg = math.degrees(yaw_rad)
                js_rotate = round((yaw_deg - 90) % 360, 1)
                base = _extract_module_base(asset)
                if base:
                    rotations[base] = js_rotate
    return rotations


def _extract_module_base(asset_path: str) -> str:
    base = asset_path.split("/")[-1]
    if "." in base:
        base = base.rsplit(".", 1)[0]
    for suffix in ["_A", "_D", "_S", "_HR", "_HR_D"]:
        if base.endswith(suffix):
            base = base[: -len(suffix)]
            break
    return base
