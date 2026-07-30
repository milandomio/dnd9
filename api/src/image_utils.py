"""
图像处理工具模块

重要：api/src/img/ 中的 .webp 文件是已交付的静态资产。
- 禁止删除 api/src/img/ 目录下的任何 .webp 文件。
- 构建阶段不再扫描游戏解包目录或转换 PNG。
- 已有 .webp 永远不会被覆盖或删除。

包含：
- sync_webp_images(): 校验已交付的 WebP 静态资源
- compress_and_save_image(): 单个 PNG → WebP 转换（Pillow）
"""

from pathlib import Path

from config import IMG_SRC


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
    delivered = sum(1 for path in IMG_SRC.glob("*.webp") if path.is_file())
    log_fn(f"[IMG] using {delivered} delivered WebP assets")
