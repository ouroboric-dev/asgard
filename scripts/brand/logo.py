"""Logo processing (brand tools spec §5.3): trace the founder's PNGs, check the trace, recolour it with the palette,
derive the missing mode, and export the favicons and app icons. Run by brand.sh logo; writes only in the logo folder.

    logo.py --resvg PATH DIR
"""
import argparse
import hashlib
import json
import math
import os
import re
import struct
import subprocess
import sys
import tempfile

import vtracer
from PIL import Image, ImageChops, ImageDraw, ImageFilter

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
PARAMS = {"colormode": "color", "hierarchical": "stacked", "mode": "spline", "filter_speckle": 4,
          "color_precision": 6, "layer_difference": 16, "corner_threshold": 60, "length_threshold": 4.0,
          "max_iterations": 10, "splice_threshold": 45, "path_precision": 3}
VTRACER_VERSION = "0.6.15"
SHAPE_LIMIT, COLOUR_LIMIT, NEAR, MIN_REGION = 0.01, 0.02, 0.05, 4
COLOURS = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent", "ok", "warn", "crit")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
BRAND = re.compile(r"^brand-[1-9][0-9]*$")
PATH = re.compile(r"<path\b([^>]*?)/?>", re.DOTALL)
ATTR = re.compile(r'([a-zA-Z-]+)="([^"]*)"')


class Refused(Exception):
    pass


# Colour maths: WCAG 2.2 luminance and contrast; OKLab and OKLCh (Björn Ottosson, 2020).

def to_rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def to_hex(rgb):
    return "#" + "".join(f"{max(0, min(255, round(c))):02X}" for c in rgb)


def linear(c):
    c /= 255
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def gamma(c):
    c = c * 12.92 if c <= 0.0031308 else 1.055 * c ** (1 / 2.4) - 0.055
    return c * 255


def luminance(h):
    r, g, b = (linear(c) for c in to_rgb(h))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def oklab(rgb):
    r, g, b = (linear(c) for c in rgb)
    lms = (0.4122214708 * r + 0.5363325363 * g + 0.0514459929 * b,
           0.2119034982 * r + 0.6806995451 * g + 0.1073969566 * b,
           0.0883024619 * r + 0.2817188376 * g + 0.6299787005 * b)
    l_, m_, s_ = (math.copysign(abs(x) ** (1 / 3), x) for x in lms)
    return (0.2104542553 * l_ + 0.7936177850 * m_ - 0.0040720468 * s_,
            1.9779984951 * l_ - 2.4285922050 * m_ + 0.4505937099 * s_,
            0.0259040371 * l_ + 0.7827717662 * m_ - 0.8086757660 * s_)


def from_oklab(lab):
    L, a, b = lab
    l_ = (L + 0.3963377774 * a + 0.2158037573 * b) ** 3
    m_ = (L - 0.1055613458 * a - 0.0638541728 * b) ** 3
    s_ = (L - 0.0894841775 * a - 1.2914855480 * b) ** 3
    rgb = (4.0767416621 * l_ - 3.3077115913 * m_ + 0.2309699292 * s_,
           -1.2684380046 * l_ + 2.6097574011 * m_ - 0.3413193965 * s_,
           -0.0041960863 * l_ - 0.7034186147 * m_ + 1.7076147010 * s_)
    return tuple(gamma(max(0.0, min(1.0, c))) for c in rgb)


def distance(h1, h2):
    return math.dist(oklab(to_rgb(h1)), oklab(to_rgb(h2)))


def derive(value, bg):
    """The colour with the same hue and chroma whose OKLab lightness is nearest the original and reaches 3:1 on bg."""
    L, a, b = oklab(to_rgb(value))
    for step in range(201):
        for sign in (1, -1):
            candidate = to_hex(from_oklab((min(1.0, max(0.0, L + sign * step * 0.005)), a, b)))
            if contrast(candidate, bg) >= 3:
                return candidate
    return "#FFFFFF" if luminance(bg) < 0.18 else "#000000"


# Inputs.

def png_size(path):
    with open(path, "rb") as fh:
        head = fh.read(24)
    if head[:8] != PNG_SIGNATURE or head[12:16] != b"IHDR":
        raise Refused(f"{os.path.basename(path)} is not a PNG: bring the logo as a PNG file")
    return struct.unpack(">II", head[16:24])


