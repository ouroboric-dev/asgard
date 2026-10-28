"""Logo preparation for step 6a (brand tools spec §3.2): cut out a flat background, flatten anti-aliased edges to the
logo's flat colours, and raise the resolution, so the tracer gets what it traces well.

    logoprep.py [--mark] DIR IMAGE

Writes DIR/.ouroboric/choices/logo-prep/<name>.png and <name>.json (what was done). The short side becomes at least
1000 pixels, and at least 2400 for a mark (`--mark`): at 1400 pixels the tracer cut a mark's long arcs short. Run by
brand.sh logo-prep; writes nothing else.
"""
import argparse
import hashlib
import json
import os
import sys
from collections import Counter

from PIL import Image, ImageChops

MAX_SIDE, MIN_SIDE, TARGET, TARGET_MARK = 8192, 256, 1000, 2400
FLAT = 48          # a border pixel is the background when its colours are within this (sum of differences) of it
INK = 96           # a pixel is part of the logo when it is farther than this from the background
MERGE = 60         # colours within this of a flat colour belong to it
MIN_SHARE, MAX_COLOURS = 0.005, 8


class Refused(Exception):
    pass


def hexed(rgb):
    return "#%02X%02X%02X" % tuple(rgb[:3])


def distance(a, b):
    return sum(abs(x - y) for x, y in zip(a[:3], b[:3]))


def flat_colours(counts):
    """The flat colours of a {colour: pixels} table: each colour that, with its near colours, holds at least 0.5% of the
    pixels. The most frequent colour of a group stands for it."""
    total = sum(counts.values())
    found, rest = [], dict(counts)
    while rest and len(found) < MAX_COLOURS:
        centre = max(rest, key=lambda c: (rest[c], c))
        group = [c for c in rest if distance(c, centre) <= MERGE]
        share = sum(rest[c] for c in group)
        for c in group:
            del rest[c]
        if share >= MIN_SHARE * total:
            found.append((centre, share))
    return [c for c, _ in found]


def palette_image(colours):
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in colours for v in c[:3]])
    return pal


def border(im):
    w, h = im.size
    strips = [im.crop(b) for b in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h))]
    out = []
    for s in strips:
        data = s.convert("RGB").tobytes()
        out += [tuple(data[i:i + 3]) for i in range(0, len(data), 3)]
    return out


