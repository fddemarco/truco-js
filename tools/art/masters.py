# /// script
# requires-python = ">=3.12"
# dependencies = ["pillow>=11", "numpy>=2", "scipy>=1.14", "potracer>=0.0.4"]
# ///
"""Rebuild an avatar's neutral face as a layered vector master, and draw its señas from it.

Only the base image is used as reference: the señas are derived from the master, so all nine
images share the outfit, colours and framing, and only the seña moves.

    uv run tools/art/masters.py grid <character>
        A labelled 10 px grid over the base, for writing the character's config.
    uv run tools/art/masters.py build <character>|all
        Trace the base into assets/work/masters/<character>/master.svg (and masks.png, which
        shows what was cut out as face parts and what stays in front of them).
    uv run tools/art/masters.py render <character>|all
        Export the base and the eight señas from master.svg to png/, plus review.png.
    uv run tools/art/masters.py install <character>|all
        Copy png/ into assets/avatars/<character>/ (base and señas; the portrait is kept).

`build` reads assets/sources/<character>/base.png, the image model's neutral face, so a
rebuilt base never gets traced again (the first build copies it there from assets/avatars).
Re-running `build` overwrites master.svg; hand edits made in Inkscape survive a `render`.

master.svg has three Inkscape layers:
  body   the hair, head outline, clothes and props, traced into flat colours (the model's
         noise and gradients are dropped);
  face   one group per face part (brows, eyes, mouth, and any extras such as blush), traced
         from the base. Each part holds a `<part>.base` group and one `<part>.<seña>` group
         per seña that changes it; `render` shows the seña's group where it has one;
  front  a clone of the body clipped to what sits over the face (glasses, a moustache, a hair
         strand), so the parts move under it.

The señas (Anexo C.2; right and left are the image's sides, see docs/art-prompts.md):
  01 brows up, eyes a little wider     02 wink: the eye on the image's LEFT closes
  03 mouth corner on the LEFT goes out and up       04 the same on the RIGHT
  05 bites the lower lip   06 puckered lips   07 mouth slightly open
  12 nose wrinkled: creases on the bridge, eyes squeezed from below, brows down and in

Each character has a config, tools/art/masters/<character>.toml (see tiburon.toml): the boxes
or polygons of its face parts, the shapes in front of them, and optional seña tuning.
"""

import argparse
import math
import shutil
import subprocess
import tomllib
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import potrace
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage
from scipy.cluster.vq import kmeans2

ROOT = Path(__file__).resolve().parents[2]
ASSETS = ROOT / "assets"
CONFIGS = Path(__file__).parent / "masters"
SIZE = 512
SS = 4  # trace at 4x for smooth curves
SENAS = ["01", "02", "03", "04", "05", "06", "07", "12"]
NS = {
    "svg": "http://www.w3.org/2000/svg",
    "inkscape": "http://www.inkscape.org/namespaces/inkscape",
    "xlink": "http://www.w3.org/1999/xlink",
}
for prefix, uri in NS.items():
    ET.register_namespace("" if prefix == "svg" else prefix, uri)


def work(character: str) -> Path:
    return ASSETS / "work" / "masters" / character


def config(character: str) -> dict:
    return tomllib.loads((CONFIGS / f"{character}.toml").read_text())


def characters() -> list[str]:
    return sorted(p.stem for p in CONFIGS.glob("*.toml"))


def hexcolour(c) -> str:
    return "#%02x%02x%02x" % tuple(int(round(v)) for v in c)


def rgb(h: str) -> np.ndarray:
    return np.array([int(h[i : i + 2], 16) for i in (1, 3, 5)], float)


# ---- shapes from the config ---------------------------------------------------------------


