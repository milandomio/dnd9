"""
图像处理工具模块

⚠️ 重要：api/src/img/ 中的 .webp 文件是不可再生资源
- 这些文件从游戏解包的 PNG 转换而来，转换后即视为静态资产
- 禁止删除 api/src/img/ 目录下的任何 .webp 文件（无法从游戏重新提取）
- 仅当 Art/ 目录中有新的 PNG 且对应 .webp 不存在时，才执行新增转换
- 已有 .webp 永远不会被覆盖或删除

包含：
- sync_webp_images(): 扫描 Art/DungeonModuleMapImage/ 目录，将新 PNG 转为 WebP
- compress_and_save_image(): 单个 PNG → WebP 转换（Pillow）
"""

from pathlib import Path

from config import GAME_ROOT, GROUP_TO_ART_DIR, IMG_SRC


def compress_and_save_image(src_path: Path, dest_path: Path, quality: int = 85) -> bool:
    try:
        from PIL import Image
    except ImportError:
        return False
    try:
        img = Image.open(src_path)
        if img.mode == "P":
            img = img.convert("RGBA")
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest_path, "WEBP", quality=quality, method=6)
        return True
    except Exception:
        return False


def sync_webp_images(log_fn=print):
    art_root = GAME_ROOT / "Data" / "Art" / "DungeonModuleMapImage"
    if not art_root.exists():
        log_fn(f"[IMG] art root not found: {art_root}")
        return

    dirs_to_scan = list(GROUP_TO_ART_DIR.values())
    # also check root of DungeonModuleMapImage for ungrouped PNGs
    dirs_to_scan.insert(0, ".")

    total = success = skipped = failed = 0

    for subdir in dirs_to_scan:
        scan_dir = art_root / subdir if subdir != "." else art_root
        if not scan_dir.exists():
            continue
        for png_path in scan_dir.iterdir():
            if png_path.suffix.lower() != ".png":
                continue
            total += 1
            stem = png_path.stem
            webp_path = IMG_SRC / f"{stem}.webp"
            if webp_path.exists():
                skipped += 1
                continue
            if compress_and_save_image(png_path, webp_path):
                log_fn(f"  [IMG] {stem}.png → {stem}.webp")
                success += 1
            else:
                log_fn(f"  [IMG] FAILED: {stem}.png")
                failed += 1

    if total:
        log_fn(f"[IMG] synced: {total} PNGs, {success} new, {skipped} skipped, {failed} failed")
