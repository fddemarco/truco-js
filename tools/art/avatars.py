# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11", "numpy>=2", "scipy>=1.14"]
# ///
"""Turn image-model galleries into avatar sprites that share one head frame per character.

The model returns grids of cells (usually 3×3) with the background often baked in as a fake
checkerboard, or black (turned white first). This tool cuts each cell out and aligns it to the
character's neutral face, so the head never moves when a seña plays at the table. Then a person
reviews the cells (correct gesture, correct side, readable at 80 px) and moves each one into
place. The workflow and review bar are in `docs/art-prompts.md`.

    uv run tools/art/avatars.py init <character> --base <base image> --sheet <gallery>
        Start a character: the frame is cell --ref-cell of the gallery (head and shoulders).
        Writes approved/<character>/base.png (the neutral face in that frame) and portrait.png.

    uv run tools/art/avatars.py sheet <character> <gallery> [--grid 3x3]
        Cut out and align every cell to approved/<character>/base.png. Writes
        candidates/<character>/<gallery>-cell<N>.png and a <gallery>-review.png contact sheet.

    uv run tools/art/avatars.py mirror <character> <source> <seña> --box X0,Y0,X1,Y1 [--box ...]
        Make the mirror-image seña from an existing one: inside the boxes (frame pixels), the
        source is replaced by its own reflection across the face's symmetry axis. 03 comes from
        04 (and back), and a wink on the wrong eye becomes 02. The source can be an approved
        image (already in the frame) or any cutout, which is aligned first. Writes
        candidates/<character>/<seña>-mirrored.png and a review sheet with the box drawn in.
        Boxes are widened to be symmetric about the axis unless --exact; --erase paints a box
        with the surrounding skin to remove a stroke the old expression leaves behind.

Then move each candidate to approved/<character>/<seña>.png or failed/<character>/, and run
`cd frontend && pnpm import-art`.
"""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy import ndimage
from scipy.signal import fftconvolve

ROOT = Path(__file__).resolve().parents[2]
AVATARS = ROOT / "assets" / "avatars"
OUT = 512  # the frame every variant is drawn in
MATCH = 160  # resolution the head silhouettes are matched at
HEAD = 0.62  # top share of the frame used for matching: the head, not hands or props
REF_CELL = 6  # in the first galleries the kiss cell had the cleanest head-and-shoulders framing

# --- background removal -------------------------------------------------------------------


def strip_frame(rgb: np.ndarray) -> np.ndarray:
    """Without a uniform grey frame some galleries draw around each cell (up to 5% per side)."""

    def is_frame(line: np.ndarray) -> bool:
        a = line.astype(int)
        grey = (a.max(1) - a.min(1)).mean() < 12
        return grey and a.std() < 12 and 60 < a.mean() < 235  # not the white or black background

    limit = round(min(rgb.shape[:2]) * 0.05)
    top, bottom, left, right = 0, rgb.shape[0], 0, rgb.shape[1]
    while top < limit and is_frame(rgb[top, left:right]):
        top += 1
    while rgb.shape[0] - bottom < limit and is_frame(rgb[bottom - 1, left:right]):
        bottom -= 1
    while left < limit and is_frame(rgb[top:bottom, left]):
        left += 1
    while rgb.shape[1] - right < limit and is_frame(rgb[top:bottom, right - 1]):
        right -= 1
    return rgb[top:bottom, left:right]


