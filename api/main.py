import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from collector import run
from config import DATA_DELIVERY_DIR, IMG_SRC, LOG_DIR, OUTPUT_DIR
from pipeline_timer import PipelineTimer


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
    if timer:
        timer.end_step()
    print(f"\n[DELIVER] data delivered to {dst}")
    print("  json/ → moved")
    print(f"  img/  → copied ({img_count} files)")

    # Output final timing summary (includes delivery)
    if timer:
        print(timer.summary())


def _cleanup_old_logs(log_dir: Path, keep: int = 10):
    """Remove old log files, keeping only the most recent ones."""
    if not log_dir.exists():
        return
    logs = sorted(log_dir.glob("pipeline_*.log"), key=lambda f: f.stat().st_mtime, reverse=True)
    for old_log in logs[keep:]:
        old_log.unlink()


if __name__ == "__main__":
    timer = run()
    _deliver(timer)

    # Save log and cleanup old ones
    if timer:
        log_file = timer.save_log()
        if log_file:
            print(f"  log saved: {log_file}")
        _cleanup_old_logs(LOG_DIR)
