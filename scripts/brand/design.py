"""The design system on the brand board (brand tools spec §5.4, with the design system process): the foundations, the
component sheet built from the recipes of the token contract (§5.5), logo usage, the kept exceptions and the first
applications. Imported by board.py; every function takes the parsed tokens and returns Markdown lines.

The message colours (ok, warn, crit) are not part of the brand: nothing here draws them.
"""
import math
import os
import re
import subprocess

from PIL import Image

COLOURS = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent")
ROLES = ("wordmark", "display", "heading", "body", "ui")
# The scale size each type role is set at on the board, and the line height it takes.
SCALE_FOR = {"wordmark": ("display", "display"), "display": ("display", "display"), "heading": ("h2", "heading"),
             "body": ("body", "body"), "ui": ("small", "body")}
LOGO_MIN_PX, MARK_MIN_PX = 96, 16
OFF_PALETTE = "#00B050"


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def n(value):
    return f"{value:g}"


def render(resvg, svg_text, work, name, *args):
    src, dst = os.path.join(work, f"{name}.svg"), os.path.join(work, f"{name}.png")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(svg_text)
    subprocess.run([resvg, *args, src, dst], check=True, capture_output=True)
    return Image.open(dst).convert("RGBA")


def font_files(spec, work, tag):
    """The role's font files as TTF or OTF paths: WOFF and WOFF2 are converted, which the renderer needs."""
    from fontTools.ttLib import TTFont
    folder = spec.get("files") and os.path.join("docs/7-branding/identity", spec["files"])
    if not folder or not os.path.isdir(folder):
        return []
    out = []
    for name in sorted(os.listdir(folder)):
        path = os.path.join(folder, name)
        if name.lower().endswith((".ttf", ".otf")):
            out.append(path)
        elif name.lower().endswith((".woff", ".woff2")):
            f = TTFont(path)
            f.flavor = None
            dst = os.path.join(work, f"{tag}-{os.path.splitext(name)[0]}.ttf")
            f.save(dst)
            out.append(dst)
    return out


def font_args(tokens, work):
    """The resvg arguments that load the company's own fonts; system fonts stay on when it ships none."""
    files = []
    for role in ROLES:
        spec = ((tokens.get("type") or {}).get("fonts") or {}).get(role) or {}
        files += [f for f in font_files(spec, work, f"sheet-{role}") if f not in files]
    return ["--skip-system-fonts"] + [a for f in files for a in ("--use-font-file", f)] if files else []