def shape_mask(spec: dict) -> np.ndarray:
    """Union of the shapes in spec: box, polygon, ellipse ([x0,y0,x1,y1]) or ring
    ([cx,cy,rx,ry,width]); each key takes one shape or a list. `minus` subtracts a spec."""
    m = Image.new("L", (SIZE, SIZE), 0)
    d = ImageDraw.Draw(m)

    def many(key, depth):  # one shape or a list of shapes
        v = spec.get(key)
        return [] if v is None else v if _depth(v) > depth else [v]

    for box in many("box", 1):
        d.rectangle(box, fill=255)
    for poly in many("polygon", 2):
        d.polygon([tuple(p) for p in poly], fill=255)
    for ell in many("ellipse", 1):
        d.ellipse(ell, fill=255)
    for cx, cy, rx, ry, w in many("ring", 1):
        d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=255, width=int(round(w)))
    out = np.asarray(m) > 0
    if "minus" in spec:
        out &= ~shape_mask(spec["minus"])
    return out


def _depth(v) -> int:
    return 1 + _depth(v[0]) if isinstance(v, list) and v else 0


# ---- palette and tracing ------------------------------------------------------------------


def palette(img: np.ndarray, cfg: dict) -> np.ndarray:
    """Flat colours of the base: k-means over pixels away from edges (no anti-aliasing),
    near-duplicates merged, plus any colours the config adds. Lightest first."""
    rgbf = img[..., :3].astype(float)
    opaque = img[..., 3] > 128
    mean = ndimage.uniform_filter(rgbf, size=(3, 3, 1))
    var = ndimage.uniform_filter(rgbf**2, size=(3, 3, 1)) - mean**2
    flat = opaque & (np.sqrt(np.clip(var, 0, None)).max(-1) < 6)
    px = rgbf[flat]
    rng = np.random.default_rng(0)
    px = px[rng.choice(len(px), min(len(px), 40000), replace=False)]
    centres, labels = kmeans2(px, cfg.get("colours", 24), seed=1, minit="++")
    counts = np.bincount(labels, minlength=len(centres))
    keep: list[np.ndarray] = []
    for i in np.argsort(-counts):
        if counts[i] < 12:
            continue
        if all(_distance(centres[i], k) > cfg.get("merge", 28) for k in keep):
            keep.append(centres[i])
    keep += [rgb(h) for h in cfg.get("add_colours", [])]
    pal = np.array(keep)
    return pal[np.argsort(-pal.sum(1))]


def _distance(a: np.ndarray, b: np.ndarray) -> float:
    """Colour distance that counts hue: greys of different lightness merge before a pink
    and a grey of the same lightness do."""
    chroma = lambda c: c - c.mean()  # noqa: E731
    return float(np.abs(a - b).sum() + 2 * np.abs(chroma(a) - chroma(b)).sum())


def snap(rgbf: np.ndarray, pal: np.ndarray) -> np.ndarray:
    return ((rgbf[..., None, :] - pal[None, None]) ** 2).sum(-1).argmin(-1)


Path_ = list  # a traced shape: [(start, [segment, ...]), ...]; a segment is ("L", p) or ("C", p1, p2, p3)


def trace(mask: np.ndarray, sigma: float, speck: float) -> Path_:
    """Smooth the mask at SS× and trace it; points in frame coordinates."""
    big = np.asarray(
        Image.fromarray((mask * 255).astype(np.uint8)).resize((SIZE * SS,) * 2, Image.BICUBIC)
    ).astype(float)
    big = ndimage.gaussian_filter(big, SS * sigma) > 127
    if not big.any():
        return []
    curves = potrace.Bitmap(~big).trace(  # potracer traces the False pixels
        turdsize=int(speck * SS * SS), alphamax=1.0, opttolerance=0.4
    )
    pt = lambda p: (p.x / SS, p.y / SS)  # noqa: E731
    out = []
    for c in curves:
        segs = []
        for s in c.segments:
            if s.is_corner:
                segs += [("L", pt(s.c)), ("L", pt(s.end_point))]
            else:
                segs.append(("C", pt(s.c1), pt(s.c2), pt(s.end_point)))
        out.append((pt(c.start_point), segs))
    return out


def d_attr(shape: Path_, warp=None) -> str:
    f = warp or (lambda x, y: (x, y))

    def p(q):
        x, y = f(*q)
        return f"{x:.2f},{y:.2f}"

    parts = []
    for start, segs in shape:
        s = [f"M{p(start)}"]
        for seg in segs:
            s.append(f"L{p(seg[1])}" if seg[0] == "L" else f"C{p(seg[1])} {p(seg[2])} {p(seg[3])}")
        parts.append(" ".join(s) + "Z")
    return " ".join(parts)