def whiten_dark_background(rgb: np.ndarray) -> np.ndarray:
    """A black background turned white, keeping the line art's outer outline.

    The background is near-black, unsaturated colour reached from the edges. That also reaches
    the black outline it touches, so only the background further than an outline's width from the
    drawing turns white: the band left next to the drawing stays black and becomes the outline.
    Saturated dark colours (dark-purple hair) are never background. A light background is
    returned unchanged.
    """
    a = rgb.astype(int)
    hi, lo = a.max(2), a.min(2)
    dark = (hi <= 45) & (hi - lo <= 15)
    # Look a little inside the edge, past any frame remains.
    k = max(3, round(min(rgb.shape[:2]) * 0.02))
    ring = np.r_[dark[k, k:-k], dark[-k - 1, k:-k], dark[k:-k, k], dark[k:-k, -k - 1]]
    if ring.mean() < 0.5:
        return rgb
    # Frame remains where the drawing crosses the frame: any grey in the outer band is background.
    band = np.zeros_like(dark)
    band[:k, :] = band[-k:, :] = band[:, :k] = band[:, -k:] = True
    dark |= band & (hi - lo <= 15) & (hi < 235)
    outline = max(2, round(min(rgb.shape[:2]) / 110))  # about the line art's width
    # The line art connects every black shape (pupils...) to the background. Opening the mask
    # erases lines that thin, so only big black areas touching the edge count as background.
    wide = ndimage.binary_opening(dark, iterations=outline + 1, border_value=1)
    labels, _ = ndimage.label(wide)
    seeds = np.zeros_like(dark)
    seeds[: k + 1, :] = seeds[-k - 1 :, :] = seeds[:, : k + 1] = seeds[:, -k - 1 :] = True
    background = np.isin(labels, list(set(np.unique(labels[seeds & wide])) - {0}))
    far = ndimage.binary_erosion(background, iterations=outline, border_value=1)
    out = rgb.copy()
    out[far] = 255
    return out


def cutout(rgb: np.ndarray) -> Image.Image:
    """RGBA image with a baked-in checkerboard or white background removed.

    Background is light, unsaturated colour reached from the top and side edges. The bottom edge
    usually cuts through the body, so it only seeds from checkerboard grey there: a white shirt cut
    by the edge is not background. White faces are safe because their outline is closed.
    """
    framed = strip_frame(rgb)
    rgb = whiten_dark_background(framed)
    dark_background = rgb is not framed
    a = rgb.astype(int)
    lo, hi = a.min(2), a.max(2)
    light = (lo >= 185) & (hi - lo <= 18)
    grey = light & (hi <= 224)
    checker = grey.mean() > 0.04  # a plain white background has almost no mid-grey
    labels, n = ndimage.label(light)
    seeds = np.zeros_like(light)
    seeds[0, :] = seeds[:, 0] = seeds[:, -1] = True
    if checker:
        seeds[-1, :] = grey[-1, :]
    background = set(np.unique(labels[seeds & light])) - {0}
    if checker:  # enclosed pockets of checkerboard, e.g. between an arm and the body
        sizes = ndimage.sum(np.ones_like(labels), labels, range(1, n + 1))
        greys = ndimage.sum(grey, labels, range(1, n + 1))
        mixed = (sizes > 150) & (greys > 0.25 * sizes) & (greys < 0.75 * sizes)
        background |= set(np.flatnonzero(mixed) + 1)
    fg = ~np.isin(labels, list(background))
    parts, m = ndimage.label(fg)
    if m:
        sizes = ndimage.sum(fg, parts, range(1, m + 1))
        main = int(np.argmax(sizes)) + 1
        at_side = set(np.unique(np.r_[parts[:, 0], parts[:, -1]])) - {0}
        # Other pieces stay only if big and not cut by a side edge (those are neighbouring cells).
        keep = [main] + [
            i + 1
            for i in range(m)
            if i + 1 != main and sizes[i] >= 0.03 * sizes.max() and i + 1 not in at_side
        ]
        fg = np.isin(parts, keep)
    alpha = Image.fromarray((fg * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))
    img = Image.fromarray(np.dstack([rgb, np.asarray(alpha)]), "RGBA")
    img.info["dark_background"] = dark_background  # black shapes on it may have gone too
    return img


def load_cutout(path: Path) -> Image.Image:
    im = Image.open(path)
    if im.mode == "RGBA" and np.asarray(im)[..., 3].min() < 255:
        return im  # real transparency already
    return cutout(np.asarray(im.convert("RGB")))


def cells(path: Path, cols: int, rows: int) -> list[tuple[Image.Image, bool]]:
    """Each grid cell cut out, and whether the drawing touches the cell's top edge."""
    im = Image.open(path).convert("RGB")
    w, h = im.size
    out = []
    for r in range(rows):
        for c in range(cols):
            x0, x1 = round(c * w / cols), round((c + 1) * w / cols)
            y0, y1 = round(r * h / rows), round((r + 1) * h / rows)
            box = (x0, y0, x1, y1)
            cut = cutout(np.asarray(im.crop(box)))
            # The top few rows: a frame stripped above the drawing leaves them see-through.
            top = np.asarray(cut)[: max(3, round(cut.height * 0.02)), :, 3] > 127
            clipped = top.mean(1).max() > 0.02
            out.append((cut, clipped))
    return out


