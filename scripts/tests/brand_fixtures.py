"""Fixtures and probes for brand.test.sh, run with the brand tools' Python. No binary fixture is committed.

    brand_fixtures.py draw NAME PATH      draw the fixture PNG NAME at PATH
    brand_fixtures.py palette TOKENS      give tokens.json a full light and dark palette
    brand_fixtures.py accept TOKENS TRACE add trace.json's first proposed brand token to tokens.json as brand-1
    brand_fixtures.py trace TRACE EXPR    exit 0 when the Python expression EXPR is true of trace.json (as t)
    brand_fixtures.py dark3 TRACE         exit 0 when the first proposal's dark value reaches 3:1 on #121212
    brand_fixtures.py ico PATH            exit 0 when the ICO holds 16, 32 and 48 pixels
    brand_fixtures.py icons LOGO_DIR      exit 0 when both icons are opaque, with every mark pixel in the safe zone
    brand_fixtures.py font TOKENS DIR FAMILY FLAVOR   build an OFL font (FLAVOR ttf or woff2) in DIR, set the heading role
    brand_fixtures.py photo PATH SIZE     a sample photo, SIZE pixels on its long side
    brand_fixtures.py record IMAGERY FILE PERSON CONSENT   add a row to imagery.md's sample images table
    brand_fixtures.py ink PATH            exit 0 when the image holds more than one colour (something is drawn)
    brand_fixtures.py round PATH KIND     write a palette round of three presets (KIND: ok, light-fail, dark-fail, ...)
    brand_fixtures.py arcs PATH [flat]    a mark of three long arcs and a dot (anti-aliased on white, or flat)
    brand_fixtures.py trace-shades TRACE  write a trace.json with three shades of one token (a soft-edged logo)
"""
import json
import sys

from PIL import Image, ImageDraw

INK, PINK, LIGHT_INK = (26, 26, 26, 255), (194, 24, 91, 255), (237, 237, 237, 255)
CLEAR = (0, 0, 0, 0)


def canvas(w=1000, h=1000):
    im = Image.new("RGBA", (w, h), CLEAR)
    return im, ImageDraw.Draw(im)


def draw(name, path):
    if name == "mark":  # a two-colour mark that traces faithfully
        im, d = canvas()
        d.ellipse((120, 120, 880, 880), fill=INK)
        d.rectangle((350, 350, 650, 650), fill=PINK)
    elif name == "mark-dark":  # the same mark, drawn for dark backgrounds
        im, d = canvas()
        d.ellipse((120, 120, 880, 880), fill=LIGHT_INK)
        d.rectangle((350, 350, 650, 650), fill=PINK)
    elif name == "small-details":  # a 2 by 2 dot and a 2 by 2 hole: they stay faithful
        im, d = canvas()
        d.ellipse((120, 120, 880, 880), fill=INK)
        d.rectangle((60, 60, 61, 61), fill=INK)
        d.rectangle((300, 500, 301, 501), fill=CLEAR)
    elif name == "ring":  # a ring 2 pixels wide, which the trace breaks into 5 shapes: a gap
        im, d = canvas(1200, 1200)
        d.ellipse((150, 150, 1050, 1050), fill=INK)
        d.ellipse((60, 60, 1140, 1140), outline=INK, width=2)
    elif name == "wide":  # a wordmark much wider than tall
        im, d = canvas(2600, 1000)
        d.rectangle((100, 350, 2500, 650), fill=INK)
    elif name == "square":  # a square mark for the favicon
        im, d = canvas()
        d.rectangle((200, 200, 800, 800), fill=INK)
    elif name == "not-square":
        im, d = canvas(1000, 600)
        d.rectangle((100, 100, 900, 500), fill=INK)
    elif name == "gradient":  # many colours: gradients, not flat colours
        im, d = canvas()
        for i in range(20):
            d.rectangle((100 + i * 40, 100, 139 + i * 40, 900), fill=(i * 12, 30, 255 - i * 12, 255))
    elif name == "opaque":
        im = Image.new("RGBA", (1000, 1000), (255, 255, 255, 255))
        ImageDraw.Draw(im).ellipse((120, 120, 880, 880), fill=INK)
    elif name == "small":
        im, d = canvas(400, 400)
        d.ellipse((50, 50, 350, 350), fill=INK)
    elif name == "huge":
        im, d = canvas(8200, 600)
        d.rectangle((100, 100, 8100, 500), fill=INK)
    else:
        sys.exit(f"no fixture {name}")
    im.save(path)