@dataclass
class Layer:
    colour: str
    shape: Path_


def trace_layers(
    labels: np.ndarray, region: np.ndarray, pal: np.ndarray, sigma, speck, skip=()
) -> list[Layer]:
    """Stacked colour layers: each covers its own pixels and every darker one's, so no gaps
    open between colours. `sigma`/`speck` may be callables of the colour index."""
    used = [i for i in range(len(pal)) if i not in skip and (region & (labels == i)).any()]
    layers = []
    for n, i in enumerate(used):
        m = region & np.isin(labels, used[n:])
        sg = sigma(i) if callable(sigma) else sigma
        sp = speck(i) if callable(speck) else speck
        shape = trace(m, sg, sp)
        if shape:
            layers.append(Layer(hexcolour(pal[i]), shape))
    return layers


def paths_svg(layers: list[Layer], indent: str, warp=None) -> str:
    return "\n".join(
        f'{indent}<path fill="{ly.colour}" fill-rule="evenodd" d="{d_attr(ly.shape, warp)}"/>'
        for ly in layers
    )


# ---- build --------------------------------------------------------------------------------


@dataclass
class Part:
    name: str
    mask: np.ndarray
    layers: list[Layer]

    @property
    def box(self) -> tuple[float, float, float, float]:
        ys, xs = np.nonzero(self.mask)
        return xs.min(), ys.min(), xs.max() + 1, ys.max() + 1


def source(character: str) -> Path:
    src = ASSETS / "sources" / character / "base.png"
    if not src.exists():
        src.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ASSETS / "avatars" / character / "base.png", src)
        print(f"copied the current base to {src.relative_to(ROOT)} (the source from now on)")
    return src


def build(character: str) -> None:
    cfg = config(character)
    out = work(character)
    out.mkdir(parents=True, exist_ok=True)
    img = np.asarray(Image.open(source(character)).convert("RGBA").resize((SIZE, SIZE)))
    rgbf = img[..., :3].astype(float)
    opaque = img[..., 3] > 128
    pal = palette(img, cfg)
    labels = snap(rgbf, pal)
    regions = {name: shape_mask(spec) for name, spec in cfg["parts"].items()}
    anyregion = np.logical_or.reduce(list(regions.values()))
    if "skin" in cfg:
        skin = rgb(cfg["skin"])
    else:  # the commonest colour around the face parts
        skin = pal[np.bincount(labels[anyregion & opaque], minlength=len(pal)).argmax()]
    skin_i = int(np.abs(pal - skin).sum(1).argmin())
    ink_i = int(pal.sum(1).argmin())
    nonskin = opaque & (np.abs(rgbf - skin).sum(-1) > cfg.get("threshold", 60))

    front = np.zeros_like(opaque)
    for spec in cfg.get("front", {}).values():
        front |= shape_mask(spec)
    front &= ndimage.binary_dilation(nonskin, iterations=1)

    parts = []
    removed = np.zeros_like(opaque)
    for name, region in regions.items():
        m = ndimage.binary_dilation(nonskin & region, iterations=1) & region & ~front
        parts.append(Part(name, m, []))
        removed |= ndimage.binary_dilation(m, iterations=2) & region & ~front
    plate = rgbf.copy()
    plate[removed] = skin

    plabels = snap(plate, pal)
    plabels_fill = ndimage.median_filter(plabels, size=5)
    plabels = ndimage.median_filter(plabels, size=3)
    body = []
    used = [i for i in range(len(pal)) if (opaque & (plabels_fill == i)).any() or i == ink_i]
    for n, i in enumerate(used):
        line = i == ink_i
        src_l = plabels if line else plabels_fill
        m = opaque & np.isin(src_l, used[n:])
        if not line:
            m |= opaque & (plabels == ink_i)
        shape = trace(m, 0.6 if line else cfg.get("smooth", 1.2), 10 if line else 30)
        if shape:
            body.append(Layer(hexcolour(pal[i]), shape))

    part_labels = snap(rgbf, pal)
    for p in parts:
        p.layers = trace_layers(part_labels, p.mask, pal, 0.5, 3, skip={skin_i})
        p.mask &= part_labels != skin_i
    front_shape = trace(front, 0.4, 2)

    ink = hexcolour(pal[ink_i])
    svg = master_svg(cfg, body, parts, front_shape, ink, hexcolour(skin))
    (out / "master.svg").write_text(svg)
    masks_review(img, parts, front, out / "masks.png")
    print(f"{character}: palette {len(pal)} colours, skin {hexcolour(skin)}, ink {ink}")
    print(f"  wrote {(out / 'master.svg').relative_to(ROOT)} and masks.png")


