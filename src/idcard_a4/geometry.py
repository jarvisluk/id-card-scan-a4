"""几何处理：从画幅取卡面 → 透视取正 → 圆角遮罩。

默认策略是确定性的：证件照片基本都是"卡片顶满画幅"，因此直接以画幅为界，
按标准宽高比（85.6:54）居中裁切，再向内收一点切掉残余阴影细边。
这比自动找边稳得多 —— 卡片内部的花纹、MRZ 文字很容易被误判成边。
拍得比较松（四周留了大片桌面）的照片用 --quad 手动给四点即可。
"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageDraw

from . import CARD_H_MM, CARD_W_MM

CARD_ASPECT = CARD_W_MM / CARD_H_MM


def frame_quad(size: tuple[int, int], aspect: float = CARD_ASPECT,
               inset: float = 0.0) -> np.ndarray:
    """以画幅为界，按标准宽高比居中取卡面，返回 [[TL], [TR], [BR], [BL]]。

    inset 为向内收的比例（相对画幅宽/高），用来切掉照片边缘的阴影/背景细边。
    """
    w, h = size
    cw, ch = (h * aspect, float(h)) if w / h > aspect else (float(w), w / aspect)
    cw *= 1 - 2 * inset
    ch *= 1 - 2 * inset
    cx, cy = w / 2, h / 2
    return np.array([[cx - cw / 2, cy - ch / 2], [cx + cw / 2, cy - ch / 2],
                     [cx + cw / 2, cy + ch / 2], [cx - cw / 2, cy + ch / 2]])


def parse_quad(text: str) -> np.ndarray:
    """解析 "x1,y1,x2,y2,x3,y3,x4,y4"（TL, TR, BR, BL，源图像素坐标）。"""
    try:
        vals = [float(v) for v in text.replace(";", ",").split(",")]
    except ValueError as exc:
        raise ValueError("--quad 需要 8 个数字：x1,y1,x2,y2,x3,y3,x4,y4") from exc
    if len(vals) != 8:
        raise ValueError(f"--quad 需要 8 个数字，收到 {len(vals)} 个")
    return np.array(vals, float).reshape(4, 2)


def warp_quad(image: Image.Image, quad: np.ndarray, out_w: int, out_h: int) -> Image.Image:
    """把四边形透视校正成 out_w × out_h 的矩形。"""
    dst = [(0, 0), (out_w, 0), (out_w, out_h), (0, out_h)]
    A, B = [], []
    for (x, y), (u, v) in zip(dst, quad):
        A.append([x, y, 1, 0, 0, 0, -u * x, -u * y]); B.append(u)
        A.append([0, 0, 0, x, y, 1, -v * x, -v * y]); B.append(v)
    coeffs = np.linalg.solve(np.array(A, float), np.array(B, float))
    return image.transform((out_w, out_h), Image.PERSPECTIVE, coeffs, Image.BICUBIC)


def round_corners(image: Image.Image, radius_px: float, fill=(255, 255, 255)) -> Image.Image:
    """圆角矩形遮罩：圆角以外一律填白（顺带清掉照片四角露出的桌面/阴影）。"""
    mask = Image.new("L", image.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [0, 0, image.width - 1, image.height - 1], radius=radius_px, fill=255)
    out = Image.new(image.mode, image.size, fill)
    out.paste(image, (0, 0), mask)
    return out
