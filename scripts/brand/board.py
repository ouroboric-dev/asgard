"""The brand board (brand tools spec §5.4): one plain Markdown page with generated images, so it reads the same in
GitHub's file view and in the rendered pages. Run by brand.sh board; writes board.md and the board/ folder.

    board.py --resvg PATH [--check] DIR
"""
import argparse
import datetime
import json
import math
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # brand.sh runs this file isolated (-I)
import design  # noqa: E402
from design import esc, render  # noqa: E402

IDENTITY = "docs/7-branding/identity"
BOARD, IMAGES = f"{IDENTITY}/board.md", f"{IDENTITY}/board"
LOGO = f"{IDENTITY}/logo"
IMAGERY, IMAGERY_MD = "docs/7-branding/imagery", "docs/7-branding/imagery.md"
PHOTO_EXT = (".png", ".jpg", ".jpeg", ".webp", ".gif")
COLOURS = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent", "ok", "warn", "crit")
MESSAGES = ("ok", "warn", "crit")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
BRAND = re.compile(r"^brand-[1-9][0-9]*$")
ROLES = design.ROLES
CLOSING = "This check compares licence files and font data. It is not legal advice."


class Refused(Exception):
    pass


def luminance(h):
    c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    c = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def readable_on(bg):
    return "#000000" if luminance(bg) > 0.18 else "#FFFFFF"


def palette(tokens, mode):
    p = tokens.get(mode) or {}
    keys = [k for k in COLOURS if isinstance(p.get(k), str) and HEX.match(p[k])]
    keys += sorted((k for k in p if BRAND.match(k) and isinstance(p[k], str) and HEX.match(p[k])),
                   key=lambda k: int(k[6:]))
    return {k: p[k].upper() for k in keys}


def brand_json(command):
    """The rows of the company's own check, so each rule has one implementation."""
    r = subprocess.run([sys.executable, "-I", ".ouroboric/checks/brand.py", command, "--json"],
                       capture_output=True, text=True, check=False)
    return [json.loads(line) for line in r.stdout.splitlines() if line.startswith("{")]


def inputs_hash():
    # the company's own brand.py computes the hash; importing it must leave no cache folder in the company
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.abspath(".ouroboric/checks"))
    import brand
    return brand.board_inputs_hash()


def recorded_hash():
    try:
        with open(BOARD, encoding="utf-8") as fh:
            m = re.search(r"<!-- inputs: (sha256:[0-9a-f]{64}) -->", fh.read())
    except OSError:
        return None
    return m.group(1) if m else None


# Generated images.

class Out:
    """The files of board/ written in this run; the rest of board/ is removed, so nothing stale stays."""

    def __init__(self):
        os.makedirs(IMAGES, exist_ok=True)
        self.written = set()

    def text(self, name, content):
        with open(os.path.join(IMAGES, name), "w", encoding="utf-8") as fh:
            fh.write(content)
        self.written.add(name)
        return f"board/{name}"

    def image(self, name, im):
        im.save(os.path.join(IMAGES, name))
        self.written.add(name)
        return f"board/{name}"

    def finish(self):
        for name in sorted(os.listdir(IMAGES)):
            if name not in self.written and name.endswith((".svg", ".png")):
                os.remove(os.path.join(IMAGES, name))


def brand_colours(pal):
    """The palette without the message colours: those colour the products' system messages, not the brand."""
    return [k for k in pal if k not in MESSAGES]


