"""回归测试：取面裁切/透视/圆角、底色对齐。

    .venv/bin/python -m pytest -q
"""
from __future__ import annotations

import numpy as np
from PIL import Image

from idcard_a4 import CARD_H_MM, CARD_W_MM
from idcard_a4.color import match_paper, paper_color, to_image
from idcard_a4.geometry import frame_quad, parse_quad, round_corners, warp_quad

ASPECT = CARD_W_MM / CARD_H_MM


def test_frame_quad_follows_card_aspect():
    quad = frame_quad((1496, 948))
    w = np.linalg.norm(quad[1] - quad[0])
    h = np.linalg.norm(quad[3] - quad[0])
    assert abs(w / h - ASPECT) < 1e-6
    assert abs(w - 1496) < 1e-6            # 宽画幅：以宽为准，裁高
    assert np.allclose(quad.mean(axis=0), (748, 474))   # 居中


def test_frame_quad_inset_shrinks():
    quad = frame_quad((1000, 800), inset=0.01)
    plain = frame_quad((1000, 800))
    assert (np.linalg.norm(quad[1] - quad[0]) <
            np.linalg.norm(plain[1] - plain[0]))
    assert np.allclose(quad.mean(axis=0), plain.mean(axis=0))


def test_parse_quad():
    q = parse_quad("0,0, 10,0, 10,5, 0,5")
    assert q.shape == (4, 2)
    assert np.allclose(q[2], (10, 5))


def test_warp_quad_keeps_content_and_size():
    img = Image.new("RGB", (800, 600))
    for x in range(0, 800, 40):                    # 竖条纹，便于检查是否被拉伸
        img.paste((0, 0, 0), (x, 0, x + 20, 600))
    card = warp_quad(img, frame_quad(img.size), 856, 540)
    assert card.size == (856, 540)
    arr = np.asarray(card.convert("L"))
    assert arr.mean() < 200                        # 黑白条纹还在
    assert abs(856 / 540 - ASPECT) < 0.01


def test_round_corners_whitens_corners():
    img = Image.new("RGB", (400, 250), (10, 20, 30))
    out = round_corners(img, radius_px=20)
    for xy in [(0, 0), (399, 0), (0, 249), (399, 249)]:
        assert out.getpixel(xy) == (255, 255, 255)
    assert out.getpixel((200, 125)) == (10, 20, 30)


def test_match_paper_equalizes_background():
    a = np.zeros((200, 300, 3))
    a[..., 0], a[..., 1], a[..., 2] = 200, 210, 220      # 偏冷
    b = np.zeros((200, 300, 3))
    b[..., 0], b[..., 1], b[..., 2] = 215, 212, 205      # 偏暖
    out, _ = match_paper([to_image(a), to_image(b)])
    ca, cb = paper_color(out[0]), paper_color(out[1])
    assert np.abs(ca - cb).max() <= 2, f"底色仍不一致: {ca.round(1)} vs {cb.round(1)}"