def mix(a, b, pct):
    """The colour `a` at `pct` percent over `b`."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x * pct / 100 + y * (100 - pct) / 100) for x, y in zip(ca, cb))


def md_cell(text):
    return str(text).replace("|", "\\|").replace("\n", " ")


# Foundations.

def parse_shadow(css):
    """(x, y, blur, spread, colour, alpha) for each layer of a box-shadow, or [] when it does not parse."""
    layers = []
    for part in re.split(r",\s*(?![^()]*\))", css):
        m = re.match(r"\s*(-?[\d.]+)(?:px)?\s+(-?[\d.]+)(?:px)?\s+([\d.]+)(?:px)?(?:\s+(-?[\d.]+)(?:px)?)?\s+rgba?\(([^)]+)\)\s*$", part)
        if not m:
            return []
        rgb = [float(v) for v in m.group(5).split(",")]
        alpha = rgb[3] if len(rgb) > 3 else 1.0
        layers.append((float(m.group(1)), float(m.group(2)), float(m.group(3)), float(m.group(4) or 0),
                       "#%02X%02X%02X" % tuple(round(v) for v in rgb[:3]), alpha))
    return layers


def space_svg(space, ink, bg):
    h = 30 * len(space) + 20
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 {h}" width="520" height="{h}">',
           f'<rect x="0" y="0" width="520" height="{h}" fill="{bg}"/>']
    for i, v in enumerate(space):
        y = 10 + 30 * i
        out += [f'<rect x="130" y="{y}" width="{v * 4:g}" height="20" fill="{ink}" fill-opacity="0.75"/>',
                f'<text x="10" y="{y + 15}" font-family="sans-serif" font-size="14" fill="{ink}">step {i + 1}: {n(v)} px</text>']
    out.append("</svg>")
    return "\n".join(out) + "\n"


def radius_svg(radius, ink, surface, bg):
    keys = [k for k in ("sm", "md", "lg", "button") if isinstance(radius.get(k), (int, float))]
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {130 * len(keys) + 10} 120" '
           f'width="{130 * len(keys) + 10}" height="120">',
           f'<rect x="0" y="0" width="{130 * len(keys) + 10}" height="120" fill="{bg}"/>']
    for i, k in enumerate(keys):
        x = 10 + 130 * i
        out += [f'<rect x="{x}" y="10" width="110" height="70" rx="{n(radius[k])}" fill="{surface}" stroke="{ink}" '
                'stroke-opacity="0.6" stroke-width="2"/>',
                f'<text x="{x}" y="105" font-family="sans-serif" font-size="14" fill="{ink}">{k}: {n(radius[k])} px</text>']
    out.append("</svg>")
    return "\n".join(out) + "\n"


def elevation_png(resvg, work, elevation, surface, bg):
    """Each elevation as a card over the background, its shadow drawn layer by layer and blurred."""
    names = [k for k in ("card", "overlay") if isinstance(elevation.get(k), str) and parse_shadow(elevation[k])]
    if not names:
        return None
    w = 300 * len(names) + 20
    defs, body = [], []
    for i, name in enumerate(names):
        x = 40 + 300 * i
        for j, (dx, dy, blur, spread, colour, alpha) in enumerate(parse_shadow(elevation[name])):
            defs.append(f'<filter id="b{i}{j}" x="-50%" y="-50%" width="200%" height="200%">'
                        f'<feGaussianBlur stdDeviation="{max(blur / 2, 0.01):g}"/></filter>')
            body.append(f'<rect x="{x + dx - spread:g}" y="{50 + dy - spread:g}" width="{200 + 2 * spread:g}" '
                        f'height="{110 + 2 * spread:g}" rx="6" fill="{colour}" fill-opacity="{alpha:g}" '
                        f'filter="url(#b{i}{j})"/>')
        body.append(f'<rect x="{x}" y="50" width="200" height="110" rx="6" fill="{surface}"/>')
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} 220" width="{w}" height="220">'
           f'<defs>{"".join(defs)}</defs><rect x="0" y="0" width="{w}" height="220" fill="{bg}"/>{"".join(body)}</svg>')
    return render(resvg, svg, work, "elevation")


def foundations_md(tokens, pal, out, resvg, work):
    md = ["## Foundations", ""]
    space = tokens.get("space") if isinstance(tokens.get("space"), list) else []
    radius = tokens.get("radius") if isinstance(tokens.get("radius"), dict) else {}
    elevation = tokens.get("elevation") if isinstance(tokens.get("elevation"), dict) else {}
    motion = tokens.get("motion") if isinstance(tokens.get("motion"), dict) else {}
    focus = tokens.get("focus") if isinstance(tokens.get("focus"), dict) else {}
    bps = tokens.get("breakpoints") if isinstance(tokens.get("breakpoints"), list) else []
    if not (space or radius or elevation or motion or focus):
        return md + ["The foundations are not set yet.", ""]
    rows = []
    if space:
        rows.append(("Spacing", ", ".join(f"{n(v)} px" for v in space)))
    if radius:
        names = {"sm": "small", "md": "medium", "lg": "large", "button": "button"}
        rows.append(("Corner radius", ", ".join(f"{names[k]} {n(radius[k])} px" for k in names if k in radius)))
    if elevation:
        rows.append(("Elevation", "; ".join(f"{k}: `{v}`" for k, v in elevation.items())))
    if motion:
        rows.append(("Motion", f"an entrance moves {n(motion.get('distance', 0))} px over {n(motion.get('duration', 0))} ms, "
                               f"easing `{motion.get('easing')}`; where the device asks for reduced motion: "
                               f"{motion.get('reduced', 'none')}"))
    if focus:
        rows.append(("Focus", f"a {n(focus.get('width', 0))} px ring in the {focus.get('role')} colour, "
                              f"{n(focus.get('offset', 0))} px from the element"))
    if tokens.get("target") is not None:
        rows.append(("Touch target", f"at least {n(tokens['target'])} px"))
    if bps:
        rows.append(("Breakpoints", ", ".join(f"{n(v)} px" for v in bps)))
    md += ["| Foundation | Value |", "| --- | --- |", *[f"| {a} | {md_cell(b)} |" for a, b in rows], ""]
    ink, bg, surface = pal.get("text", "#1A1A1A"), pal.get("bg", "#FFFFFF"), pal.get("surface", "#F5F5F5")
    if space:
        md += [f"![The spacing steps]({out.text('foundations-space.svg', space_svg(space, ink, bg))})", ""]
    if radius:
        md += [f"![The corner radii]({out.text('foundations-radius.svg', radius_svg(radius, ink, surface, bg))})", ""]
    shadow = elevation_png(resvg, work, elevation, surface, bg) if elevation else None
    if shadow is not None:
        md += [f"![The elevations, each as a card over the background]"
               f"({out.image('foundations-elevation.png', shadow)})", ""]
    return md


# Components.

COMMON = {
    "button": "radius-button, height at least target, label in the ui face at text-small, weight 600",
    "link": "text in accent-text",
    "field": "label in the ui face at text-small; control on surface, 1 px border, radius-md, height at least target, "
             "focus ring from the focus tokens",
    "card": "padding space-3, heading in the heading face at text-h3",
    "message": "padding space-2 and space-3, radius-md, text at text-small",
    "navigation": "padding space-3 and space-4, 1 px bottom border, links in the ui face at text-small, "
                  "each at least target high",
    "image": "a placeholder tone of accent over surface",
    "icon": "22 px, accent-text",
}
RECIPES = {
    "button": {"filled": "fill accent, label on-accent, border accent",
               "outlined": "no fill, label accent-text, border accent",
               "soft": "fill accent mixed 16% into bg, label accent-text"},
    "link": {"underlined": "always underlined, offset 3 px", "colour": "no underline until hover"},
    "field": {"standard": "placeholder in muted, value in the body face"},
    "card": {"bordered": "fill bg, 1 px border, no shadow", "surface": "fill surface, no border, no shadow",
             "raised": "fill surface, 1 px border, shadow-card"},
    "message": {"tint": "fill 10% of the message colour over bg, text in the message colour",
                "bar": "fill surface, 3 px bar in the message colour on the left"},
    "navigation": {"left": "logo at the start, links at the end", "centre": "logo centred, links beneath"},
    "image": {"borderless": "the image alone", "rounded": "radius-md", "framed": "a space-1 frame in bg, a soft shadow"},
    "icon": {"outline": "outlined strokes", "filled": "solid fill"},
}
KEYS = {"button": "button", "link": "link", "field": None, "card": "card", "message": "message",
        "navigation": "nav", "image": "image", "icon": "icons"}


def chosen(tokens, component):
    key = KEYS[component]
    if key is None:
        return "standard"
    value = (tokens.get("components") or {}).get(key)
    return value if isinstance(value, str) else None


def component_sheet(tokens, pal, mode, resvg, work, args):
    """The chosen variant of each component on the mode's palette, drawn from the recipes. The message component is
    drawn in the accent colour: the message colours stay off the board."""
    fonts = (tokens.get("type") or {}).get("fonts") or {}
    sizes = ((tokens.get("type") or {}).get("scale") or {}).get("sizes") or {}
    space = tokens.get("space") if isinstance(tokens.get("space"), list) and tokens.get("space") else [8, 12, 16, 24]
    radius = tokens.get("radius") if isinstance(tokens.get("radius"), dict) else {}
    focus = tokens.get("focus") if isinstance(tokens.get("focus"), dict) else {}
    target = tokens.get("target") if isinstance(tokens.get("target"), (int, float)) else 44
    elevation = tokens.get("elevation") if isinstance(tokens.get("elevation"), dict) else {}
    s = lambda i: space[min(i - 1, len(space) - 1)]  # noqa: E731 - space-1 .. space-n
    fam = lambda role: esc(((fonts.get(role) or {}).get("family")) or "sans-serif") + ", sans-serif"  # noqa: E731
    small, body, h3 = sizes.get("small", 14), sizes.get("body", 16), sizes.get("h3", 20)
    c = pal
    rb, rm, rl = radius.get("button", 4), radius.get("md", 4), radius.get("lg", 6)
    parts, defs = [], []

    def text(x, y, content, role, size, fill, weight=400, anchor="start", deco=""):
        parts.append(f'<text x="{n(x)}" y="{n(y)}" font-family="{fam(role)}" font-size="{n(size)}" font-weight="{weight}" '
                     f'fill="{fill}" text-anchor="{anchor}"{deco}>{esc(content)}</text>')

    def label(y, name, variant):
        text(24, y, f"{name}: {variant}", "ui", 13, c["muted"], 500)

    y = 40
    text(24, y, f"{mode.capitalize()} mode", "heading", h3, c["text"], 600)
    y += 40

    variant = chosen(tokens, "button")
    label(y, "button", variant)
    y += 14
    for i, (word, off) in enumerate((("Primary", 1.0), ("Secondary", 1.0), ("Disabled", 0.45))):
        x = 24 + i * 170
        kind = variant if i != 1 else "outlined"
        fill = {"filled": c["accent"], "outlined": "none", "soft": mix(c["accent"], c["bg"], 16)}.get(kind, c["accent"])
        stroke = c["accent"] if kind != "soft" else fill
        ink = c["on-accent"] if kind == "filled" else c["accent-text"]
        parts.append(f'<g opacity="{off}"><rect x="{x}" y="{y}" width="150" height="{n(target)}" rx="{n(rb)}" '
                     f'fill="{fill}" stroke="{stroke}" stroke-width="1.5"/></g>')
        text(x + 75, y + target / 2 + small * 0.35, word, "ui", small, ink, 600, "middle")
    y += target + 36

    label(y, "link", chosen(tokens, "link"))
    y += 28
    deco = ' text-decoration="underline"' if chosen(tokens, "link") == "underlined" else ""
    parts.append(f'<text x="24" y="{n(y)}" font-family="{fam("body")}" font-size="{n(body)}" fill="{c["text"]}">'
                 f'Read the full story on the <tspan fill="{c["accent-text"]}"{deco}>about page</tspan>.</text>')
    y += 36

    label(y, "field", "standard")
    y += 22
    text(24, y, "Label", "ui", small, c["text"], 500)
    y += 8
    fw, fo = focus.get("width", 2), focus.get("offset", 2)
    ring = c.get(focus.get("role"), c["accent"])
    for i, (shown, ringed) in enumerate((("Placeholder", False), ("A value", True))):
        x = 24 + i * 350
        parts.append(f'<rect x="{x}" y="{y}" width="320" height="{n(target)}" rx="{n(rm)}" fill="{c["surface"]}" '
                     f'stroke="{c["border"]}" stroke-width="1"/>')
        if ringed:
            parts.append(f'<rect x="{x - fo - fw / 2:g}" y="{y - fo - fw / 2:g}" width="{320 + 2 * fo + fw:g}" '
                         f'height="{target + 2 * fo + fw:g}" rx="{n(rm + fo)}" fill="none" stroke="{ring}" '
                         f'stroke-width="{n(fw)}"/>')
        text(x + s(3), y + target / 2 + body * 0.35, shown, "body", body, c["muted"] if not ringed else c["text"])
    y += target + 40

    variant = chosen(tokens, "card")
    label(y, "card", variant)
    y += 14
    shadow = parse_shadow(elevation.get("card", "")) if variant == "raised" else []
    for j, (dx, dy, blur, spread, colour, alpha) in enumerate(shadow):
        defs.append(f'<filter id="c{j}" x="-50%" y="-50%" width="200%" height="200%">'
                    f'<feGaussianBlur stdDeviation="{max(blur / 2, 0.01):g}"/></filter>')
        parts.append(f'<rect x="{24 + dx - spread:g}" y="{y + dy - spread:g}" width="{300 + 2 * spread:g}" '
                     f'height="{140 + 2 * spread:g}" rx="{n(rl)}" fill="{colour}" fill-opacity="{alpha:g}" filter="url(#c{j})"/>')
    fill = c["bg"] if variant == "bordered" else c["surface"]
    stroke = "none" if variant == "surface" else c["border"]
    parts.append(f'<rect x="24" y="{y}" width="300" height="140" rx="{n(rl)}" fill="{fill}" stroke="{stroke}" stroke-width="1"/>')
    text(24 + s(3), y + s(3) + h3, "Card title", "heading", h3, c["text"], 600)
    text(24 + s(3), y + s(3) + h3 + 28, "A short line of text in the", "body", body, c["text"])
    text(24 + s(3), y + s(3) + h3 + 28 + body * 1.5, "body face, on the card.", "body", body, c["muted"])
    y += 140 + 40

    variant = chosen(tokens, "message")
    label(y, "message", variant)
    y += 14
    if variant == "bar":
        parts.append(f'<rect x="24" y="{y}" width="460" height="{target}" fill="{c["surface"]}"/>'
                     f'<rect x="24" y="{y}" width="3" height="{target}" fill="{c["accent"]}"/>')
    else:
        parts.append(f'<rect x="24" y="{y}" width="460" height="{target}" rx="{n(rm)}" fill="{mix(c["accent"], c["bg"], 10)}"/>')
    text(24 + s(3), y + target / 2 + small * 0.35, "Your message has been sent.", "ui", small, c["accent-text"])
    y += target + 40

    variant = chosen(tokens, "navigation")
    label(y, "navigation", variant)
    y += 14
    bar = target + 2 * s(3) + (30 if variant == "centre" else 0)
    parts.append(f'<rect x="24" y="{y}" width="900" height="{n(bar)}" fill="{c["bg"]}"/>'
                 f'<rect x="24" y="{y + bar - 1}" width="900" height="1" fill="{c["border"]}"/>')
    if variant == "centre":
        text(474, y + s(3) + 20, "Logo", "ui", body, c["text"], 600, "middle")
        for i, w in enumerate(("Home", "Work", "About")):
            text(474 + (i - 1) * 90, y + bar - s(3) - 4, w, "ui", small, c["text"] if i else c["accent-text"], 500, "middle")
    else:
        text(24 + s(4), y + bar / 2 + 6, "Logo", "ui", body, c["text"], 600)
        for i, w in enumerate(("Home", "Work", "About")):
            text(924 - s(4) - (2 - i) * 90, y + bar / 2 + 5, w, "ui", small, c["text"] if i else c["accent-text"], 500, "end")
    y += bar + 36

    variant = chosen(tokens, "image")
    label(y, "image", variant)
    y += 14
    tone = mix(c["accent"], c["surface"], 40)
    for i in range(3):
        x = 24 + i * 170
        if variant == "framed":
            parts.append(f'<rect x="{x}" y="{y}" width="150" height="110" fill="{c["bg"]}" stroke="{c["border"]}" stroke-width="1"/>'
                         f'<rect x="{x + s(1)}" y="{y + s(1)}" width="{150 - 2 * s(1)}" height="{110 - 2 * s(1)}" fill="{tone}"/>')
        else:
            parts.append(f'<rect x="{x}" y="{y}" width="150" height="110" rx="{n(rm) if variant == "rounded" else 0}" fill="{tone}"/>')
    y += 110 + 36

    variant = chosen(tokens, "icon")
    label(y, "icon", variant)
    y += 14
    star = "M11 1 L14 8 L21 8.5 L15.5 13 L17.5 20.5 L11 16.5 L4.5 20.5 L6.5 13 L1 8.5 L8 8 Z"
    for i in range(4):
        fill = c["accent-text"] if variant == "filled" else "none"
        parts.append(f'<g transform="translate({24 + i * 50},{y})"><path d="{star}" fill="{fill}" stroke="{c["accent-text"]}" '
                     'stroke-width="1.6" stroke-linejoin="round"/></g>')
    y += 22 + 30
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 948 {y}" width="948" height="{y}">'
           f'<defs>{"".join(defs)}</defs><rect x="0" y="0" width="948" height="{y}" fill="{c["bg"]}"/>{"".join(parts)}</svg>')
    return render(resvg, svg, work, f"components-{mode}", *args)


def components_md(tokens, pals, out, resvg, work):
    md = ["## Components", ""]
    if not all(all(k in pals[m] for k in COLOURS) for m in ("light", "dark")):
        return md + ["The palette is not complete yet, so the components are not drawn.", ""]
    args = font_args(tokens, work)
    for mode in ("light", "dark"):
        sheet = component_sheet(tokens, pals[mode], mode, resvg, work, args)
        md += [f"![The components in {mode} mode]({out.image(f'components-{mode}.png', sheet)})", ""]
    md += ["| Component | Variant | Built from |", "| --- | --- | --- |"]
    for comp in KEYS:
        variant = chosen(tokens, comp)
        recipe = RECIPES[comp].get(variant, "a variant the token contract does not list") if variant else "not chosen yet"
        md.append(f"| {comp} | {variant or 'not chosen'} | {md_cell(recipe)}; {COMMON[comp]} |")
    md.append("")
    return md


# Logo usage.

def logo_parts(path):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    x, y, w, h = (float(v) for v in re.search(r'viewBox="([^"]+)"', text).group(1).split())
    return x, y, w, h, re.findall(r"<path\b[^>]*/>", text)


def mark_width(logo_h, mark_path):
    """The mark's width when it stands as tall as the logo, or half the logo's height when there is no mark."""
    if mark_path and os.path.isfile(mark_path):
        _, _, mw, mh, _ = logo_parts(mark_path)
        return logo_h * mw / mh, True
    return logo_h / 2, False


def clear_space_svg(logo, bg, ink, clear):
    x, y, w, h, paths = logo_parts(logo)
    m = 0.12 * max(w, h)
    W, H = w + 2 * clear + 2 * m, h + 2 * clear + 2 * m + 0.2 * h
    return "\n".join([
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W:g} {H:g}" width="480" height="{480 * H / W:.0f}">',
        f'<rect x="0" y="0" width="{W:g}" height="{H:g}" fill="{bg}"/>',
        f'<rect x="{m:g}" y="{m:g}" width="{w + 2 * clear:g}" height="{h + 2 * clear:g}" fill="none" stroke="{ink}" '
        f'stroke-opacity="0.6" stroke-width="{0.01 * max(w, h):g}" stroke-dasharray="{0.04 * max(w, h):g}"/>',
        f'<rect x="{m + clear:g}" y="{m + clear:g}" width="{w:g}" height="{h:g}" fill="none" stroke="{ink}" '
        f'stroke-opacity="0.25" stroke-width="{0.005 * max(w, h):g}"/>',
        f'<g transform="translate({m + clear - x:g},{m + clear - y:g})">', *paths, "</g>",
        f'<text x="{m:g}" y="{H - 0.06 * h:g}" font-family="sans-serif" font-size="{0.12 * h:g}" fill="{ink}">'
        "clear space on every side</text>", "</svg>"]) + "\n"


def misuse_svg(logo, kind, bg, accent):
    x, y, w, h, paths = logo_parts(logo)
    s = min(200 / w, 100 / h)
    cx, cy = 180, 120
    tile_bg = accent if kind == "low-contrast" else bg
    joined = "\n".join(re.sub(r'fill="[^"]*"', f'fill="{OFF_PALETTE}"', p) for p in paths) if kind == "recoloured" \
        else "\n".join(paths)
    sx, sy = {"stretched": (1.5 * s, 0.6 * s)}.get(kind, (s, s))
    turn = " rotate(-18)" if kind == "rotated" else ""
    return "\n".join([
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 360 240" width="360" height="240">',
        f'<rect x="0" y="0" width="360" height="240" fill="{tile_bg}"/>',
        f'<g transform="translate({cx},{cy}){turn} scale({sx:g},{sy:g}) translate({-(x + w / 2):g},{-(y + h / 2):g})">',
        joined, "</g>", "</svg>"]) + "\n"


def minimum_png(resvg, work, logo, mark, bg):
    tile = Image.new("RGBA", (420, 130), bg)
    for src, width, at in ((logo, LOGO_MIN_PX, (20, 20)), (mark, MARK_MIN_PX, (180, 20)), (mark, 32, (240, 20))):
        if src and os.path.isfile(src):
            with open(src, encoding="utf-8") as fh:
                art = render(resvg, fh.read(), work, f"min-{width}", "-w", str(width))
            tile.alpha_composite(art, at)
    return tile


def logo_usage_md(tokens, pals, out, resvg, work):
    ident = "docs/7-branding/identity/logo"
    logo = f"{ident}/logo.svg"
    md = ["### Logo usage", ""]
    if not os.path.isfile(logo):
        return md + ["The logo is not processed yet, so its usage is not drawn.", ""]
    mark = f"{ident}/mark.svg"
    light = pals["light"]
    bg, ink, accent = light.get("bg", "#FFFFFF"), light.get("text", "#1A1A1A"), light.get("accent", "#888888")
    _, _, _, lh, _ = logo_parts(logo)
    clear, with_mark = mark_width(lh, mark)
    md += [("**Clear space.** Keep the width of the mark free on every side of the logo, so nothing crowds it."
            if with_mark else
            "**Clear space.** Keep half the logo's height free on every side of the logo, so nothing crowds it."), "",
           f"![The clear space around the logo]({out.text('logo-clear-space.svg', clear_space_svg(logo, bg, ink, clear))})", ""]
    md += [f"**Minimum size.** The logo is never shown narrower than {LOGO_MIN_PX} pixels"
           + (f", and the mark never smaller than {MARK_MIN_PX} pixels." if os.path.isfile(mark) else "."), ""]
    for mode, suffix in (("light", ""), ("dark", "-dark")):
        tile_bg = pals[mode].get("bg", "#FFFFFF" if mode == "light" else "#121212")
        art = f"{ident}/logo{suffix}.svg"
        art_mark = f"{ident}/mark{suffix}.svg"
        tile = minimum_png(resvg, work, art if os.path.isfile(art) else logo, art_mark if os.path.isfile(art_mark) else None,
                           tile_bg)
        md += [f"![The logo and the mark at their minimum sizes, {mode}]({out.image(f'logo-minimum-{mode}.png', tile)})", ""]
    md += ["**Misuse.**", ""]
    words = {"stretched": "Do not stretch or squash the logo.", "rotated": "Do not rotate the logo.",
             "recoloured": "Do not recolour the logo outside the palette.",
             "low-contrast": "Do not place the logo on a colour it does not stand out from."}
    for kind, sentence in words.items():
        md += [f"![A misuse of the logo: {kind}]({out.text(f'misuse-{kind}.svg', misuse_svg(logo, kind, bg, accent))})", "",
               sentence, ""]
    return md


# Accepted exceptions.

def accepted_md(tokens):
    md = ["## Accepted exceptions", ""]
    entries = [e for e in (tokens.get("accepted") or []) if isinstance(e, dict)]
    if not entries:
        return md + ["No exception is kept.", ""]
    md += ["The founder chose to keep these, with her reasons. Each names one check on one value; if the value changes, "
           "the check applies again.", "", "| Check | Value | Reason | By | Date |", "| --- | --- | --- | --- | --- |"]
    md += [f"| {md_cell(e.get('check'))} | {md_cell(e.get('value'))} | {md_cell(e.get('reason'))} | "
           f"{md_cell(e.get('by'))} | {md_cell(e.get('date'))} |" for e in entries]
    return md + [""]


# Applications.

APPLICATIONS = "docs/7-branding/identity/applications"


def fit(resvg, work, svg_path, name, box):
    with open(svg_path, encoding="utf-8") as fh:
        text = fh.read()
    _, _, w, h, _ = logo_parts(svg_path)
    key = ("-w", str(box[0])) if w / h >= box[0] / box[1] else ("-h", str(box[1]))
    return render(resvg, text, work, name, *key)


def centred(im, size, bg):
    tile = Image.new("RGBA", size, bg + "FF")
    tile.alpha_composite(im, ((size[0] - im.width) // 2, (size[1] - im.height) // 2))
    return tile.convert("RGB")


def applications_md(tokens, pals, resvg, work):
    md = ["## Applications", ""]
    ident = "docs/7-branding/identity/logo"
    logo = f"{ident}/logo.svg"
    if not os.path.isfile(logo):
        return md + ["The logo is not processed yet, so the applications are not made.", ""]
    mark = f"{ident}/mark.svg" if os.path.isfile(f"{ident}/mark.svg") else logo
    pal = pals["light"]
    bg = pal.get("bg", "#FFFFFF")
    os.makedirs(APPLICATIONS, exist_ok=True)
    centred(fit(resvg, work, mark, "profile", (620, 620)), (1080, 1080), bg).save(f"{APPLICATIONS}/profile-picture.png")
    centred(fit(resvg, work, logo, "preview", (760, 360)), (1200, 630), bg).save(f"{APPLICATIONS}/link-preview.png")
    sig = fit(resvg, work, logo, "signature", (320, 160))
    sig.save(f"{APPLICATIONS}/signature-logo@2x.png")
    fonts = (tokens.get("type") or {}).get("fonts") or {}
    ui = fonts.get("ui") or {}
    stack = ", ".join(x for x in (f"'{ui['family']}'" if ui.get("family") else None,
                                  ui.get("fallback") or "Helvetica, Arial, sans-serif") if x)
    html = f"""<!-- Generated from the brand inputs: do not edit; make the board again instead. -->