def palette_panel(pal, mode):
    bg = pal.get("bg", "#FFFFFF" if mode == "light" else "#121212")
    ink = pal.get("text", readable_on(bg))
    cols, cw, ch = 4, 230, 130
    keys = brand_colours(pal)
    rows = max(1, math.ceil(len(keys) / cols))
    w, h = cols * cw + 20, rows * ch + 60
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">',
           f'<rect x="0" y="0" width="{w}" height="{h}" fill="{bg}"/>',
           f'<text x="20" y="34" font-family="sans-serif" font-size="20" fill="{ink}">{mode.capitalize()} palette</text>']
    if not keys:
        out.append(f'<text x="20" y="80" font-family="sans-serif" font-size="16" fill="{ink}">The palette is not set '
                   "yet.</text>")
    for i, k in enumerate(keys):
        x, y = 20 + (i % cols) * cw, 50 + (i // cols) * ch
        out += [f'<g transform="translate({x},{y})">',
                f'<rect x="0" y="0" width="210" height="70" rx="6" fill="{pal[k]}" stroke="{ink}" stroke-opacity="0.25"/>',
                f'<text x="0" y="92" font-family="sans-serif" font-size="15" fill="{ink}">{esc(k)}</text>',
                f'<text x="0" y="112" font-family="monospace" font-size="14" fill="{ink}">{pal[k]}</text>', "</g>"]
    out.append("</svg>")
    return "\n".join(out) + "\n"


def palette_strip(pal):
    keys = brand_colours(pal)
    w = 60 * len(keys)
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 40" width="{w}" height="40">']
    out += [f'<rect x="{i * 60}" y="0" width="60" height="40" fill="{pal[k]}"/>' for i, k in enumerate(keys)]
    out.append("</svg>")
    return "\n".join(out) + "\n"


def on_background(svg_path, bg):
    """The logo's paths on a background rectangle, with room around them."""
    with open(svg_path, encoding="utf-8") as fh:
        text = fh.read()
    x, y, w, h = (float(v) for v in re.search(r'viewBox="([^"]+)"', text).group(1).split())
    pad = 0.08 * max(w, h)
    paths = re.findall(r"<path\b[^>]*/>", text)
    box = f"{x - pad:g} {y - pad:g} {w + 2 * pad:g} {h + 2 * pad:g}"
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{box}" width="480" height="{480 * (h + 2 * pad) / (w + 2 * pad):.0f}">',
           f'<rect x="{x - pad:g}" y="{y - pad:g}" width="{w + 2 * pad:g}" height="{h + 2 * pad:g}" fill="{bg}"/>',
           *paths, "</svg>"]
    return "\n".join(out) + "\n"


def specimen(resvg, work, role, spec, pal, size):
    """The role's font in each weight at its scale size, rendered by resvg from the shipped files."""
    fonts = design.font_files(spec, work, role)
    if not fonts:
        return None
    weights = spec.get("weights") or [400]
    bg, ink = pal.get("bg", "#FFFFFF"), pal.get("text", "#1A1A1A")
    step = round(size * 1.6) + 16
    h = 30 + step * len(weights)
    lines = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 {h}" width="1200" height="{h}">',
             f'<rect x="0" y="0" width="1200" height="{h}" fill="{bg}"/>']
    for i, weight in enumerate(weights):
        lines.append(f'<text x="24" y="{24 + round(size * 1.1) + step * i}" font-family="{esc(spec["family"])}" '
                     f'font-weight="{weight}" font-size="{size:g}" fill="{ink}">{esc(spec["family"])} {weight}: '
                     "The quick brown fox, 0123</text>")
    lines.append("</svg>")
    args = ["--skip-system-fonts"] + [a for f in fonts for a in ("--use-font-file", f)]
    im = render(resvg, "\n".join(lines) + "\n", work, f"type-{role}", *args)
    # A font the renderer cannot load draws nothing: no blank image goes on the board.
    return im if len(im.convert("RGB").getcolors(1 << 24) or []) > 1 else None


# The page.

def sample_images():
    if not os.path.isdir(IMAGERY):
        return []
    photos = sorted(n for n in os.listdir(IMAGERY) if n.lower().endswith(PHOTO_EXT))
    if len(photos) > 6:
        raise Refused(f"{IMAGERY} holds {len(photos)} sample images: the board shows six at most; keep the six "
                      "that show the work best")
    for n in photos:
        with Image.open(os.path.join(IMAGERY, n)) as im:
            if max(im.size) > 1600:
                raise Refused(f"{n} is {im.size[0]} by {im.size[1]} pixels: sample images are at most 1600 pixels on "
                              "their long side")
    return photos