def masks_review(img, parts, front, path: Path) -> None:
    viz = img[..., :3].copy()
    viz[img[..., 3] < 128] = 200
    cols = [(230, 0, 0), (0, 150, 0), (0, 60, 230), (200, 0, 200), (240, 130, 0), (0, 170, 170)]
    for i, p in enumerate(parts):
        viz[p.mask] = cols[i % len(cols)]
    viz[front] = (viz[front] * 0.4 + np.array([255, 220, 0]) * 0.6).astype(np.uint8)
    Image.fromarray(viz).resize((SIZE * 2,) * 2, Image.NEAREST).save(path)


# ---- señas --------------------------------------------------------------------------------


def group(gid: str, body: str, transform: str = "", hidden: bool = True) -> str:
    t = f' transform="{transform}"' if transform else ""
    style = ' style="display:none"' if hidden else ""
    label = gid.split(".", 1)[1]
    return f'      <g id="{gid}" inkscape:label="{label}"{t}{style}>\n{body}\n      </g>'


def master_svg(cfg, body, parts, front_shape, ink, skin) -> str:
    s = cfg.get("senas", {})
    line = s.get("line", 3.5)
    by = {p.name: p for p in parts}
    eyes = [by[n] for n in ("eye-L", "eye-R") if n in by]
    brows = [by[n] for n in ("brow-L", "brow-R") if n in by]
    eye_h = np.mean([p.box[3] - p.box[1] for p in eyes]) if eyes else 20
    lift = s.get("lift", round(0.35 * eye_h, 1))
    ind = "        "
    face = []

    def nose_part() -> str:
        if "nose" in s:
            nx, ny = s["nose"]
        else:
            nx = np.mean([(p.box[0] + p.box[2]) / 2 for p in eyes])
            ny = np.mean([p.box[1] for p in eyes]) + 0.15 * eye_h
        k = s.get("nose_scale", 1.0)
        strokes = []
        for side in (-1, 1):
            for j in range(3):
                y = ny + j * 4.2 * k
                x0, x1 = nx + side * 2.5 * k, nx + side * (11 - j) * k
                strokes.append(
                    f'<path d="M{x0:.1f},{y + 1.2 * k:.1f} Q{(x0 + x1) / 2:.1f},{y - 2 * k:.1f} '
                    f'{x1:.1f},{y + 0.8 * k:.1f}"/>'
                )
        body_ = (
            f'{ind}<g fill="none" stroke="{ink}" stroke-width="{line * 0.5:.2f}" '
            f'stroke-linecap="round">\n{ind}  ' + f"\n{ind}  ".join(strokes) + f"\n{ind}</g>"
        )
        return f'    <g id="nose" inkscape:label="nose">\n{group("nose.12", body_)}\n    </g>'

    for p in parts:
        base = paths_svg(p.layers, ind)
        x0, y0, x1, y1 = p.box
        cx, cy, w, h = (x0 + x1) / 2, (y0 + y1) / 2, x1 - x0, y1 - y0
        variants = [group(f"{p.name}.base", base, hidden=False)]
        if p.name in ("brow-L", "brow-R"):
            variants.append(group(f"{p.name}.01", base, f"translate(0,{-lift})"))
            ox = x0 if p.name == "brow-L" else x1
            ang = s.get("frown", 9) * (1 if p.name == "brow-L" else -1)
            variants.append(
                group(
                    f"{p.name}.12",
                    base,
                    f"translate(0,{0.4 * lift:.1f}) rotate({ang},{ox:.1f},{cy:.1f})",
                )
            )
        elif p.name in ("eye-L", "eye-R"):
            k = s.get("widen", 1.12)
            variants.append(
                group(
                    f"{p.name}.01", base, f"translate(0,{cy * (1 - k):.2f}) scale(1,{k})"
                )
            )
            q = s.get("squeeze", 0.78)
            variants.append(
                group(f"{p.name}.12", base, f"translate(0,{y0 * (1 - q):.2f}) scale(1,{q})")
            )
            if p.name == "eye-L":
                variants.append(group("eye-L.02", wink(p, s, ink, line, ind)))
        elif p.name == "mouth":
            mw = s.get("mouth_size", min(w, 58))
            mx, my = s.get("mouth_at", [cx, cy])
            for seña, side in (("03", -1), ("04", 1)):
                variants.append(group(f"mouth.{seña}", paths_svg(p.layers, ind, smirk(p, side, s))))
            colours = dict(ink=ink, lip=s.get("lip", "#e07f84"), line=line, ind=ind)
            variants.append(group("mouth.05", bite(mx, my, mw, **colours)))
            variants.append(group("mouth.06", pucker(mx, my, mw, **colours)))
            variants.append(group("mouth.07", open_mouth(mx, my, mw, **colours)))
        face.append(
            f'    <g id="{p.name}" inkscape:label="{p.name}">\n' + "\n".join(variants) + "\n    </g>"
        )
        if p.name == "eye-R" or (p.name == "eye-L" and "eye-R" not in by):
            face.append(nose_part())
    if not any(p.name.startswith("eye") for p in parts):
        face.append(nose_part())

    clip = f'<clipPath id="front-clip"><path d="{d_attr(front_shape)}"/></clipPath>' if front_shape else ""
    front = (
        '<use xlink:href="#body" clip-path="url(#front-clip)"/>' if front_shape else ""
    )
    return f"""<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="{SIZE}" height="{SIZE}" viewBox="0 0 {SIZE} {SIZE}" data-skin="{skin}">
  <defs>{clip}</defs>
  <g id="body" inkscape:groupmode="layer" inkscape:label="body">
{paths_svg(body, "    ")}
  </g>
  <g id="face" inkscape:groupmode="layer" inkscape:label="face">
{chr(10).join(face)}
  </g>
  <g id="front" inkscape:groupmode="layer" inkscape:label="front">
    {front}
  </g>
</svg>
"""


