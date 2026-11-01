"""A4 排版：把处理好的卡面按 1:1 或"适应纸张"摆到 A4 上。"""
from __future__ import annotations

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from . import CARD_H_MM, CARD_W_MM

PT_PER_MM = 72 / 25.4


def place_on_a4(cards: list, out_path: str, mode: str = "real", layout: str = "vertical",
                gap_mm: float = 10.0, margin_mm: float = 15.0,
                real_w_mm: float = CARD_W_MM, real_h_mm: float = CARD_H_MM,
                title: str = "证件 1:1 打印") -> str:
    """cards: [(图片路径或 PIL.Image, 宽高比)]，按顺序摆放。

    mode="real"  每张按真实尺寸（默认 85.6×54 mm，ID-1）绘制 —— 打印出即实物大小
    mode="fit"   等比缩放到页边距内，占满可用宽度
    layout        "vertical" 纵向堆叠 / "horizontal" 并排
    """
    if layout not in {"vertical", "horizontal"}:
        raise ValueError("layout 只能是 vertical 或 horizontal")
    if mode not in {"real", "fit"}:
        raise ValueError("mode 只能是 real 或 fit")

    pw, ph = A4
    avail_w, avail_h = pw - 2 * margin_mm * PT_PER_MM, ph - 2 * margin_mm * PT_PER_MM

    if mode == "real":
        w, h = real_w_mm * PT_PER_MM, real_h_mm * PT_PER_MM
    else:                                       # 等比缩放到可用纸面，按排列方向分配
        gap_pt = gap_mm * PT_PER_MM
        n = len(cards)
        if layout == "vertical":
            h = min(avail_w / (CARD_W_MM / CARD_H_MM),
                    (avail_h - gap_pt * (n - 1)) / n)
            w = h * (CARD_W_MM / CARD_H_MM)
        else:
            w = min((avail_w - gap_pt * (n - 1)) / n, avail_h * (CARD_W_MM / CARD_H_MM))
            h = w / (CARD_W_MM / CARD_H_MM)
    gap = gap_mm * PT_PER_MM

    if layout == "vertical":
        total_w = w
        total_h = h * len(cards) + gap * (len(cards) - 1)
    else:
        total_w = w * len(cards) + gap * (len(cards) - 1)
        total_h = h
    if total_w > avail_w + 0.5 or total_h > avail_h + 0.5:
        raise ValueError(f"排版超出页边距：需要 {total_w/PT_PER_MM:.1f}×{total_h/PT_PER_MM:.1f} mm，"
                         f"可用 {avail_w/PT_PER_MM:.1f}×{avail_h/PT_PER_MM:.1f} mm（可调小 --gap/--margin）")

    c = canvas.Canvas(out_path, pagesize=A4)
    c.setTitle(title)
    x_center = pw / 2
    top = (ph + total_h) / 2
    for i, card in enumerate(cards):
        src = card[0] if isinstance(card, tuple) else card
        if layout == "vertical":
            x = x_center - w / 2
            y = top - (i + 1) * h - i * gap
        else:
            x = x_center - total_w / 2 + i * (w + gap)
            y = top - h
        c.drawImage(src, x, y, w, h)
    c.showPage()
    c.save()
    return out_path