def load_input(path, kind):
    name = os.path.basename(path)
    w, h = png_size(path)
    if max(w, h) > 8192:
        raise Refused(f"{name} is {w} by {h} pixels: bring it at 8192 pixels or less on each side")
    if min(w, h) < 512:
        raise Refused(f"{name} is {w} by {h} pixels: bring it at 512 pixels or more on its short side, "
                      "ideally 1000 or more")
    if kind == "mark" and not 0.8 <= w / h <= 1.25:
        raise Refused(f"{name} is {w} by {h} pixels: the mark for the favicon must be roughly square")
    im = Image.open(path)
    im.load()
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    edges = [alpha.crop(box) for box in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h))]
    clear = sum(sum(e.histogram()[:128]) for e in edges)
    if clear < 0.2 * sum(e.width * e.height for e in edges):
        raise Refused(f"{name} has no transparent background: bring the logo in flat colours on a transparent "
                      "background")
    return im


def binary_alpha(im):
    return im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)


def main_colours(im):
    """The colours that each cover at least 0.5% of the logo's opaque pixels."""
    a = binary_alpha(im)
    opaque = a.histogram()[255]
    rgba = Image.merge("RGBA", (*Image.composite(im.convert("RGB"), Image.new("RGB", im.size), a).split(), a))
    colours = rgba.getcolors(1 << 22) or []
    return [c for count, c in colours if c[3] == 255 and count >= 0.005 * opaque]


# Trace and render.

def trace(im, work, name):
    clean = im.copy()
    clean.putalpha(binary_alpha(im))
    src, out = os.path.join(work, f"{name}.png"), os.path.join(work, f"{name}.traced.svg")
    clean.save(src)
    vtracer.convert_image_to_svg_py(src, out, **PARAMS)
    with open(out, encoding="utf-8") as fh:
        text = fh.read()
    paths = []
    for m in PATH.finditer(text):
        attrs = dict(ATTR.findall(m.group(1)))
        if attrs.get("d") and HEX.match(attrs.get("fill", "")):
            paths.append({"d": attrs["d"], "fill": attrs["fill"].upper(), "transform": attrs.get("transform", "")})
    return paths


def svg(paths, box, fills, size=None, style=None):
    """An SVG of only svg and path elements (and one style element when given), with a viewBox and no comment."""
    x, y, w, h = box
    dims = f' width="{size[0]}" height="{size[1]}"' if size else ""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x:g} {y:g} {w:g} {h:g}"{dims}>']
    if style:
        out.append(f"<style>{style}</style>")
    for p in paths:
        transform = f' transform="{p["transform"]}"' if p["transform"] else ""
        paint = f' class="{fills[p["fill"]]}"' if style else f' fill="{fills[p["fill"]]}"'
        out.append(f'<path d="{p["d"]}"{paint}{transform}/>')
    out.append("</svg>")
    return "\n".join(out) + "\n"


def render(resvg, text, work, name, w, h):
    src, out = os.path.join(work, f"{name}.svg"), os.path.join(work, f"{name}.png")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(text)
    subprocess.run([resvg, "-w", str(w), "-h", str(h), src, out], check=True, capture_output=True)
    return Image.open(out).convert("RGBA")


# Faithfulness.

def regions(mask):
    """The 4-connected regions of 255 in an L mask with at least MIN_REGION pixels."""
    m, n = mask.copy(), 0
    while (box := m.getbbox()) is not None:
        row = m.crop((box[0], box[1], box[2], box[1] + 1)).tobytes()
        x, y = box[0] + row.index(255), box[1]
        before = m.histogram()[255]
        ImageDraw.floodfill(m, (x, y), 0)
        if before - m.histogram()[255] >= MIN_REGION:
            n += 1
    return n


def hole_mask(mask):
    """The transparent regions as 255, inside a one-pixel 255 border, so the outside is one region."""
    holes = Image.new("L", (mask.width + 2, mask.height + 2), 255)
    holes.paste(mask.point(lambda v: 0 if v else 255), (1, 1))
    return holes


def topology(mask):
    return regions(mask), regions(hole_mask(mask)) - 1


def components(mask, limit=200):
    """Each 4-connected region of at least MIN_REGION pixels, as its own mask (at most limit of them)."""
    m, found = mask.copy(), []
    while (box := m.getbbox()) is not None and len(found) < limit:
        row = m.crop((box[0], box[1], box[2], box[1] + 1)).tobytes()
        before = m.copy()
        ImageDraw.floodfill(m, (box[0] + row.index(255), box[1]), 0)
        piece = ImageChops.subtract(before, m)
        if piece.histogram()[255] >= MIN_REGION:
            found.append(piece)
    return found