def wink(p: Part, s: dict, ink: str, line: float, ind: str) -> str:
    """A closed eye: a tapered arc bowed downwards, with a small lash at the outer end."""
    x0, y0, x1, y1 = p.box
    cx = (x0 + x1) / 2 + s.get("wink_dx", 0)
    ww = s.get("wink_width", 0.8 * (x1 - x0))
    y = s.get("wink_y", y0 + 0.5 * (y1 - y0))
    bow, t = 0.2 * ww, line * 1.3
    a, b = cx - ww / 2, cx + ww / 2
    lash = (
        f'<path d="M{a + 2:.1f},{y + 1:.1f} L{a - 0.1 * ww:.1f},{y - 0.08 * ww:.1f}" '
        f'stroke="{ink}" stroke-width="{line * 0.8:.2f}" stroke-linecap="round"/>'
    )
    return (
        f'{ind}<path fill="{ink}" d="M{a:.1f},{y:.1f} Q{cx:.1f},{y + bow + t:.1f} {b:.1f},{y:.1f} '
        f'Q{cx:.1f},{y + bow - t * 0.2:.1f} {a:.1f},{y:.1f} Z" stroke="{ink}" '
        f'stroke-width="{line * 0.6:.2f}" stroke-linejoin="round"/>\n{ind}{lash}'
    )


def smirk(p: Part, side: int, s: dict):
    """Warp the mouth so its corner on `side` (-1 image left, +1 right) goes out and up."""
    x0, y0, x1, y1 = p.box
    cx, half = (x0 + x1) / 2, (x1 - x0) / 2
    out_, up = s.get("corner", [0.16, 0.2])
    slide = 0.06 * half * 2

    def f(x, y):
        u = min(max((x - cx) * side / half, 0), 1.2)
        wgt = u * u
        return x + side * (slide + out_ * half * 2 * wgt * 0.5), y - up * half * wgt

    return f


