"""把证件照片（PDF 或图片）处理成扫描件效果，并按 1:1 排到 A4 上打印。"""

__version__ = "0.1.0"

CARD_W_MM = 85.6   # ID-1 标准卡（银行卡/往来港澳通行证）宽度
CARD_H_MM = 54.0
CORNER_R_MM = 3.18  # ID-1 标准圆角半径

from .color import levels, match_paper, paper_color, sharpen, white_balance  # noqa: E402
from .extract import load_images  # noqa: E402
from .geometry import frame_quad, parse_quad, round_corners, warp_quad  # noqa: E402
from .layout import place_on_a4  # noqa: E402

__all__ = [
    "CARD_W_MM", "CARD_H_MM", "CORNER_R_MM",
    "load_images", "frame_quad", "parse_quad", "warp_quad", "round_corners",
    "white_balance", "levels", "sharpen", "paper_color", "match_paper",
    "place_on_a4",
]