def unmatched(a, b):
    """The regions of a that do not meet exactly one region of b, and the regions of b that meet none of a."""
    out = Image.new("L", a.size, 0)
    for piece in components(a):
        if regions(ImageChops.multiply(piece, b)) != 1:
            out = ImageChops.lighter(out, piece)
    for piece in components(b):
        if regions(ImageChops.multiply(piece, a)) == 0:
            out = ImageChops.lighter(out, piece)
    return out


def detail_marks(a, r):
    """Each shape or hole that is in one image and not in the other, thickened so it shows at board size."""
    marks = unmatched(a, r)
    holes = unmatched(hole_mask(a), hole_mask(r)).crop((1, 1, a.width + 1, a.height + 1))
    return ImageChops.lighter(marks, holes).filter(ImageFilter.MaxFilter(7))


def colour_delta(im, rendered, fill):
    """The mean OKLab distance from the PNG's pixels to the traced colour, inside the region drawn in that colour."""
    diff = ImageChops.difference(rendered.convert("RGB"), Image.new("RGB", im.size, to_rgb(fill)))
    exact = [band.point(lambda v: 255 if v == 0 else 0) for band in diff.split()]
    mask = ImageChops.multiply(ImageChops.multiply(exact[0], exact[1]), exact[2])
    mask = ImageChops.multiply(mask, ImageChops.multiply(binary_alpha(im), binary_alpha(rendered)))
    region = Image.merge("RGBA", (*Image.composite(im.convert("RGB"), Image.new("RGB", im.size), mask).split(), mask))
    colours = [(n, c) for n, c in (region.getcolors(1 << 22) or []) if c[3] == 255]
    total = sum(n for n, _ in colours)
    if not total:
        return None
    target = oklab(to_rgb(fill))
    return sum(n * math.dist(oklab(c[:3]), target) for n, c in colours) / total


def faithfulness(im, paths, resvg, work, name):
    w, h = im.size
    fills = {p["fill"]: p["fill"] for p in paths}
    rendered = render(resvg, svg(paths, (0, 0, w, h), fills), work, f"{name}.check", w, h)
    a, r = binary_alpha(im), binary_alpha(rendered)
    differing = ImageChops.logical_xor(a.convert("1"), r.convert("1")).convert("L")
    mismatch = differing.histogram()[255] / max(1, a.histogram()[255])
    shapes = [topology(a), topology(r)]
    if shapes[0] != shapes[1]:
        differing = ImageChops.lighter(differing, detail_marks(a, r))
    deltas = {f: colour_delta(im, rendered, f) for f in sorted(fills)}
    known = [d for d in deltas.values() if d is not None]
    return {"mismatch": round(mismatch, 5),
            "shapes": [shapes[0][0], shapes[1][0]], "holes": [shapes[0][1], shapes[1][1]],
            "colour_delta": round(max(known), 5) if known else 0.0}, differing


def gap_image(im, differing, crit, path):
    faded = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
    faded = Image.blend(faded, Image.new("RGBA", im.size, (255, 255, 255, 255)), 0.7)
    faded.paste(Image.new("RGBA", im.size, (*to_rgb(crit), 255)), (0, 0), differing)
    faded.convert("RGB").save(path)


# Palette mapping.

def palette(tokens, mode):
    p = tokens.get(mode) or {}
    keys = [k for k in COLOURS if isinstance(p.get(k), str) and HEX.match(p[k])]
    keys += sorted((k for k in p if BRAND.match(k) and isinstance(p[k], str) and HEX.match(p[k])),
                   key=lambda k: int(k[6:]))
    return {k: p[k].upper() for k in keys}


def nearest(value, pal):
    best = min(pal, key=lambda k: distance(value, pal[k]), default=None)
    return (best, distance(value, pal[best])) if best else (None, None)


