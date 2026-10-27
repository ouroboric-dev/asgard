"""Fixtures and probes for brand.test.sh, run with the brand tools' Python. No binary fixture is committed.

    brand_fixtures.py draw NAME PATH      draw the fixture PNG NAME at PATH
    brand_fixtures.py palette TOKENS      give tokens.json a full light and dark palette
    brand_fixtures.py accept TOKENS TRACE add trace.json's first proposed brand token to tokens.json as brand-1
    brand_fixtures.py trace TRACE EXPR    exit 0 when the Python expression EXPR is true of trace.json (as t)
    brand_fixtures.py dark3 TRACE         exit 0 when the first proposal's dark value reaches 3:1 on #121212
    brand_fixtures.py ico PATH            exit 0 when the ICO holds 16, 32 and 48 pixels
    brand_fixtures.py icons LOGO_DIR      exit 0 when both icons are opaque, with every mark pixel in the safe zone
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


def main(args):
    cmd = args[0]
    if cmd == "draw":
        draw(args[1], args[2])
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
