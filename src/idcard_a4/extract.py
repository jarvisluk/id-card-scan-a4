"""从 PDF（每页一张图）或图片文件里取出待处理的图像。"""
from __future__ import annotations

import io
from pathlib import Path

from PIL import Image

IMAGE_SUFFIXES = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".bmp"}


def _page_images(page) -> list[Image.Image]:
    """取一页里的内嵌图像，保持原始像素（不重新渲染整页）。"""
    out = []
    for img in page.images:
        try:
            im = Image.open(io.BytesIO(img.data))
            im.load()
        except Exception:
            continue
        out.append(im.convert("RGB"))
    return out


def load_images(paths: list[str], largest_only: bool = True) -> list[Image.Image]:
    """按给定顺序读取图像。PDF 每页取分辨率最高（默认唯一）的那张图。"""
    images: list[Image.Image] = []
    for p in paths:
        path = Path(p)
        if path.suffix.lower() == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            for page in reader.pages:
                imgs = _page_images(page)
                if not imgs:
                    continue
                if largest_only:
                    imgs = [max(imgs, key=lambda im: im.width * im.height)]
                images.extend(imgs)
        elif path.suffix.lower() in IMAGE_SUFFIXES:
            im = Image.open(path)
            im.load()
            images.append(im.convert("RGB"))
        else:
            raise ValueError(f"不支持的文件类型: {path}")
    if not images:
        raise ValueError("没有读到任何图像")
    return images
