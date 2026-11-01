"""色彩处理：白平衡、色阶、多图底色对齐、锐化。全部基于 numpy + Pillow。"""
from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

LUMA = np.array([0.299, 0.587, 0.114])


def _luma(rgb: np.ndarray) -> np.ndarray:
    return rgb @ LUMA


def _box_mean(a: np.ndarray, r: int) -> np.ndarray:
    """半径 r 的滑动平均（积分图实现，无需 scipy）。"""
    k = 2 * r + 1
    pad = np.pad(a, ((r + 1, r), (r + 1, r)), mode="edge")
    s = pad.cumsum(0).cumsum(1)
    out = s[k:, k:] - s[:-k, k:] - s[k:, :-k] + s[:-k, :-k]
    return out / (k * k)


def local_std(gray: np.ndarray, r: int = 7) -> np.ndarray:
    mean = _box_mean(gray, r)
    return np.sqrt(np.maximum(_box_mean(gray * gray, r) - mean * mean, 0))


def to_array(img: Image.Image) -> np.ndarray:
    return np.asarray(img.convert("RGB"), float)


def to_image(arr: np.ndarray) -> Image.Image:
    return Image.fromarray(np.clip(arr, 0, 255).round().astype(np.uint8))


def white_balance(rgb: np.ndarray, lo: float = 10, hi: float = 95,
                  clamp: float = 0.02) -> tuple[np.ndarray, np.ndarray]:
    """中调灰世界估计光源。

    clamp 把修正量限制在 ±clamp（默认 ±2%），避免把证件本身的冷色底纹
    （浅蓝）/暖色区域当成偏色推成灰白——那是把底色处理“发黄”的根源。
    """
    lum = _luma(rgb)
    m = (lum >= np.percentile(lum, lo)) & (lum <= np.percentile(lum, hi))
    ref = np.median(rgb[m], axis=0)
    gains = np.clip(ref.mean() / np.maximum(ref, 1), 1 - clamp, 1 + clamp)
    return rgb * gains, gains


def levels(rgb: np.ndarray, lo: float = 0.5, hi: float = 99.7,
           strength: float = 1.06, white_cap: float = 251.0) -> np.ndarray:
    """按亮度做色阶（黑场/白场定位 + 中灰为轴拉伸），结果按比例回传各通道，保色相。

    white_cap < 255 可以保住高光里的底纹细节，避免纸张糊成死白。
    """
    lum = _luma(rgb)
    b, w = np.percentile(lum, lo), np.percentile(lum, hi)
    norm = np.clip((lum - b) / max(w - b, 1e-6), 0, 1)
    norm = np.clip(0.5 + (norm - 0.5) * strength, 0, 1) * white_cap
    return rgb * (norm / np.maximum(lum, 1e-3))[..., None]


def sharpen(img: Image.Image, radius: float = 1.1, percent: int = 55,
            threshold: int = 3) -> Image.Image:
    return img.filter(ImageFilter.UnsharpMask(radius=radius, percent=percent, threshold=threshold))


def paper_color(img: Image.Image) -> np.ndarray:
    """估计"纸张底色"：平滑（低局部方差）+ 偏亮像素的中值色。

    避开文字、花纹和纯白遮罩，才能代表真正的底纹颜色。
    """
    rgb = to_array(img)
    lum = _luma(rgb)
    sd = local_std(lum)
    m = (sd <= np.percentile(sd, 35) + 1e-9) & (lum >= np.percentile(lum, 60)) & (lum < 252)
    if not m.any():
        m = lum > np.percentile(lum, 90)
    return np.median(rgb[m], axis=0)


def match_paper(imgs: list[Image.Image], target: np.ndarray | None = None,
                clamp: float = 0.1) -> tuple[list[Image.Image], np.ndarray]:
    """把多张图的纸张底色对齐到同一目标值（默认取各自平均值）。

    证件正反面背景本是同一张纸，扫描/拍摄后常一冷一暖，这一步消除色相差。
    """
    cols = [paper_color(im) for im in imgs]
    tgt = target if target is not None else np.mean(cols, axis=0)
    out = []
    for im, col in zip(imgs, cols):
        gain = np.clip(tgt / np.maximum(col, 1), 1 - clamp, 1 + clamp)
        out.append(to_image(to_array(im) * gain))
    return out, tgt