def image_records():
    records = {}
    try:
        with open(IMAGERY_MD, encoding="utf-8") as fh:
            text = fh.read()
    except OSError:
        return records
    part = text.split("## Sample images", 1)[1] if "## Sample images" in text else ""
    for line in part.splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 3 and cells[0] not in ("File", "---") and not cells[0].startswith("-"):
            records[cells[0]] = {"person": cells[1].lower(), "consent": cells[2]}
    return records


def drawn_lettering(tokens):
    """(drawn family, wordmark family, alternative) when the logo's lettering was drawn in another face than the wordmark role's."""
    try:
        with open(f"{IDENTITY}/choices/logo.json", encoding="utf-8") as fh:
            chosen = json.load(fh)
        drawn = chosen["wordmark"]["family"]
        now = tokens["type"]["fonts"]["wordmark"]["family"]
    except (OSError, ValueError, KeyError, TypeError):
        return None
    return (drawn, now, chosen.get("alternative", "ALTERNATIVE")) if drawn != now else None


def make(resvg, today):
    with open(f"{IDENTITY}/tokens.json", encoding="utf-8") as fh:
        tokens = json.load(fh)
    pals = {m: palette(tokens, m) for m in ("light", "dark")}
    photos = sample_images()
    records = image_records()
    contrast_rows, font_rows = brand_json("contrast"), brand_json("fonts")
    out, md, open_items = Out(), [], []
    trace = None
    if os.path.isfile(f"{LOGO}/trace.json"):
        with open(f"{LOGO}/trace.json", encoding="utf-8") as fh:
            trace = json.load(fh)

    md += ["## Palette", ""]
    for mode in ("light", "dark"):
        md += [f"### {mode.capitalize()}", "", f"![The {mode} palette]({out.text(f'palette-{mode}.svg', palette_panel(pals[mode], mode))})", ""]
        rows = [r for r in contrast_rows if r["mode"] == mode]
        if rows:
            md += ["| Pair | Ratio | Minimum | Result |", "| --- | --- | --- | --- |"]
            for r in rows:
                ratio = f"{math.floor(r['ratio'] * 100) / 100:.2f}:1"
                minimum = f"{r['minimum']:g}:1" if r["minimum"] else "none"
                if r["fg"] not in MESSAGES:   # the message colours are checked, not shown: they are not the brand
                    md.append(f"| {r['fg']} on {r['bg']} | {ratio} | {minimum} | {r['result']} |")
                if r["result"] == "fails":
                    open_items.append(f"Contrast, {mode}: {r['fg']} on {r['bg']} is {ratio}, under {minimum}.")
            md.append("")
        else:
            md += ["The palette is not set yet.", ""]
    md += [("The message colours (ok, warn, crit) colour the products' system messages only. They are not part of "
            "the brand, so the board leaves them out; they are in tokens.json, and the brand check checks their "
            "contrast."), ""]

    md += ["## Type", ""]
    fonts = (tokens.get("type") or {}).get("fonts") or {}
    by_role = {r["role"]: r for r in font_rows}
    with tempfile.TemporaryDirectory() as work:
        chosen = [role for role in ROLES if (fonts.get(role) or {}).get("family")]
        if not chosen:
            md += ["No font is chosen yet.", ""]
        for role in chosen:
            spec = fonts[role]
            md += [f"### {role.capitalize()}: {spec['family']}", ""]
            if spec.get("files") and os.path.isdir(os.path.join(IDENTITY, spec["files"])):
                scale = (tokens.get("type") or {}).get("scale") or {}
                size_key, leading_key = design.SCALE_FOR[role]
                size = (scale.get("sizes") or {}).get(size_key, 32)
                leading = (scale.get("lineHeight") or {}).get(leading_key)
                im = specimen(resvg, work, role, spec, pals["light"], size)
                if im is not None:
                    md += [f"![{spec['family']} in each weight]({out.image(f'type-{role}.png', im)})", "",
                           f"Set at {size:g} px" + (f" with line height {leading:g}" if leading else "") + ".", ""]
                else:
                    md += [f"The sample of {spec['family']} could not be drawn from its files.", ""]
                    open_items.append(f"Font {spec['family']} ({role}): its sample could not be drawn from the "
                                      "font files; check that they are complete font files.")
            row = by_role.get(role, {})
            result, reasons, review = row.get("result"), row.get("reasons") or [], row.get("review") or {}
            if result == "known":
                words = f"known open licence {reasons[0]}"
            elif result == "not-shipped":
                words = f"not shipped: the reader's device supplies it (fallback {spec.get('fallback') or 'none'})"
            elif result == "person" and review.get("by"):
                words = f"read by {review['by']} on {review.get('date')}: this is their reading"
            elif result == "person":
                words = "needs a person: " + "; ".join(reasons)
                open_items.append(f"Font {spec['family']} ({role}): needs a person: {'; '.join(reasons)}.")
            else:
                words = "missing evidence: " + "; ".join(reasons)
                open_items.append(f"Font {spec['family']} ({role}): missing evidence: {'; '.join(reasons)}.")
            md += [f"Licence: {words}.", ""]
        if chosen:
            md += [CLOSING, ""]

        md += ["## Logo", ""]
        if trace is None:
            md += ["The logo is not processed yet.", ""]
        else:
            for name, label in (("logo.png", "for light backgrounds"), ("logo-dark.png", "for dark backgrounds"),
                                ("mark.png", "the square mark")):
                if os.path.isfile(f"{LOGO}/source/{name}"):
                    md += [f"![The logo as the founder brought it, {label}](logo/source/{name})", ""]
            for art in ("logo", "mark"):
                if not os.path.isfile(f"{LOGO}/{art}.svg"):
                    continue
                for mode, suffix in (("light", ""), ("dark", "-dark")):
                    bg = pals[mode].get("bg", "#FFFFFF" if mode == "light" else "#121212")
                    link = out.text(f"{art}-on-{mode}.svg", on_background(f"{LOGO}/{art}{suffix}.svg", bg))
                    md += [f"![The {art} on the {mode} background]({link})", ""]
            md += ["| Mode | Traced colour | Token | Value |", "| --- | --- | --- | --- |"]
            for mode in ("light", "dark"):
                # soft edges trace as several shades of one colour: one row for each token (or kept colour)
                shown = set()
                for c in trace["modes"][mode]["colours"]:
                    key = c["token"] or c["value"]
                    if key in shown:
                        continue
                    shown.add(key)
                    md.append(f"| {mode} | {c.get('traced', 'derived')} | {c['token'] or 'kept: no token'} | {c['value']} |")
            md.append("")
            current = {v for m in ("light", "dark") for v in pals[m].values()}
            for p in trace.get("proposed_brand_tokens", []):
                if p["light"].upper() not in current:
                    open_items.append(f"Proposed brand token {p['traced']}: light {p['light']}, dark {p['dark']}. "
                                      "Add it to tokens.json if the founder accepts it.")
            if os.path.isfile(f"{LOGO}/favicon.svg"):
                with open(f"{LOGO}/favicon.svg", encoding="utf-8") as fh:
                    fav = fh.read()
                links = [out.image(f"favicon-{s}.png", render(resvg, fav, work, f"fav{s}", "-w", str(s), "-h", str(s)))
                         for s in (16, 32, 48)]
                md += ["Favicon at 16, 32 and 48 pixels: " + " ".join(f"![Favicon, {s} pixels]({link})"
                                                                     for s, link in zip((16, 32, 48), links)), ""]
            for s in (192, 512):
                if os.path.isfile(f"{LOGO}/icon-{s}.png"):
                    icon = Image.open(f"{LOGO}/icon-{s}.png").convert("RGBA")
                    mask = Image.new("L", icon.size, 0)
                    ImageDraw.Draw(mask).ellipse((0, 0, s - 1, s - 1), fill=255)
                    icon.putalpha(mask)
                    md += [f"![The {s}-pixel app icon inside a circle mask]({out.image(f'icon-{s}-masked.png', icon)})", ""]
            if trace.get("faithful") and not trace.get("gaps"):
                md += ["Faithful: the trace matches the PNG.", ""]
            for g in trace.get("gaps", []):
                where = g["where"]
                line = f"Gap: {g['what']}."
                if where.endswith(".png") and os.path.isfile(f"{LOGO}/{where}"):
                    md += [line, "", f"![Where the trace differs]({'logo/' + where})", ""]
                else:
                    md += [line, ""]
                open_items.append(f"Logo: {g['what']}.")
            md += design.logo_usage_md(tokens, pals, out, resvg, work)

    lettering = drawn_lettering(tokens)
    if lettering:
        open_items.append(f"Logo: the lettering is drawn in {lettering[0]}, and the wordmark role is {lettering[1]} now. Draw it again "
                          f"with `brand.sh logo-proposals CANDIDATES --choose {lettering[2]}:FACE`, FACE being the id of {lettering[1]}.")
    md += ["## Sample images", ""]
    if not photos:
        md += ["No sample image yet.", ""]
    for n in photos:
        rec = records.get(n)
        if rec is None:
            words = "no record in imagery.md"
            open_items.append(f"Sample image {n}: no record in imagery.md.")
        elif rec["person"] == "yes" and not rec["consent"]:
            words = "shows a person; no consent recorded"
            open_items.append(f"Sample image {n}: shows a person and has no consent recorded.")
        elif rec["person"] == "yes":
            words = f"shows a person; consent: {rec['consent']}"
        else:
            words = "shows no person"
        md += [f"![{n}](../imagery/{n})", "", f"{n}: {words}.", ""]
    if pals["light"]:
        md += [f"![The light palette]({out.text('palette-strip.svg', palette_strip(pals['light']))})", ""]

    with tempfile.TemporaryDirectory() as work2:
        md += design.foundations_md(tokens, pals["light"], out, resvg, work2)
        md += design.components_md(tokens, pals, out, resvg, work2)
        md += design.applications_md(tokens, pals, resvg, work2)
    md += design.accepted_md(tokens)

    md += ["## Open items", ""]
    md += [f"- {item}" for item in open_items] if open_items else ["None."]
    out.finish()

    date = today
    try:
        with open(BOARD, encoding="utf-8") as fh:
            m = re.search(r"^date: (\d{4}-\d{2}-\d{2})$", fh.read(), re.MULTILINE)
            date = m.group(1) if m else today
    except OSError:
        pass
    page = ["---", "title: Brand board", "status: draft", f"date: {date}",
            "related: [README.md, tokens.json, logo/README.md, ../imagery.md]", "style: reference", "---", "",
            "<!-- Generated from the brand inputs: do not edit; make the board again instead. -->",
            f"<!-- inputs: {inputs_hash()} -->", "", "# Brand board", "",
            "The palette, the fonts, the logo and sample images together, for the brand stop.", "", *md]
    with open(BOARD, "w", encoding="utf-8") as fh:
        fh.write("\n".join(page).rstrip("\n") + "\n")
    print(f"The brand board is written: {BOARD}, {len(out.written)} images in {IMAGES}/.")
    for item in open_items:
        print(f"open item: {item}")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--resvg", required=True)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("company")
    args = ap.parse_args(argv)
    os.chdir(args.company)
    if args.check:
        recorded = recorded_hash()
        if recorded is not None and recorded != inputs_hash():
            print(f"{BOARD}: out of date with its inputs; make the board again")
            return 1
        print("The brand board matches its inputs.")
        return 0
    try:
        make(args.resvg, datetime.date.today().isoformat())
    except Refused as e:
        print(f"brand.sh board: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
