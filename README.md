# id-card-scan-a4

[中文说明](README.zh-CN.md) · **English**

Turn phone photos of an ID-sized card into a clean, scan-like image and lay both sides out on
a single A4 page **at 1:1 real size**, ready to print.

Built for the case where a photo is all you have: slight perspective, desk visible at the corners,
front and back shot under different lighting, and the printout comes out tiny and grubby.

## What it does

| Step | How |
| --- | --- |
| Crop | Take the frame, center-crop to the standard aspect ratio (85.6:54 by default), inset 0.2 mm to shave off edge shadow |
| Rectify | 4-point perspective transform to the target rectangle at 500 dpi (1685×1063 px) |
| White balance | Mid-tone gray-world illuminant estimate, correction **clamped to ±2%** so the card's own cool tint is not pushed to cream |
| Contrast | Luminance levels (black/white point + mid-gray stretch), scaled back onto RGB to preserve hue; white point capped at 251 to keep highlight detail |
| Background match | Estimate each side's paper color and align both to one target, so the two sides look like the same card |
| Corners | ID-1 corner radius (3.18 mm) mask; everything outside is filled white — which also removes desk visible at the corners |
| Layout | A4 portrait, real size 85.6×54 mm, stacked or side by side |

## Install

```bash
git clone https://github.com/jarvisluk/id-card-scan-a4.git
cd id-card-scan-a4
uv venv && uv pip install -e . pytest
```

Requires Python 3.10+. Dependencies: `pillow`, `numpy`, `pypdf`, `reportlab` — no scipy, no poppler CLI.

## Usage

```bash
# front and back on one page, front on top
.venv/bin/idcard-a4 front.pdf back.pdf -o out.pdf

# a single PDF with one side per page: put page 2 on top
.venv/bin/idcard-a4 scan.pdf --reverse -o out.pdf

# just fill the page (not real size), side by side
.venv/bin/idcard-a4 scan.pdf --mode fit --layout horizontal -o out.pdf

# shot with a lot of desk around the card: give the four corners yourself
# (source pixels, TL / TR / BR / BL)
.venv/bin/idcard-a4 photo.jpg -o out.pdf --quad 120,90,1080,60,1090,700,110,730

# sanity check: draw the quad that will be used
.venv/bin/idcard-a4 photo.jpg -o out.pdf --save-quad /tmp/quad
```

If the console script is on your `PATH`, use `idcard-a4` instead of `.venv/bin/idcard-a4`.

### Options

| Flag | Default | Meaning |
| --- | --- | --- |
| `--size` | `85.6x54` | Real card size in mm (passport, etc.) |
| `--mode` | `real` | `real` = 1:1 physical size; `fit` = scale to printable area |
| `--layout` | `vertical` | `vertical` stack / `horizontal` row |
| `--gap`, `--margin` | `10`, `15` | Gap and page margin in mm |
| `--inset` | `0.2` | Inset each side by this many mm to cut edge shadow (`0` = off) |
| `--corner-radius` | `3.18` | Corner radius in mm (`0` = square corners) |
| `--quad` | — | Manual card corners in source pixels: `x1,y1,...,x4,y4` |
| `--wb-clamp` | `0.02` | Max white-balance correction ratio |
| `--contrast` | `1.06` | Contrast stretch strength |
| `--dpi` | `500` | Render resolution per card in `real` mode |
| `--reverse` | off | Reverse page order |
| `--no-wb`, `--no-contrast`, `--no-sharpen`, `--no-match-paper` | off | Skip a step |
| `--keep-images`, `--save-quad` | — | Keep intermediate images / visualize the quad |

## Printing

Choose **"Actual size / 100%"** in the print dialog and turn off "Fit to page".
The layout is physical size, not page-relative — any auto-scaling breaks the 1:1.

## Design notes

- **No automatic edge detection.** Texture segmentation, region growing, and gradient peaks with
  step/smoothness checks were all tried: guilloche patterns, MRZ text and QR codes masquerade as
  card edges, and a 1–2 mm miss either eats card content or pulls the desk in. The deterministic
  path (frame + standard aspect + small inset) is off by < 0.5 mm and never misfires; for loose
  framing use `--quad`. The trade-off is explicit and cheap.
- **White balance clamped to ±2%.** A plain gray-world treats the card's light blue background as a
  cast and pushes it to cream/ivory — that is exactly how an earlier version looked yellow.
- **White point at 251, not 255.** Keeps the guilloche texture in highlights so a printout reads as
  a card rather than blank paper.
- **Paper color uses a median, not a mean.** Large colored areas (photo background, red emblem)
  would drag a mean around.

## Data safety

Cards are sensitive. This repository holds **no scans, photos or output files**:

- `.gitignore` ignores `*.pdf`, `*.jpg`, `*.png`, `*.docx`, … plus `samples/`, `out/`, `output/`
- `.githooks/pre-commit` rejects image/PDF/Office files and text that looks like an ID number or an
  MRZ line
- Enable the hook after cloning:

```bash
git config core.hooksPath .githooks
```

Deliberately committing redacted or synthetic test data: `git commit --no-verify`.

## Layout

```
src/idcard_a4/
  extract.py   # PDF / image → PIL image (embedded image, no page re-render)
  geometry.py  # frame crop, perspective transform, rounded-corner mask
  color.py     # white balance, levels, paper-color statistics and matching, sharpening
  layout.py    # A4 placement (reportlab)
  cli.py       # command line
tests/         # regression tests on synthetic images only
```

```bash
.venv/bin/python -m pytest -q
```

## Scope

- Input is a photo or scan of a card, assumed to roughly fill the frame. Loose framing: use `--quad`.
- No real ID data in the repo; all tests synthesize their own images.

## License

MIT — see [LICENSE](LICENSE).