def run(company, resvg):
    identity = os.path.join(company, "docs/7-branding/identity")
    folder = os.path.join(identity, "logo")
    source = os.path.join(folder, "source")
    given = {m: os.path.join(source, f) for m, f in (("light", "logo.png"), ("dark", "logo-dark.png"))
             if os.path.isfile(os.path.join(source, f))}
    if not given:
        raise Refused("no logo PNG: put the logo in logo/source/logo.png (for light backgrounds), "
                      "logo/source/logo-dark.png (for dark backgrounds), or both")
    mark_path = os.path.join(source, "mark.png")
    images = {m: load_input(p, "logo") for m, p in given.items()}
    mark = load_input(mark_path, "mark") if os.path.isfile(mark_path) else None
    with open(os.path.join(identity, "tokens.json"), encoding="utf-8") as fh:
        tokens = json.load(fh)
    pals = {m: palette(tokens, m) for m in ("light", "dark")}
    crit = pals["light"].get("crit", "#D00000")
    gaps, proposals = [], []
    record = {"inputs": {}, "tracer": {"name": "vtracer", "version": VTRACER_VERSION, "params": PARAMS}}
    for p in sorted(list(given.values()) + ([mark_path] if mark else [])):
        with open(p, "rb") as fh:
            record["inputs"][os.path.relpath(p, folder)] = "sha256:" + hashlib.sha256(fh.read()).hexdigest()

    with tempfile.TemporaryDirectory() as work:
        def process(label, sources):
            """Trace each given PNG of one artwork (the logo or the mark), check it, map its colours and build the
            light and dark fills. Returns the paths per mode, the fills per mode and the trace record."""
            out, traced, fills = {}, {}, {"light": {}, "dark": {}}
            for mode, im in sources.items():
                name = f"{label}-{mode}"
                w, h = im.size
                if min(w, h) < 1000:
                    gaps.append({"what": f"{label} ({mode}): the PNG is under 1000 pixels on its short side, so "
                                         "small details may be lost", "where": f"source/{os.path.basename(given.get(mode, mark_path))}"})
                if len(main_colours(im)) > 8:
                    gaps.append({"what": f"{label} ({mode}): the PNG has more than eight main colours, which shows "
                                         "gradients or a photo rather than flat colours", "where": "source/"})
                paths = trace(im, work, name)
                result, differing = faithfulness(im, paths, resvg, work, name)
                where = f"trace-{mode}.png" if label == "logo" else f"trace-mark-{mode}.png"
                failed = []
                if result["mismatch"] > SHAPE_LIMIT:
                    failed.append(f"the shape differs from the PNG by {result['mismatch']:.2%} (limit 1%)")
                if result["shapes"][0] != result["shapes"][1] or result["holes"][0] != result["holes"][1]:
                    def count(n, word):
                        return f"{n} {word}{'' if n == 1 else 's'}"
                    failed.append("a detail of the logo is lost or added: the PNG has "
                                  f"{count(result['shapes'][0], 'shape')} and {count(result['holes'][0], 'hole')}, "
                                  f"the trace {count(result['shapes'][1], 'shape')} and "
                                  f"{count(result['holes'][1], 'hole')}")
                if result["colour_delta"] > COLOUR_LIMIT:
                    failed.append(f"a colour differs from the PNG by {result['colour_delta']:.3f} (limit 0.02)")
                image_path = os.path.join(folder, where)
                if failed:
                    gap_image(im, differing, crit, image_path)
                    gaps.extend({"what": f"{label} ({mode}): {f}", "where": where} for f in failed)
                elif os.path.exists(image_path):
                    os.remove(image_path)
                colours = []
                for fill in sorted({p["fill"] for p in paths}):
                    token, dist = nearest(fill, pals[mode])
                    if token is not None and dist <= NEAR:
                        fills[mode][fill] = pals[mode][token]
                        colours.append({"traced": fill, "token": token, "value": pals[mode][token],
                                        "delta": round(dist, 4)})
                        continue
                    fills[mode][fill] = fill
                    colours.append({"traced": fill, "token": None, "value": fill})
                    other = "dark" if mode == "light" else "light"
                    if "bg" in pals[other] and not any(distance(fill, q[mode]) <= NEAR for q in proposals):
                        proposals.append({"traced": fill, mode: fill, other: derive(fill, pals[other]["bg"])})
                traced[mode] = {"from": "given", **result, "colours": colours}
                out[mode] = paths
            for mode, other in (("dark", "light"), ("light", "dark")):
                if mode in out:
                    continue
                base = traced[other]["colours"]
                colours = []
                for c in base:
                    if c["token"] and c["token"] in pals[mode]:
                        fills[mode][c["traced"]] = pals[mode][c["token"]]
                        colours.append({"token": c["token"], "value": pals[mode][c["token"]]})
                    else:
                        fills[mode][c["traced"]] = c["value"]
                        colours.append({"token": None, "value": c["value"]})
                traced[mode] = {"from": "derived", "colours": colours}
                out[mode] = out[other]
            for mode in ("light", "dark"):
                bg = pals[mode].get("bg")
                if not bg:
                    continue
                for c in traced[mode]["colours"]:
                    if c["token"] is None and contrast(c["value"], bg) < 3:
                        gaps.append({"what": f"{label}: the colour {c['value']} may be hard to see on {mode} "
                                             f"backgrounds (under 3:1)", "where": f"{label}{'-dark' if mode == 'dark' else ''}.svg"})
            return out, fills, traced

        if not pals["light"] or not pals["dark"]:
            gaps.append({"what": "the palette is not set, so the logo keeps its own colours and the derived version "
                                 "is not recoloured", "where": "../tokens.json"})
        logo_paths, logo_fills, record["modes"] = process("logo", images)
        size = next(iter(images.values())).size
        written = set()

        def write(name, text):
            with open(os.path.join(folder, name), "w", encoding="utf-8") as fh:
                fh.write(text)
            written.add(name)

        for mode, name in (("light", "logo.svg"), ("dark", "logo-dark.svg")):
            write(name, svg(logo_paths[mode], (0, 0, *size), logo_fills[mode]))
        if mark is not None:
            mark_paths, mark_fills, record["mark"] = process("mark", {"light": mark})
            for mode, name in (("light", "mark.svg"), ("dark", "mark-dark.svg")):
                write(name, svg(mark_paths[mode], (0, 0, *mark.size), mark_fills[mode]))
            fav_image, fav_paths, fav_fills = mark, mark_paths, mark_fills
        else:
            for name in ("mark.svg", "mark-dark.svg"):
                if os.path.exists(os.path.join(folder, name)):
                    os.remove(os.path.join(folder, name))
            mode = "light" if "light" in images else "dark"
            fav_image, fav_paths, fav_fills = images[mode], logo_paths, logo_fills
            left, top, right, bottom = binary_alpha(fav_image).getbbox()
            if right - left > 1.5 * (bottom - top):
                gaps.append({"what": "the logo is wide, so the favicon is hard to read at 16 pixels; a square mark "
                                     "(logo/source/mark.png) would fix it", "where": "favicon.ico"})

        # The favicon and the icons: the artwork's opaque box, centred in a square with a little room around it.
        x0, y0, x1, y1 = binary_alpha(fav_image).getbbox()
        side = max(x1 - x0, y1 - y0) * 1.08
        box = ((x0 + x1) / 2 - side / 2, (y0 + y1) / 2 - side / 2, side, side)
        light_paths = fav_paths["light"]
        classes = {}
        for fill in sorted({p["fill"] for p in light_paths}):
            classes[fill] = f"c{len(classes)}"
        light_rules = "".join(f".{c}{{fill:{fav_fills['light'][f]}}}" for f, c in classes.items())
        dark_rules = "".join(f".{c}{{fill:{fav_fills['dark'].get(f, fav_fills['light'][f])}}}" for f, c in classes.items())
        write("favicon.svg", svg(light_paths, box, classes,
                                 style=f"{light_rules}@media (prefers-color-scheme: dark){{{dark_rules}}}"))
        light_svg = svg(light_paths, box, fav_fills["light"])
        icons = [render(resvg, light_svg, work, f"favicon-{s}", s, s) for s in (16, 32, 48)]
        # Pillow writes only the sizes up to the saved image's own, so the 48-pixel render carries the other two.
        icons[2].save(os.path.join(folder, "favicon.ico"), format="ICO", sizes=[(16, 16), (32, 32), (48, 48)],
                      append_images=icons[:2])
        written.add("favicon.ico")
        bg = to_rgb(pals["light"].get("bg", "#FFFFFF"))
        for s in (192, 512):
            inner = int(0.8 * s / math.sqrt(2)) - 2
            art = render(resvg, light_svg, work, f"icon-{s}", inner, inner)
            canvas = Image.new("RGBA", (s, s), (*bg, 255))
            canvas.alpha_composite(art, ((s - inner) // 2, (s - inner) // 2))
            canvas.convert("RGB").save(os.path.join(folder, f"icon-{s}.png"))
            written.add(f"icon-{s}.png")

    record["proposed_brand_tokens"] = proposals
    record["gaps"] = gaps
    record["faithful"] = not any(g["where"].startswith("trace-") for g in gaps)
    with open(os.path.join(folder, "trace.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    print(f"Logo processed: {', '.join(sorted(written))} and trace.json in docs/7-branding/identity/logo/.")
    for p in proposals:
        print(f"proposed brand token: {p['traced']} (light {p['light']}, dark {p['dark']}): add it to tokens.json "
              "if the founder accepts it, then run the logo step again")
    for g in gaps:
        print(f"gap: {g['what']} ({g['where']})")
    print("Faithful." if record["faithful"] else "Not faithful: each gap above is shown on the brand board.")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--resvg", required=True)
    ap.add_argument("company")
    args = ap.parse_args(argv)
    try:
        run(args.company, args.resvg)
    except Refused as e:
        print(f"brand.sh logo: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
