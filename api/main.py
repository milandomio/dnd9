import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from collector import run
from config import DATA_DELIVERY_DIR, IMG_SRC, OUTPUT_DIR


def _deliver():
    """Move JSON + DB, copy images to DATA_DELIVERY_DIR for frontend."""
    dst = DATA_DELIVERY_DIR
    dst.mkdir(parents=True, exist_ok=True)

    # Move JSON outputs → data/json/
    json_dst = dst / "json"
    json_dst.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DIR.exists():
        for item in OUTPUT_DIR.iterdir():
            dest = json_dst / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                shutil.rmtree(item)
            else:
                shutil.move(str(item), str(dest))

    # Copy images → data/img/
    img_dst = dst / "img"
    img_dst.mkdir(parents=True, exist_ok=True)
    if IMG_SRC.exists():
        for f in IMG_SRC.iterdir():
            shutil.copy2(f, img_dst / f.name)

    img_count = len(list(IMG_SRC.iterdir())) if IMG_SRC.exists() else 0
    print(f"\n[DELIVER] data delivered to {dst}")
    print("  json/ → moved")
    print(f"  img/  → copied ({img_count} files)")


if __name__ == "__main__":
    run()
    _deliver()