def prepare(path, mark):
    with open(path, "rb") as fh:
        head = fh.read(8)
    if not (head[:8] == b"\x89PNG\r\n\x1a\n" or head[:3] == b"\xff\xd8\xff"):
        raise Refused(f"{os.path.basename(path)} is not a PNG or a JPEG: bring the logo as one of those")
    Image.MAX_IMAGE_PIXELS = MAX_SIDE * MAX_SIDE
    try:
        im = Image.open(path)
        w, h = im.size
        if max(w, h) > MAX_SIDE:
            raise Refused(f"{os.path.basename(path)} is {w} by {h} pixels: bring it at {MAX_SIDE} pixels or less "
                          "on each side")
        if min(w, h) < MIN_SIDE:
            raise Refused(f"{os.path.basename(path)} is {w} by {h} pixels: bring it at {MIN_SIDE} pixels or more "
                          "on its short side, ideally 1000 or more")
        im.load()
    except (OSError, Image.DecompressionBombError) as e:
        raise Refused(f"{os.path.basename(path)} cannot be read as an image ({e})")
    rgba = im.convert("RGBA")
    target = TARGET_MARK if mark else TARGET
    # enlarged to the target exactly, not by a whole multiple: the tracer's output is not monotonic in the size
    scale = max(1.0, target / min(w, h))
    while scale > 1 and max(w, h) * scale > MAX_SIDE:
        scale = max(1.0, MAX_SIDE / max(w, h))
    size = (max(1, round(w * scale)), max(1, round(h * scale)))
    warnings = []
    if min(size) < target:
        warnings.append(f"the short side is {min(size)} pixels, under the {target} the tracer needs: "
                        "bring a larger image")
    alpha = rgba.getchannel("A")
    edge = [alpha.crop(b) for b in ((0, 0, w, 1), (0, h - 1, w, h), (0, 0, 1, h), (w - 1, 0, w, h))]
    clear = sum(sum(e.histogram()[:128]) for e in edge)
    given = clear >= 0.2 * sum(e.width * e.height for e in edge)
    if given:
        mask = alpha.point(lambda v: 255 if v >= 128 else 0)
        counts = Counter()
        solid = Image.new("RGB", rgba.size, (0, 0, 0))
        solid.paste(rgba.convert("RGB"), mask=mask)
        for n, c in (solid.getcolors(1 << 24) or []):
            counts[c] += n
        counts[(0, 0, 0)] -= mask.histogram()[0]       # the pixels pasted onto nothing are not the logo's black
        counts = Counter({c: n for c, n in counts.items() if n > 0})
        ink = flat_colours(counts)
        if not ink:
            raise Refused(f"{os.path.basename(path)} has nothing but a transparent background")
        up = rgba.convert("RGBa").resize(size, Image.LANCZOS).convert("RGBA")
        out = up.convert("RGB").quantize(palette=palette_image(ink), dither=Image.Dither.NONE).convert("RGBA")
        out.putalpha(up.getchannel("A").point(lambda v: 255 if v >= 128 else 0))
        background = {"from": "given"}
    else:
        rgb = rgba.convert("RGB")
        edge_px = border(rgb)
        bg = Counter(edge_px).most_common(1)[0][0]
        if sum(1 for p in edge_px if distance(p, bg) <= FLAT) < 0.9 * len(edge_px):
            raise Refused(f"the background of {os.path.basename(path)} is not one flat colour: bring the logo on a "
                          "plain background, or in flat colours on a transparent one")
        diff = ImageChops.difference(rgb, Image.new("RGB", rgb.size, bg))
        far = ImageChops.add(ImageChops.add(*diff.split()[:2]), diff.split()[2]).point(
            lambda v: 255 if v > INK else 0)
        if far.getbbox() is None:
            raise Refused(f"{os.path.basename(path)} has nothing but its background: bring the logo itself")
        only = Image.new("RGB", rgb.size, bg)
        only.paste(rgb, mask=far)
        counts = Counter({c: n for n, c in (only.getcolors(1 << 24) or []) if distance(c, bg) > INK})
        ink = flat_colours(counts)
        up = rgb.resize(size, Image.LANCZOS)
        q = up.quantize(palette=palette_image([bg] + ink), dither=Image.Dither.NONE)
        out = q.convert("RGBA")
        out.putalpha(q.point([0] + [255] * 255, "L"))
        background = {"from": "removed", "colour": hexed(bg)}
    if len(ink) > 4:
        warnings.append(f"{len(ink)} flat colours: a logo with gradients or many colours traces badly")
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    facts = {"input": {"name": os.path.basename(path), "sha256": digest, "width": w, "height": h},
             "background": background, "colours": [hexed(c) for c in ink], "scale": round(scale, 4), "mark": mark,
             "output": {"width": size[0], "height": size[1], "short_side": min(size)}, "warnings": warnings}
    return out, facts


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--mark", action="store_true")
    ap.add_argument("company")
    ap.add_argument("image")
    args = ap.parse_args(argv)
    try:
        out, facts = prepare(args.image, args.mark)
    except Refused as e:
        print(f"brand.sh logo-prep: {e}", file=sys.stderr)
        return 2
    folder = os.path.join(args.company, ".ouroboric", "choices", "logo-prep")
    os.makedirs(folder, exist_ok=True)
    stem = os.path.splitext(os.path.basename(args.image))[0]
    out.save(os.path.join(folder, f"{stem}.png"))
    with open(os.path.join(folder, f"{stem}.json"), "w", encoding="utf-8") as fh:
        json.dump(facts, fh, indent=2)
        fh.write("\n")
    print(f"Prepared {facts['input']['name']}: background {facts['background']['from']}, "
          f"{len(facts['colours'])} flat colours, {facts['input']['width']}x{facts['input']['height']} -> "
          f"{facts['output']['width']}x{facts['output']['height']}: .ouroboric/choices/logo-prep/{stem}.png")
    for w in facts["warnings"]:
        print(f"warning: {w}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