def _g(ind, body):
    return f"{ind}" + f"\n{ind}".join(body)


def bite(x, y, s, ink, lip, line, ind):
    """Upper teeth resting on the lower lip."""
    return _g(
        ind,
        [
            f'<path d="M{x - 0.27 * s:.1f},{y + 0.1 * s:.1f} Q{x:.1f},{y + 0.36 * s:.1f} '
            f'{x + 0.27 * s:.1f},{y + 0.1 * s:.1f} Q{x:.1f},{y + 0.2 * s:.1f} '
            f'{x - 0.27 * s:.1f},{y + 0.1 * s:.1f} Z" fill="{lip}" stroke="{ink}" '
            f'stroke-width="{line * 0.5:.2f}" stroke-linejoin="round"/>',
            f'<path d="M{x - 0.19 * s:.1f},{y + 0.02 * s:.1f} L{x - 0.17 * s:.1f},{y + 0.15 * s:.1f} '
            f'Q{x:.1f},{y + 0.19 * s:.1f} {x + 0.17 * s:.1f},{y + 0.15 * s:.1f} '
            f'L{x + 0.19 * s:.1f},{y + 0.02 * s:.1f} Z" fill="#ffffff" stroke="{ink}" '
            f'stroke-width="{line * 0.4:.2f}" stroke-linejoin="round"/>',
            f'<path d="M{x:.1f},{y + 0.03 * s:.1f} L{x:.1f},{y + 0.16 * s:.1f}" stroke="{ink}" '
            f'stroke-width="{line * 0.3:.2f}"/>',
            f'<path d="M{x - 0.38 * s:.1f},{y - 0.02 * s:.1f} Q{x:.1f},{y + 0.06 * s:.1f} '
            f'{x + 0.38 * s:.1f},{y - 0.02 * s:.1f}" fill="none" stroke="{ink}" '
            f'stroke-width="{line:.2f}" stroke-linecap="round"/>',
        ],
    )


def pucker(x, y, s, ink, lip, line, ind):
    """Small round kiss lips, pushed forward."""
    return _g(
        ind,
        [
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{0.15 * s:.1f}" ry="{0.13 * s:.1f}" '
            f'fill="{lip}" stroke="{ink}" stroke-width="{line * 0.8:.2f}"/>',
            f'<path d="M{x - 0.07 * s:.1f},{y:.1f} Q{x:.1f},{y - 0.03 * s:.1f} {x + 0.07 * s:.1f},{y:.1f} '
            f'Q{x:.1f},{y + 0.03 * s:.1f} {x - 0.07 * s:.1f},{y:.1f} Z" fill="{ink}"/>',
            f'<ellipse cx="{x - 0.06 * s:.1f}" cy="{y - 0.07 * s:.1f}" rx="{0.03 * s:.1f}" '
            f'ry="{0.018 * s:.1f}" fill="#ffffff" opacity="0.8"/>',
        ],
    )


def open_mouth(x, y, s, ink, lip, line, ind):
    """A small relaxed oval, as if about to speak."""
    rx, ry = 0.2 * s, 0.13 * s
    return _g(
        ind,
        [
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="#6b2a30"/>',
            f'<path d="M{x - 0.7 * rx:.1f},{y + 0.62 * ry:.1f} Q{x:.1f},{y - 0.1 * ry:.1f} '
            f'{x + 0.7 * rx:.1f},{y + 0.62 * ry:.1f} Q{x:.1f},{y + 1.05 * ry:.1f} '
            f'{x - 0.7 * rx:.1f},{y + 0.62 * ry:.1f} Z" fill="{lip}"/>',
            f'<ellipse cx="{x:.1f}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="none" '
            f'stroke="{ink}" stroke-width="{line * 0.8:.2f}"/>',
        ],
    )


# ---- render -------------------------------------------------------------------------------


