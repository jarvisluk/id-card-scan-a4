"""命令行入口：idcard-a4 输入.pdf -o 输出.pdf"""
from __future__ import annotations

import argparse

import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

from . import CORNER_R_MM, CARD_H_MM, CARD_W_MM
from .color import (levels, match_paper, paper_color, sharpen, to_array,
                    to_image, white_balance)
from .extract import load_images
from .geometry import frame_quad, parse_quad, round_corners, warp_quad
from .layout import place_on_a4


def _parse_size(text: str) -> tuple[float, float]:
    try:
        w, h = text.lower().replace("×", "x").split("x")
        return float(w), float(h)
    except Exception as exc:
        raise argparse.ArgumentTypeError("尺寸格式应为 宽x高（mm），例如 85.6x54") from exc


def _dump_quad(img: Image.Image, quad, path: Path) -> None:
    vis = img.copy()
    d = ImageDraw.Draw(vis)
    d.line([tuple(p) for p in quad] + [tuple(quad[0])], fill=(255, 0, 255), width=4)
    vis.save(path)


def build(args) -> Path:
    size_w, size_h = args.size
    dpi = args.dpi
    out_w = int(round(size_w / 25.4 * dpi))
    out_h = int(round(size_h / 25.4 * dpi))

    images = load_images(args.inputs)
    if args.reverse:
        images = images[::-1]
    print(f"读取 {len(images)} 张图，输出 {out_w}×{out_h} px/张（{dpi} dpi）")

    tmp = Path(args.keep_images) if args.keep_images else Path(tempfile.mkdtemp(prefix="idcard-a4-"))
    tmp.mkdir(parents=True, exist_ok=True)

    cards: list[Image.Image] = []
    for i, img in enumerate(images, 1):
        quad = parse_quad(args.quad) if args.quad else frame_quad(
            img.size, aspect=size_w / size_h, inset=args.inset / size_w)
        if args.save_quad:
            Path(args.save_quad).mkdir(parents=True, exist_ok=True)
            _dump_quad(img, quad, Path(args.save_quad) / f"quad-{i}.png")
        card = warp_quad(img, quad, out_w, out_h)

        arr = to_array(card)
        if not args.no_wb:
            arr, gains = white_balance(arr, clamp=args.wb_clamp)
            print(f"  第 {i} 张 白平衡增益 {[round(float(g), 3) for g in gains]}")
        if not args.no_contrast:
            arr = levels(arr, strength=args.contrast)
        card = to_image(arr)
        if not args.no_sharpen:
            card = sharpen(card)
        cards.append(card)

    if not args.no_match_paper and len(cards) > 1:
        before = [paper_color(c).round(1).tolist() for c in cards]
        cards, tgt = match_paper(cards)
        after = [paper_color(c).round(1).tolist() for c in cards]
        print(f"  底色对齐 {before} → {after}（目标 {tgt.round(1).tolist()}）")

    if args.corner_radius > 0:
        r = args.corner_radius / 25.4 * dpi
        cards = [round_corners(c, r) for c in cards]

    paths = []
    for i, card in enumerate(cards, 1):
        p = tmp / f"card-{i}.jpg"
        card.save(p, quality=args.quality, subsampling=0)
        paths.append(str(p))
        print(f"  第 {i} 张 → {p}")

    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    place_on_a4(paths, str(out), mode=args.mode, layout=args.layout,
                gap_mm=args.gap, margin_mm=args.margin,
                real_w_mm=size_w, real_h_mm=size_h,
                title=f"证件打印 {size_w}x{size_h}mm")
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(
        prog="idcard-a4",
        description="证件照片（PDF/图片）→ 透视取正 + 去背景 + 色彩校正 → 一页 A4（默认 1:1）")
    p.add_argument("inputs", nargs="+", help="输入文件：PDF（每页一张图）或图片")
    p.add_argument("-o", "--output", required=True, help="输出 PDF 路径")
    p.add_argument("--size", type=_parse_size, default=(CARD_W_MM, CARD_H_MM),
                   help="证件真实尺寸 宽x高（mm），默认 85.6x54（ID-1 卡）")
    p.add_argument("--mode", choices=["real", "fit"], default="real",
                   help="real=按真实尺寸 1:1；fit=等比缩放到可用纸面")
    p.add_argument("--layout", choices=["vertical", "horizontal"], default="vertical",
                   help="多张时的排列方向（默认纵向堆叠）")
    p.add_argument("--gap", type=float, default=10.0, help="间距 mm（默认 10）")
    p.add_argument("--margin", type=float, default=15.0, help="页边距 mm（默认 15）")
    p.add_argument("--dpi", type=int, default=500, help="1:1 模式下每张图的渲染分辨率（默认 500）")
    p.add_argument("--corner-radius", type=float, default=CORNER_R_MM,
                   help=f"圆角半径 mm（默认 {CORNER_R_MM}，0 = 不做圆角）")
    p.add_argument("--quad", help="手动指定卡面四点（源图像素，TL,TR,BR,BL）：x1,y1,...,x4,y4")
    p.add_argument("--contrast", type=float, default=1.06, help="对比度拉伸强度（默认 1.06）")
    p.add_argument("--inset", type=float, default=0.2,
                   help="四边向内收多少 mm，切掉照片边缘的阴影/背景细边（默认 0.2，0 = 不内收）")
    p.add_argument("--wb-clamp", type=float, default=0.02,
                   help="白平衡最大修正比例（默认 0.02 = ±2%%）")
    p.add_argument("--quality", type=int, default=96, help="中间 JPEG 质量（默认 96）")
    p.add_argument("--reverse", action="store_true", help="反转页面顺序（例如让卡面排在上方）")
    p.add_argument("--no-wb", action="store_true", help="跳过白平衡")
    p.add_argument("--no-contrast", action="store_true", help="跳过对比度处理")
    p.add_argument("--no-sharpen", action="store_true", help="跳过锐化")
    p.add_argument("--no-match-paper", action="store_true", help="跳过正反面底色对齐")
    p.add_argument("--keep-images", help="保存中间图像到指定目录")
    p.add_argument("--save-quad", help="保存边缘检测结果（洋红色框）到指定目录，便于排查")
    args = p.parse_args(argv)

    out = build(args)
    print(f"完成：{out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