<table cellpadding="0" cellspacing="0" style="font-family: {stack}; font-size: 14px; color: {pal.get('text', '#1A1A1A')};">
  <tr><td style="padding-bottom: 8px;"><strong style="font-size: 16px;">Your name</strong><br><span style="color: {pal.get('muted', '#555555')};">Your role</span></td></tr>
  <tr><td><img src="signature-logo@2x.png" width="{sig.width // 2}" alt="Logo" style="display: block; border: 0;"></td></tr>
  <tr><td style="padding-top: 8px;"><a href="https://example.com" style="color: {pal.get('accent-text', '#0B5FCC')};">example.com</a></td></tr>
</table>
"""
    with open(f"{APPLICATIONS}/email-signature.html", "w", encoding="utf-8") as fh:
        fh.write(html)
    return md + [
        "The first places the brand appears, made from the logo and the palette. Copy each one from the folder "
        "`applications/` next to this page.", "",
        "- **Profile picture**, square, 1080 pixels, from the mark: "
        "![The profile picture](applications/profile-picture.png)",
        "- **Link preview**, 1200 by 630 pixels, shown when a link is shared in a chat: "
        "![The link preview](applications/link-preview.png)",
        "- **Email signature**: [email-signature.html](applications/email-signature.html), with the logo at twice its "
        "size so it stays sharp on high-resolution screens: ![The signature logo](applications/signature-logo@2x.png)", ""]