def render(character: str) -> None:
    out = work(character)
    tree = ET.parse(out / "master.svg")
    vdir, pdir = out / "variants", out / "png"
    vdir.mkdir(exist_ok=True)
    pdir.mkdir(exist_ok=True)
    face = tree.getroot().find(".//svg:g[@id='face']", NS)
    names = ["base"] + [f"sena_{s}" for s in SENAS]
    files = []
    for name in names:
        seña = name.removeprefix("sena_")
        for part in face.findall("svg:g", NS):
            kids = {k.get("id").split(".", 1)[1]: k for k in part.findall("svg:g", NS)}
            show = seña if seña in kids else "base"
            for key, k in kids.items():
                if key == show:
                    k.attrib.pop("style", None)
                else:
                    k.set("style", "display:none")
        f = vdir / f"{name}.svg"
        tree.write(f, xml_declaration=True, encoding="utf-8")
        files.append(f)
    subprocess.run(
        ["inkscape", "--export-type=png", f"--export-width={SIZE}", f"--export-height={SIZE}"]
        + [str(f) for f in files],
        check=True,
        capture_output=True,
    )
    for f in files:
        f.with_suffix(".png").replace(pdir / f.with_suffix(".png").name)
    review(character, names)
    print(f"{character}: rendered {len(names)} images to {pdir.relative_to(ROOT)}; review.png")


def review(character: str, names: list[str]) -> None:
    """Every image at 200 px and at the table's 80 px, after the source base."""
    out = work(character)
    tiles = [("source", Image.open(source(character)).convert("RGBA"))] + [
        (n, Image.open(out / "png" / f"{n}.png").convert("RGBA")) for n in names
    ]
    font = ImageFont.load_default()
    w, big, small = len(tiles) * 204, 200, 80
    sheet = Image.new("RGB", (w, 16 + big + 8 + small + 8), (200, 208, 216))
    d = ImageDraw.Draw(sheet)
    for i, (label, im) in enumerate(tiles):
        x = i * 204 + 2
        d.text((x + 4, 2), label, fill=(0, 0, 0), font=font)
        sheet.paste(im.resize((big, big), Image.LANCZOS), (x, 16), im.resize((big, big), Image.LANCZOS))
        sm = im.resize((small, small), Image.LANCZOS)
        sheet.paste(sm, (x + 60, 16 + big + 8), sm)
    sheet.save(out / "review.png")


# ---- grid and install ---------------------------------------------------------------------


def grid(character: str) -> None:
    out = work(character)
    out.mkdir(parents=True, exist_ok=True)
    im = Image.open(source(character)).convert("RGBA")
    bg = Image.new("RGBA", im.size, (255, 255, 255, 255))
    im = Image.alpha_composite(bg, im).convert("RGB").resize((SIZE * 3,) * 2, Image.NEAREST)
    d = ImageDraw.Draw(im)
    for v in range(0, SIZE, 10):
        c = (0, 90, 255) if v % 50 == 0 else (120, 170, 255)
        d.line([(v * 3, 0), (v * 3, SIZE * 3)], fill=c, width=1)
        d.line([(0, v * 3), (SIZE * 3, v * 3)], fill=c, width=1)
    for v in range(0, SIZE, 50):
        for u in range(0, SIZE, 50):
            d.text((v * 3 + 2, u * 3 + 2), f"{v},{u}", fill=(220, 0, 0))
    im.save(out / "grid.png")
    print(f"wrote {(out / 'grid.png').relative_to(ROOT)} (3x; lines every 10 px)")


def install(character: str) -> None:
    pdir = work(character) / "png"
    dest = ASSETS / "avatars" / character
    backup = ASSETS / "work" / "masters" / "backup" / character
    if not backup.exists():
        shutil.copytree(dest, backup)
        print(f"backed up {dest.relative_to(ROOT)} to {backup.relative_to(ROOT)}")
    for f in sorted(pdir.glob("*.png")):
        shutil.copy(f, dest / f.name)
    print(f"{character}: installed {len(list(pdir.glob('*.png')))} images into {dest.relative_to(ROOT)}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", choices=["grid", "build", "render", "install"])
    ap.add_argument("character", help="a character with a config in tools/art/masters/, or all")
    a = ap.parse_args()
    run = {"grid": grid, "build": build, "render": render, "install": install}[a.command]
    for c in characters() if a.character == "all" else [a.character]:
        run(c)


if __name__ == "__main__":
    main()