# --- alignment ------------------------------------------------------------------------------


def _mask(im: Image.Image, size: tuple[int, int]) -> np.ndarray:
    return np.asarray(im.getchannel("A").resize(size, Image.BILINEAR)) > 127


def align(ref: Image.Image, img: Image.Image) -> tuple[float, float, float]:
    """Scale and top-left offset (in ref pixels) that best lay img's head over ref's head.

    Brute force over scales; for each one, FFT correlation of ±1 alpha masks finds the offset.
    Only the head of the reference counts, so hands, cards and props don't pull the match.
    """
    k = MATCH / ref.width
    window = (_mask(ref, (MATCH, MATCH)).astype(float) * 2 - 1)[: int(MATCH * HEAD)]

    def score(s: float) -> tuple[float, tuple[float, float, float]]:
        w, h = max(8, round(img.width * s * k)), max(8, round(img.height * s * k))
        big = -np.ones((h + 2 * MATCH, w + 2 * MATCH))
        big[MATCH : MATCH + h, MATCH : MATCH + w] = _mask(img, (w, h)).astype(float) * 2 - 1
        corr = fftconvolve(big, window[::-1, ::-1], mode="valid")
        y, x = np.unravel_index(np.argmax(corr), corr.shape)
        return corr[y, x], (s, (MATCH - x) / k, (MATCH - y) / k)

    def best(scales) -> tuple[float, float, float]:
        return max((score(s) for s in scales), key=lambda r: r[0])[1]

    s0 = best(np.exp(np.linspace(np.log(0.1), np.log(4.0), 160)))[0]
    return best(np.linspace(s0 * 0.97, s0 * 1.03, 25))


def place(img: Image.Image, s: float, x: float, y: float, ref_width: int) -> Image.Image:
    """img drawn into the OUT×OUT frame, given its alignment to a ref of ref_width pixels."""
    f = OUT / ref_width
    scaled = img.resize((round(img.width * s * f), round(img.height * s * f)), Image.LANCZOS)
    frame = Image.new("RGBA", (OUT, OUT), (0, 0, 0, 0))
    frame.paste(scaled, (round(x * f), round(y * f)), scaled)
    return frame


def patch_top(img: Image.Image, top: float, neutral: Image.Image) -> Image.Image:
    """Rebuild a hat or hair top cut off by the gallery's cell edge from the neutral face.

    `top` is the y of the source cell's top edge in the frame. Above it (plus a margin past the
    edge's antialiasing) every variant shows the same hat, so the neutral's pixels win there.
    """
    y0 = round(top) + 8
    if y0 <= 0:
        return img
    strip = img.crop((0, 0, OUT, y0))
    strip.alpha_composite(neutral.crop((0, 0, OUT, y0)))
    out = img.copy()
    out.paste(strip, (0, 0))
    return out


def patch_body(img: Image.Image, neutral: Image.Image) -> Image.Image:
    """The body below the chin filled in from the neutral face, where the variant has none.

    On a black background, black shapes touching it (headphones, a dark jacket) are lost with it.
    Señas only change the face, so the neutral face's body is the right one.
    """
    chin = round(OUT * 0.7)
    body = neutral.crop((0, chin, OUT, OUT))
    body.alpha_composite(img.crop((0, chin, OUT, OUT)))
    out = img.copy()
    out.paste(body, (0, chin))
    return out


# --- commands -------------------------------------------------------------------------------


# --- mirrored señas ---------------------------------------------------------------------------


