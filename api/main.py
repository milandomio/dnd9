import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from collector import run
from config import DATA_DELIVERY_DIR, IMG_SRC, LOG_DIR, OUTPUT_DIR
from pipeline_timer import PipelineTimer

PLACEHOLDER_IMG = "RareModule_1x1"


def _deliver(timer: PipelineTimer | None = None):
    """Move JSON outputs and copy images to DATA_DELIVERY_DIR for frontend.

    DB is a backend-only file and must NOT be delivered to the frontend area.
    """
    if timer:
        timer.start_step("[DELIVER] data delivery")
    dst = DATA_DELIVERY_DIR
    dst.mkdir(parents=True, exist_ok=True)

    # Remove any stale .db files from delivery dir (backend-only)
    for stale_db in dst.glob("*.db"):
        stale_db.unlink()

    # Move JSON outputs → data/json/
    # Exclude files only used internally by the pipeline (not fetched by frontend)
    skip_deliver = {"entity_index.json", "quest_items.json"}
    json_dst = dst / "json"
    json_dst.mkdir(parents=True, exist_ok=True)
    if OUTPUT_DIR.exists():
        for item in OUTPUT_DIR.iterdir():
            if item.suffix == ".db":
                continue  # skip DB files
            if item.name in skip_deliver:
                continue  # skip pipeline-internal files
            dest = json_dst / item.name
            if item.is_dir():
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(item, dest)
                shutil.rmtree(item, ignore_errors=True)
            else:
                shutil.move(str(item), str(dest))

    # Copy images → data/img/
    img_dst = dst / "img"
    img_dst.mkdir(parents=True, exist_ok=True)
    if IMG_SRC.exists():
        for f in IMG_SRC.iterdir():
            shutil.copy2(f, img_dst / f.name)

    img_count = len(list(IMG_SRC.iterdir())) if IMG_SRC.exists() else 0
    if timer:
        timer.end_step()
    print(f"\n[DELIVER] data delivered to {dst}")
    print("  json/ → moved")
    print(f"  img/  → copied ({img_count} files)")

    # Output final timing summary (includes delivery)
    if timer:
        print(timer.summary())


def _validate_images():
    """Scan dungeon_modules.json and patch any missing img_name references.

    After delivery, some modules may reference .webp files that don't exist
    (e.g. image was never extracted). This replaces them with the placeholder
    so the frontend never sees a 404.
    """
    img_dir = DATA_DELIVERY_DIR / "img"
    json_dir = DATA_DELIVERY_DIR / "json"
    modules_file = json_dir / "dungeon_modules.json"
    if not modules_file.exists():
        return

    placeholder_src = img_dir / f"{PLACEHOLDER_IMG}.webp"
    if not placeholder_src.exists():
        print(f"[VALIDATE] placeholder {PLACEHOLDER_IMG}.webp not found, skipping")
        return

    modules = json.loads(modules_file.read_text(encoding="utf-8"))
    patched = 0
    for m in modules:
        img_name = m.get("img_name", "")
        if not img_name or img_name == PLACEHOLDER_IMG:
            continue
        if not (img_dir / f"{img_name}.webp").exists():
            print(f"[VALIDATE] {m['name']}: {img_name}.webp missing → {PLACEHOLDER_IMG}")
            m["img_name"] = PLACEHOLDER_IMG
            m["has_img"] = True
            patched += 1

    if patched:
        modules_file.write_text(json.dumps(modules, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"[VALIDATE] patched {patched} missing images")
    else:
        print("[VALIDATE] all module images OK")


def _cleanup_old_logs(log_dir: Path, keep: int = 10):
    """Remove old log files, keeping only the most recent ones."""
    if not log_dir.exists():
        return
    logs = sorted(log_dir.glob("pipeline_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_log in logs[keep:]:
        old_log.unlink()


def _pre_cleanup():
    """Remove stale data/json/ before pipeline to avoid double disk usage.

    Pipeline writes to api/output/json/ first, then delivers to data/json/.
    Cleaning data/json/ upfront frees space for the pipeline output.
    """
    json_dir = DATA_DELIVERY_DIR / "json"
    if json_dir.exists():
        shutil.rmtree(json_dir)
        print(f"[CLEANUP] removed {json_dir}")


if __name__ == "__main__":
    _pre_cleanup()
    timer = run()
    _deliver(timer)
    _validate_images()

    # Save log and cleanup old ones
    if timer:
        log_file = timer.save_log()
        if log_file:
            print(f"  log saved: {log_file}")
        _cleanup_old_logs(LOG_DIR)