GOOD = {
    "light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "border": "#DDDDDD", "text": "#1A1A1A", "muted": "#555555",
              "accent": "#0B5FCC", "accent-text": "#0B5FCC", "on-accent": "#FFFFFF", "ok": "#1B6E20",
              "warn": "#8A5A00", "crit": "#B00020"},
    "dark": {"bg": "#121212", "surface": "#1E1E1E", "border": "#333333", "text": "#EDEDED", "muted": "#B0B0B0",
             "accent": "#6EA8FE", "accent-text": "#6EA8FE", "on-accent": "#121212", "ok": "#81C784",
             "warn": "#FFB74D", "crit": "#EF9A9A"},
}


def luminance(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def load(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def save(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def font(tokens, folder, family, flavor):
    import os

    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    os.makedirs(folder, exist_ok=True)
    fb = FontBuilder(1000, isTTF=True)
    order = [".notdef"] + [chr(c) for c in range(0x41, 0x5B)] + [chr(c) for c in range(0x61, 0x7B)]
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(g): g for g in order[1:]})
    glyphs, metrics = {}, {}
    for g in order:
        pen = TTGlyphPen(None)
        pen.moveTo((50, 0))
        pen.lineTo((300, 700))
        pen.lineTo((550, 0))
        pen.closePath()
        glyphs[g], metrics[g] = pen.glyph(), (600, 50)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics(metrics)
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    ps = family.replace(" ", "") + "-Regular"
    names = {"familyName": family, "styleName": "Regular"}
    if flavor != "bare":  # "bare": only the family and style names, a font the renderer cannot load
        names.update({"uniqueFontIdentifier": f"1.000;TEST;{ps}", "fullName": f"{family} Regular", "psName": ps,
                      "version": "Version 1.000"})
    fb.setupNameTable(names)
    fb.setupOS2(usWeightClass=400, fsType=0)
    fb.setupPost()
    if flavor == "woff2":
        fb.font.flavor = "woff2"
    fb.save(os.path.join(folder, f"Test-Regular.{'ttf' if flavor == 'bare' else flavor}"))
    with open(os.path.join(folder, "OFL.txt"), "w", encoding="utf-8") as fh:
        fh.write("SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n")
    t = load(tokens)
    rel = os.path.relpath(folder, os.path.dirname(tokens))
    for role in ("wordmark", "display", "heading", "body", "ui"):
        t["type"]["fonts"][role].update({"family": family, "fallback": "serif", "weights": [400], "files": rel,
                                         "licence": "OFL-1.1", "source": "https://example.org/fonts"})
    save(tokens, t)


def face(folder, family, name, chars, weight, italic, axis, licence):
    """A font file and its licence file in `folder`, as the library publishes a family: `axis` is "wght" for a
    variable font with a weight axis from 300 to 700 (and "wght,ital" with an italic axis too), else "-"."""
    import os

    from fontTools.fontBuilder import FontBuilder
    from fontTools.pens.ttGlyphPen import TTGlyphPen

    os.makedirs(folder, exist_ok=True)
    chars = "".join(chr(int(c, 16)) for c in chars.split(",")) if chars != "-" else "ABCabc"
    order = [".notdef"] + ["g%04X" % ord(c) for c in chars]
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(order)
    fb.setupCharacterMap({ord(c): "g%04X" % ord(c) for c in chars})
    pen = TTGlyphPen(None)
    pen.moveTo((50, 0))
    pen.lineTo((300, 700))
    pen.lineTo((550, 0))
    pen.closePath()
    glyph = pen.glyph()
    fb.setupGlyf({g: glyph for g in order})
    fb.setupHorizontalMetrics({g: (600, 50) for g in order})
    fb.setupHorizontalHeader(ascent=800, descent=-200)
    fb.setupNameTable({"familyName": family, "styleName": "Italic" if italic == "1" else "Regular"})
    fb.setupOS2(usWeightClass=int(weight), fsType=0, fsSelection=1 if italic == "1" else 0x40)
    fb.setupPost()
    if italic == "1":
        fb.font["head"].macStyle = 2
    if axis != "-":
        axes = [("wght", 300, 400, 700, "Weight")] + ([("ital", 0, 0, 1, "Italic")] if "ital" in axis else [])
        fb.setupFvar(axes=axes, instances=[])
    fb.save(os.path.join(folder, name))
    text = {"ofl": "SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007\n",
            "unknown": "Commercial font licence. One desktop seat.\n"}[licence]
    with open(os.path.join(folder, "OFL.txt"), "w", encoding="utf-8") as fh:
        fh.write(text)
def round_file(path, kind):
    """A palette round of three presets: `kind` says what is wrong with it (ok: nothing)."""
    import copy
    good = {m: dict(v) for m, v in GOOD.items()}
    calm, bold, pale = (copy.deepcopy(good) for _ in range(3))
    bold["light"].update({"accent": "#8A1C7C", "accent-text": "#8A1C7C"})
    bold["dark"].update({"accent": "#F0A0E6", "accent-text": "#F0A0E6"})
    pale["light"]["muted"] = "#999999" if kind == "light-fail" else good["light"]["muted"]
    pale["dark"]["muted"] = "#555555" if kind == "dark-fail" else good["dark"]["muted"]
    presets = [{"id": "calm", "name": "Calm blue", **calm}, {"id": "bold", "name": "Bold plum", **bold},
               {"id": "pale", "name": "Pale grey", **pale}]
    rnd = 1
    if kind == "five":
        presets += [{**copy.deepcopy(calm), "id": f"x{i}", "name": f"Extra {i}"} for i in range(2)]
    elif kind == "missing-key":
        del presets[0]["light"]["border"]
    elif kind == "bad-hex":
        presets[1]["dark"]["text"] = "white"
    elif kind == "dup":
        presets[1]["id"] = "calm"
    elif kind == "brand-half":
        presets[0]["light"]["brand-1"] = "#C2185B"
    elif kind == "round4":
        rnd = 4
    elif kind == "brand-ok":
        presets[0]["light"]["brand-1"] = "#C2185B"
        presets[0]["dark"]["brand-1"] = "#F06292"
    save(path, {"round": rnd, "presets": presets})


def arcs(path, flat):
    """A mark of three long arcs and a dot, 1400 pixels square: anti-aliased on white (a logo as an image generator
    makes it), or `flat`: the same, flattened to three colours on a transparent background, but not enlarged."""
    k, size = 4, 1400
    big = Image.new("RGB", (size * k, size * k), (255, 255, 255))
    d = ImageDraw.Draw(big)
    c = size * k / 2
    for r, a0, a1 in ((0.42, 200, 520), (0.30, 20, 330), (0.18, 100, 400)):
        radius = r * size * k
        d.arc((c - radius, c - radius, c + radius, c + radius), a0, a1, fill=(26, 26, 26), width=80 * k)
    d.ellipse((c - 0.05 * size * k, c - 0.05 * size * k, c + 0.05 * size * k, c + 0.05 * size * k), fill=(194, 24, 91))
    im = big.resize((size, size), Image.LANCZOS)
    if flat:
        pal = Image.new("P", (1, 1))
        pal.putpalette([255, 255, 255, 26, 26, 26, 194, 24, 91] + [0] * (256 * 3 - 9))
        q = im.quantize(palette=pal, dither=Image.Dither.NONE)
        im = q.convert("RGB")
        im.putalpha(q.point([0] + [255] * 255, "L"))
    im.save(path)


def main(args):
    cmd = args[0]
    if cmd == "draw":
        draw(args[1], args[2])
    elif cmd == "font":
        font(*args[1:5])
    elif cmd == "photo":
        size = int(args[2])
        im = Image.new("RGB", (size, size * 2 // 3), (120, 140, 160))
        ImageDraw.Draw(im).ellipse((size // 4, size // 8, size * 3 // 4, size // 2), fill=(200, 160, 120))
        im.save(args[1])
    elif cmd == "trace-shades":  # a trace.json whose dark shades all map to one token, as a real soft-edged logo gives
        shades = ["#2D2523", "#2E2524", "#2E2624"]
        light = [{"traced": s, "token": "text", "value": "#1A1A1A", "delta": 0.01} for s in shades]
        light.append({"traced": "#9C5650", "token": "accent", "value": "#0B5FCC", "delta": 0.0})
        dark = [{"token": "text", "value": "#EDEDED"} for _ in shades] + [{"token": "accent", "value": "#6EA8FE"}]
        save(args[1], {"inputs": {}, "tracer": {"name": "vtracer", "version": "0.6.15", "params": {}},
                       "modes": {"light": {"from": "given", "mismatch": 0.0, "shapes": [1, 1], "holes": [0, 0],
                                           "colour_delta": 0.0, "colours": light},
                                 "dark": {"from": "derived", "colours": dark}},
                       "proposed_brand_tokens": [], "gaps": [], "faithful": True})
    elif cmd == "face":  # face FOLDER FAMILY FILE CHARS(hex,hex|-) WEIGHT ITALIC(0|1) AXIS LICENCE
        face(*args[1:9])
    elif cmd == "json-get":  # json-get FILE PYTHON-EXPRESSION: print the value
        print(eval(args[2], {"d": load(args[1])}))
    elif cmd == "round":  # round PATH KIND
        round_file(args[1], args[2])
    elif cmd == "json":  # json FILE PYTHON-EXPRESSION: exit 0 when the expression is true of d
        return 0 if eval(args[2], {"d": load(args[1])}) else 1
    elif cmd == "arcs":  # arcs PATH [flat]
        arcs(args[1], len(args) > 2 and args[2] == "flat")
    elif cmd == "colours":  # colours PNG MAX: opaque pixels have at most MAX colours, and the alpha is 0 or 255
        im = Image.open(args[1]).convert("RGBA")
        found = {c[:3] for _, c in im.getcolors(1 << 24) if c[3] > 0}
        alphas = {c for _, c in im.getchannel("A").getcolors()}
        return 0 if len(found) <= int(args[2]) and alphas <= {0, 255} else 1
    elif cmd == "short":  # short PNG MIN: the short side is at least MIN pixels
        return 0 if min(Image.open(args[1]).size) >= int(args[2]) else 1
    elif cmd == "clear-corners":  # clear-corners PNG: the four corner pixels are transparent
        im = Image.open(args[1]).convert("RGBA")
        w, h = im.size
        return 0 if all(im.getpixel(p)[3] == 0 for p in ((0, 0), (w - 1, 0), (0, h - 1), (w - 1, h - 1))) else 1
    elif cmd == "jpeg":  # jpeg PATH: a logo saved as a JPEG, on white
        im = Image.new("RGB", (900, 900), (255, 255, 255))
        d = ImageDraw.Draw(im)
        d.ellipse((100, 100, 800, 800), fill=(26, 26, 26))
        d.rectangle((330, 330, 570, 570), fill=(194, 24, 91))
        im.save(args[1], "JPEG", quality=70)
    elif cmd == "noisy":  # noisy PATH: a logo on a background that is not one flat colour
        im = Image.new("RGB", (800, 800))
        px = im.load()
        for y in range(800):
            for x in range(800):
                px[x, y] = ((x * 7) % 256, (y * 11) % 256, ((x + y) * 5) % 256)
        im.save(args[1])
    elif cmd == "blank":  # blank PATH: nothing but a flat background
        Image.new("RGB", (800, 800), (250, 250, 250)).save(args[1])
    elif cmd == "accepted":  # accepted TOKENS CHECK VALUE REASON
        t = load(args[1])
        t["accepted"].append({"check": args[2], "value": args[3], "reason": args[4], "by": "Alex", "date": "2026-10-28"})
        save(args[1], t)
    elif cmd == "message-colour":  # message-colour TOKENS HEX: the message colours become one distinctive colour
        t = load(args[1])
        for mode in ("light", "dark"):
            t[mode].update({"ok": args[2], "warn": args[2], "crit": args[2]})
        save(args[1], t)
    elif cmd == "lacks-colour":  # lacks-colour PNG HEX: no pixel has this colour
        im = Image.open(args[1]).convert("RGB")
        want = tuple(int(args[2][i:i + 2], 16) for i in (1, 3, 5))
        return 1 if any(c == want for _, c in (im.getcolors(1 << 24) or [])) else 0
    elif cmd == "half-width":  # half-width HTML PNG: the HTML shows the image at half its pixel width
        import re
        shown = int(re.search(r'width="(\d+)"', open(args[1], encoding="utf-8").read()).group(1))
        return 0 if Image.open(args[2]).width == 2 * shown else 1
    elif cmd == "size":  # size PNG WxH
        return 0 if "x".join(map(str, Image.open(args[1]).size)) == args[2] else 1
    elif cmd == "ink":
        im = Image.open(args[1]).convert("RGB")
        return 0 if len(im.getcolors(1 << 24) or []) > 1 else 1
    elif cmd == "record":
        with open(args[1], "a", encoding="utf-8") as fh:
            fh.write(f"| {args[2]} | {args[3]} | {args[4]} |\n")
    elif cmd == "palette":
        t = load(args[1])
        for mode, values in GOOD.items():
            t[mode].update(values)
        save(args[1], t)
    elif cmd == "accept":
        t = load(args[1])
        p = load(args[2])["proposed_brand_tokens"][0]
        t["light"]["brand-1"], t["dark"]["brand-1"] = p["light"], p["dark"]
        save(args[1], t)
    elif cmd == "trace":
        return 0 if eval(args[2], {"t": load(args[1])}) else 1
    elif cmd == "dark3":
        d = load(args[1])["proposed_brand_tokens"][0]["dark"]
        a, b = sorted((luminance(d), luminance("#121212")), reverse=True)
        return 0 if (a + 0.05) / (b + 0.05) >= 3 else 1
    elif cmd == "ico":
        sizes = set(Image.open(args[1]).info["sizes"])
        return 0 if {(16, 16), (32, 32), (48, 48)} <= sizes else 1
    elif cmd == "icons":
        for size in (192, 512):
            im = Image.open(f"{args[1]}/icon-{size}.png").convert("RGBA")
            if im.size != (size, size) or im.getchannel("A").getextrema() != (255, 255):
                return 1
            bg, c, r = im.getpixel((0, 0)), size / 2, 0.4 * size
            for y in range(size):
                for x in range(size):
                    if (x + 0.5 - c) ** 2 + (y + 0.5 - c) ** 2 > r * r and im.getpixel((x, y)) != bg:
                        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