def symmetry_axis(img: Image.Image, rows: tuple[int, int]) -> float:
    """x of the vertical axis about which the face is most symmetric, in the given rows.

    The face outline and eyes dominate, so hair or a smirk off to one side barely move it.
    """
    a = np.asarray(img.convert("RGBA")).astype(float)
    band = (a[rows[0] : rows[1], :, :3].mean(2) * (a[rows[0] : rows[1], :, 3] / 255))[:, :]
    w = band.shape[1]
    best, axis = np.inf, w / 2
    for twice in range(round(w * 0.7), round(w * 1.3) + 1):  # axis = twice / 2, half-pixel steps
        half = min(twice // 2, w - (twice + 1) // 2, round(w * 0.3))
        left = band[:, twice // 2 - half : twice // 2]
        right = band[:, (twice + 1) // 2 : (twice + 1) // 2 + half][:, ::-1]
        err = np.abs(left - right).mean()
        if err < best:
            best, axis = err, twice / 2
    return axis


def mirror_box(
    img: Image.Image, boxes: list[tuple[int, ...]], axis: float, exact: bool = False
) -> Image.Image:
    """img with the boxes (widened to be symmetric about the axis) replaced by their reflection.

    Several boxes let the region bend around an eye. The edge is feathered so the reflected skin
    blends into the untouched one.
    """
    a = np.asarray(img.convert("RGBA")).astype(float)
    h, w = a.shape[:2]
    xs = np.clip(np.round(2 * axis - np.arange(w)).astype(int), 0, w - 1)
    flipped = a[:, xs]
    mask = np.zeros((h, w), np.uint8)
    for x0, y0, x1, y1 in boxes:
        if not exact:
            reach = max(axis - x0, x1 - axis)
            x0, x1 = round(axis - reach), round(axis + reach) + 1
        mask[y0:y1, max(0, x0) : min(w, x1)] = 255
    soft = np.asarray(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(4))) / 255.0
    out = a * (1 - soft[..., None]) + flipped * soft[..., None]
    return Image.fromarray(out.round().astype(np.uint8), "RGBA")


def erase_box(img: Image.Image, box: tuple[int, ...]) -> Image.Image:
    """The box painted over with the median colour of the ring around it (the skin there).

    For stray bits of the old expression the mirror leaves behind, such as an eyelash stub.
    """
    a = np.asarray(img.convert("RGBA")).astype(float)
    x0, y0, x1, y1 = box
    sides = [
        a[y0 - 3 : y0, x0:x1],
        a[y1 : y1 + 3, x0:x1],
        a[y0:y1, x0 - 3 : x0],
        a[y0:y1, x1 : x1 + 3],
    ]
    colour = np.median(np.concatenate([side.reshape(-1, 4) for side in sides]), axis=0)
    mask = np.zeros(a.shape[:2], np.uint8)
    mask[y0:y1, x0:x1] = 255
    soft = np.asarray(Image.fromarray(mask).filter(ImageFilter.GaussianBlur(2))) / 255.0
    out = a * (1 - soft[..., None]) + colour * soft[..., None]
    return Image.fromarray(out.round().astype(np.uint8), "RGBA")


def mirror_cmd(
    character: str,
    source: Path,
    sena: str,
    boxes: list[tuple[int, ...]],
    exact: bool,
    erase: list[tuple[int, ...]],
) -> None:
    neutral = Image.open(AVATARS / "approved" / character / "base.png").convert("RGBA")
    src = Image.open(source).convert("RGBA")
    if src.size != (OUT, OUT):  # a raw cutout: put it in the character's frame first
        s, x, y = align(neutral, src)
        src = place(src, s, x, y, neutral.width)
    top, bottom = min(b[1] for b in boxes), max(b[3] for b in boxes)
    axis = symmetry_axis(src, (max(0, top - 60), min(OUT, bottom + 60)))
    result = mirror_box(src, boxes, axis, exact)
    for box in erase:
        result = erase_box(result, box)
    out = AVATARS / "candidates" / character
    out.mkdir(parents=True, exist_ok=True)
    result.save(out / f"{sena}-mirrored.png")
    marked = src.copy()
    draw = ImageDraw.Draw(marked)
    for x0, y0, x1, y1 in boxes:
        if not exact:
            reach = max(axis - x0, x1 - axis)
            x0, x1 = axis - reach, axis + reach
        draw.rectangle((x0, y0, x1, y1), outline="#f4d35e", width=3)
    draw.line((axis, 0, axis, OUT), fill="#f4d35e", width=1)
    review_sheet(
        [("neutral", neutral), ("source + box", marked), (f"{sena} mirrored", result)],
        out / f"{sena}-mirrored-review.png",
    )
    print(f"axis x={axis:.1f}; wrote {out / f'{sena}-mirrored.png'} and its review sheet")


def review_sheet(images: list[tuple[str, Image.Image]], path: Path) -> None:
    """Each image at 200 px and at the table's 80 px, on felt green."""
    sheet = Image.new("RGB", (200 * len(images), 300), "#1f5130")
    draw = ImageDraw.Draw(sheet)
    for k, (label, im) in enumerate(images):
        big, small = im.resize((200, 200), Image.LANCZOS), im.resize((80, 80), Image.LANCZOS)
        sheet.paste(big, (k * 200, 20), big)
        sheet.paste(small, (k * 200 + 60, 220), small)
        draw.text((k * 200 + 6, 4), label, fill="#f4d35e")
    sheet.save(path)


def init(character: str, base: Path, sheet: Path, ref_cell: int, grid: tuple[int, int]) -> None:
    ref, _ = cells(sheet, *grid)[ref_cell - 1]
    portrait = load_cutout(base)
    out = AVATARS / "approved" / character
    out.mkdir(parents=True, exist_ok=True)
    s, x, y = align(ref, portrait)
    place(portrait, s, x, y, ref.width).save(out / "base.png")
    portrait.crop(portrait.getbbox()).save(out / "portrait.png")
    print(f"wrote {out / 'base.png'} and portrait.png (scale {s:.3f})")


def sheet_cmd(character: str, sheet: Path, grid: tuple[int, int]) -> None:
    neutral = Image.open(AVATARS / "approved" / character / "base.png").convert("RGBA")
    out = AVATARS / "candidates" / character
    out.mkdir(parents=True, exist_ok=True)
    shown = [("neutral", neutral)]
    for i, (cut, clipped) in enumerate(cells(sheet, *grid), start=1):
        s, x, y = align(neutral, cut)
        framed = place(cut, s, x, y, neutral.width)
        fixes = []
        if clipped:
            framed = patch_top(framed, y * OUT / neutral.width, neutral)
            fixes.append("top rebuilt")
        if cut.info["dark_background"]:
            framed = patch_body(framed, neutral)
            fixes.append("body from neutral")
        framed.save(out / f"{sheet.stem}-cell{i}.png")
        shown.append((f"cell {i}", framed))
        print(f"cell {i}: scale {s:.3f}" + (f" ({', '.join(fixes)})" if fixes else ""))
        if (np.asarray(cut)[..., 3] > 127).mean() > 0.9:
            # White, checkerboard and black backgrounds are recognised; anything else isn't.
            print(f"  warning: cell {i} has no background left to remove")
    review_sheet(shown, out / f"{sheet.stem}-review.png")
    print(f"candidates and review sheet in {out}")


def main() -> None:
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest="cmd", required=True)
    grid = {
        "type": lambda g: tuple(int(n) for n in g.split("x")),
        "default": (3, 3),
        "help": "COLSxROWS",
    }
    a = sub.add_parser("init", help="start a character from its base image and a first gallery")
    a.add_argument("character")
    a.add_argument("--base", type=Path, required=True)
    a.add_argument("--sheet", type=Path, required=True)
    a.add_argument("--ref-cell", type=int, default=REF_CELL)
    a.add_argument("--grid", **grid)
    b = sub.add_parser("sheet", help="cut out and align a gallery's cells as candidates")
    b.add_argument("character")
    b.add_argument("sheet", type=Path)
    b.add_argument("--grid", **grid)
    c = sub.add_parser("mirror", help="a seña's mirror image (03 from 04, 02 from a wrong wink)")
    c.add_argument("character")
    c.add_argument("source", type=Path)
    c.add_argument("sena", help="name of the result, e.g. sena_03")
    c.add_argument(
        "--box",
        required=True,
        action="append",
        type=lambda b: tuple(int(n) for n in b.split(",")),
        help="X0,Y0,X1,Y1 in the 512 frame around the mouth or eyes; repeat to combine boxes",
    )
    c.add_argument(
        "--exact",
        action="store_true",
        help="use the boxes as given, without widening them to be symmetric (one box per eye, "
        "to keep an asymmetric detail such as a hair strand out)",
    )
    c.add_argument(
        "--erase",
        action="append",
        default=[],
        type=lambda b: tuple(int(n) for n in b.split(",")),
        help="X0,Y0,X1,Y1 to paint with the surrounding skin after mirroring (leftover strokes)",
    )
    args = p.parse_args()
    if args.cmd == "init":
        init(args.character, args.base, args.sheet, args.ref_cell, args.grid)
    elif args.cmd == "sheet":
        sheet_cmd(args.character, args.sheet, args.grid)
    else:
        mirror_cmd(args.character, args.source, args.sena, args.box, args.exact, args.erase)


if __name__ == "__main__":
    main()
