"""The reference of step 6g (brand tools spec §5.8): the design system as products will build it.

    reference.py DIR

Writes DIR/docs/7-branding/identity/reference/, generated from tokens.json and never edited by hand:

- components.css: every component recipe and variant of the token contract (spec §5.5), built only from the variables of
  tokens.css, with their states. Products and checks read it.
- playground.html: the design system as one self-contained page (the tokens, the faces, the stylesheet and a sample site, with
  every variant), light and dark by the reader's setting. It cannot save anything: the choice is made.
- screenshots/: that page in light and dark at 390, 820 and 1280 pixels, from a headless browser, for people reviewing and for
  agents that read images.

brand.py reports the reference stale when its inputs change (tokens, the generated CSS, the fonts, the logo's SVGs).
"""
import base64
import json
import os
import re
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

IDENTITY = "docs/7-branding/identity"
REFERENCE = f"{IDENTITY}/reference"
WIDTHS = (390, 820, 1280)

COMPONENTS_CSS = """/* Generated from tokens.json: do not edit. The component recipes of the token contract, built only from the variables of
   tokens.css. */
/* inputs: INPUTS_HASH */

/* Buttons: filled, outlined, soft. A secondary button is outlined. */
.ds-btn { box-sizing: border-box; display: inline-flex; align-items: center; justify-content: center; gap: var(--space-1); min-height: var(--target); padding: 0 var(--space-4); border: 1.5px solid var(--color-accent); border-radius: var(--radius-button); font-family: var(--font-ui); font-size: var(--text-small); font-weight: 600; line-height: 1; cursor: pointer; text-decoration: none; transition: filter var(--motion-duration) var(--motion-easing), transform var(--motion-duration) var(--motion-easing); }
.ds-btn[data-variant="filled"] { background: var(--color-accent); color: var(--color-on-accent); }
.ds-btn[data-variant="outlined"] { background: transparent; color: var(--color-accent-text); }
.ds-btn[data-variant="soft"] { background: color-mix(in srgb, var(--color-accent) 16%, var(--color-bg)); border-color: color-mix(in srgb, var(--color-accent) 16%, var(--color-bg)); color: var(--color-accent-text); }
.ds-btn:hover { filter: brightness(.93); }
.ds-btn:active { transform: scale(.97); }
.ds-btn:focus-visible { outline: var(--focus-width) solid var(--focus-color); outline-offset: var(--focus-offset); }
.ds-btn[aria-disabled="true"], .ds-btn:disabled { opacity: .45; cursor: not-allowed; }

/* Links: underlined, colour (underlined on hover). */
.ds-link { color: var(--color-accent-text); }
.ds-link[data-variant="underlined"] { text-decoration: underline; text-underline-offset: 3px; }
.ds-link[data-variant="colour"] { text-decoration: none; }
.ds-link[data-variant="colour"]:hover { text-decoration: underline; text-underline-offset: 3px; }
.ds-link:focus-visible { outline: var(--focus-width) solid var(--focus-color); outline-offset: var(--focus-offset); }
.ds-link[aria-disabled="true"] { opacity: .45; cursor: not-allowed; }

/* Fields: a label above, a control, an error beneath. */
.ds-field { display: grid; gap: var(--space-1); font-family: var(--font-ui); font-size: var(--text-small); font-weight: 500; color: var(--color-text); }
.ds-field input, .ds-field textarea, .ds-field select { box-sizing: border-box; min-height: var(--target); padding: 0 var(--space-3); background: var(--color-surface); color: var(--color-text); border: 1px solid var(--color-border); border-radius: var(--radius-md); font-family: var(--font-body); font-size: var(--text-body); }
.ds-field input::placeholder, .ds-field textarea::placeholder { color: var(--color-muted); }
.ds-field input:focus-visible, .ds-field textarea:focus-visible, .ds-field select:focus-visible { outline: var(--focus-width) solid var(--focus-color); outline-offset: var(--focus-offset); }
.ds-field input[aria-invalid="true"] { border-color: var(--color-crit); }
.ds-field .ds-error { color: var(--color-crit); font-weight: 500; }
.ds-field input[aria-disabled="true"], .ds-field input:disabled { opacity: .45; cursor: not-allowed; }

/* Cards: bordered, surface, raised. */
.ds-card { box-sizing: border-box; padding: var(--space-3); border-radius: var(--radius-lg); display: grid; gap: var(--space-1); align-content: start; color: var(--color-text); }
.ds-card h3 { margin: 0; font-family: var(--font-heading); font-size: var(--text-h3); line-height: var(--leading-heading); }
.ds-card p { margin: 0; font-family: var(--font-body); }
.ds-card[data-variant="bordered"] { background: var(--color-bg); border: 1px solid var(--color-border); }
.ds-card[data-variant="surface"] { background: var(--color-surface); }
.ds-card[data-variant="raised"] { background: var(--color-surface); border: 1px solid var(--color-border); box-shadow: var(--shadow-card); }

/* Messages: tint, bar. The tone sets --c: the success, attention or error colour. */
.ds-message { box-sizing: border-box; padding: var(--space-2) var(--space-3); border-radius: var(--radius-md); font-family: var(--font-body); font-size: var(--text-small); display: flex; gap: var(--space-2); align-items: center; }
.ds-message[data-tone="ok"] { --c: var(--color-ok); }
.ds-message[data-tone="warn"] { --c: var(--color-warn); }
.ds-message[data-tone="crit"] { --c: var(--color-crit); }
.ds-message[data-variant="tint"] { background: color-mix(in srgb, var(--c) 10%, var(--color-bg)); color: var(--c); }
.ds-message[data-variant="bar"] { background: var(--color-surface); color: var(--c); border-left: 3px solid var(--c); border-radius: 0 var(--radius-md) var(--radius-md) 0; }

/* Navigation: left (logo at the start), centre (logo centred, links beneath). */
.ds-nav { box-sizing: border-box; display: flex; align-items: center; justify-content: space-between; gap: var(--space-3); flex-wrap: wrap; padding: var(--space-3) var(--space-4); background: var(--color-bg); border-bottom: 1px solid var(--color-border); font-family: var(--font-ui); font-size: var(--text-small); font-weight: 500; color: var(--color-text); }
.ds-nav[data-variant="centre"] { flex-direction: column; justify-content: center; }
.ds-nav a { color: var(--color-text); text-decoration: none; min-height: var(--target); display: inline-flex; align-items: center; }
.ds-nav a[aria-current="page"] { color: var(--color-accent-text); }
.ds-nav a:focus-visible { outline: var(--focus-width) solid var(--focus-color); outline-offset: var(--focus-offset); }

/* Images: borderless, rounded, framed. */
.ds-image { display: block; max-width: 100%; }
.ds-image[data-variant="rounded"] { border-radius: var(--radius-md); }
.ds-image[data-variant="framed"] { border: var(--space-1) solid var(--color-bg); box-shadow: 0 1px 3px color-mix(in srgb, var(--color-text) 25%, transparent); }

/* Icons: outline, filled. */
.ds-icon { width: 22px; height: 22px; color: var(--color-accent-text); }
.ds-icon[data-variant="outline"] path { fill: none; stroke: currentColor; stroke-width: 1.6; stroke-linejoin: round; }
.ds-icon[data-variant="filled"] path { fill: currentColor; stroke: none; }

@media (prefers-reduced-motion: reduce) { .ds-btn { transition: none; } .ds-btn:active { transform: none; } }
"""

PAGE_CSS = """
body { margin: 0; background: var(--color-bg); color: var(--color-text); font-family: var(--font-body); font-size: var(--text-body); line-height: var(--leading-body); }
main { max-width: 1100px; margin: 0 auto; }
section { padding: var(--space-5) var(--space-4); display: grid; gap: var(--space-3); border-top: 1px solid var(--color-border); }
h1, h2, h3 { margin: 0; }
h1 { font-family: var(--font-display); font-size: var(--text-display); line-height: var(--leading-display); font-weight: 500; }
h2 { font-family: var(--font-heading); font-size: var(--text-h2); line-height: var(--leading-heading); }
p { margin: 0; max-width: 62ch; }
.wordmark { font-family: var(--font-wordmark); font-size: var(--text-h2); }
.row { display: flex; flex-wrap: wrap; gap: var(--space-3); align-items: center; }
.grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: var(--space-3); }
.swatches { display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: var(--space-2); }
.swatch { display: grid; gap: var(--space-1); font-size: var(--text-small); }
.swatch i { display: block; height: var(--target); border-radius: var(--radius-sm); border: 1px solid var(--color-border); }
.ph { aspect-ratio: 4 / 3; background: color-mix(in srgb, var(--color-accent) 35%, var(--color-surface)); }
.logo-dark { display: none; }
@media (prefers-color-scheme: dark) { .logo-light { display: none; } .logo-dark { display: inline-block; } }
.logo svg { height: var(--target); width: auto; }
.small { font-size: var(--text-small); color: var(--color-muted); }
"""

STAR = "M11 1 L14 8 L21 8.5 L15.5 13 L17.5 20.5 L11 16.5 L4.5 20.5 L6.5 13 L1 8.5 L8 8 Z"


class Refused(Exception):
    pass


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def inline_svg(path):
    text = re.sub(r"<\?xml[^>]*\?>", "", read(path)).strip()
    return text.replace("<svg ", '<svg role="img" aria-label="The logo" ', 1)


def font_faces(brand, tokens):
    """@font-face rules with the web fonts embedded, so that the page is one file."""
    out = []
    for spec, source, web in brand.shipped_fonts(tokens):
        if not os.path.isfile(web):
            continue
        font = brand.open_font(source)
        lo, hi = brand.font_weights(font)
        with open(web, "rb") as fh:
            uri = "data:font/woff2;base64," + base64.b64encode(fh.read()).decode()
        out.append(f'@font-face {{ font-family: "{spec["family"]}"; src: url({uri}) format("woff2"); '
                   f'font-weight: {lo:g}{"" if lo == hi else f" {hi:g}"}; font-style: {"italic" if brand.font_is_italic(font) else "normal"}; '
                   "font-display: block; }")
    return out


def body(has_logo):
    e = lambda s: s.replace("&", "&amp;").replace("<", "&lt;")  # noqa: E731
    logo = ('<span class="logo"><span class="logo-light">LOGO_LIGHT</span><span class="logo-dark">LOGO_DARK</span></span>'
            if has_logo else '<span class="wordmark">Your company</span>')
    star = f'<svg class="ds-icon" data-variant="VARIANT" viewBox="0 0 22 22" aria-hidden="true"><path d="{STAR}"/></svg>'
    parts = [f'<nav class="ds-nav" data-variant="left">{logo}<span class="row"><a href="#a" aria-current="page">Home</a><a href="#a">Work</a><a href="#a">Contact</a></span></nav>',
             '<main>',
             '<section><h1>The design system, as products build it</h1><p>Every colour, type role and component below comes from the company\'s tokens. '
             'A product reads the tokens and the stylesheet, and looks like this.</p>'
             '<div class="row"><a class="ds-btn" data-variant="filled" href="#a">A button</a><a class="ds-link" data-variant="underlined" href="#a">A link</a></div></section>',
             '<section><h2>Colour</h2><div class="swatches">' + "".join(
                 f'<span class="swatch"><i style="background: var(--color-{k})"></i>{k}</span>' for k in
                 ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent", "ok", "warn", "crit")) + '</div></section>',
             '<section><h2>Type</h2><p class="wordmark">The wordmark</p><p style="font-family: var(--font-display); font-size: var(--text-display)">Display</p>'
             '<h2>Heading</h2><p>Body text, with <strong>bold</strong> and <em>italic</em> for emphasis.</p>'
             '<p style="font-family: var(--font-ui); font-size: var(--text-small)">Interface text: labels, buttons, menus.</p></section>',
             '<section><h2>Buttons</h2><div class="row">' + "".join(
                 f'<a class="ds-btn" data-variant="{v}" href="#a">{v.capitalize()}</a>' for v in ("filled", "outlined", "soft")) +
             '<a class="ds-btn" data-variant="filled" aria-disabled="true">Disabled</a></div></section>',
             '<section><h2>Links</h2><div class="row"><a class="ds-link" data-variant="underlined" href="#a">Underlined</a>'
             '<a class="ds-link" data-variant="colour" href="#a">Colour only</a></div></section>',
             '<section><h2>Fields</h2><div class="grid"><label class="ds-field">Your name<input type="text" placeholder="Name"></label>'
             '<label class="ds-field">Your email<input type="email" aria-invalid="true" placeholder="name@example.com"><span class="ds-error">Check the address.</span></label></div></section>',
             '<section><h2>Cards</h2><div class="grid">' + "".join(
                 f'<div class="ds-card" data-variant="{v}"><h3>{v.capitalize()}</h3><p>A card, as the company sets one apart.</p></div>' for v in ("bordered", "surface", "raised")) + '</div></section>',
             '<section><h2>Messages</h2><div class="grid">' + "".join(
                 f'<p class="ds-message" data-variant="{v}" data-tone="{t}">{e(m)}</p>' for v in ("tint", "bar")
                 for t, m in (("ok", "Your message has been sent."), ("warn", "Two dates are left."), ("crit", "Something went wrong."))) + '</div></section>',
             '<section><h2>Navigation</h2><nav class="ds-nav" data-variant="centre">' + logo + '<span class="row"><a href="#a" aria-current="page">Home</a><a href="#a">Work</a><a href="#a">Contact</a></span></nav></section>',
             '<section><h2>Images</h2><div class="grid">' + "".join(
                 f'<div class="ds-image ph" data-variant="{v}"></div>' for v in ("borderless", "rounded", "framed")) + '</div></section>',
             '<section><h2>Icons</h2><div class="row">' + star.replace("VARIANT", "outline") + star.replace("VARIANT", "filled") + '</div></section>',
             '</main>']
    return "\n".join(parts)


def build(company):
    checks = os.path.join(company, ".ouroboric", "checks")
    if not os.path.isfile(os.path.join(checks, "brand.py")):
        raise Refused(f"{company} is not a company folder: no .ouroboric/checks/brand.py")
    sys.path.insert(0, os.path.abspath(checks))
    import brand
    company = os.path.abspath(company)
    os.chdir(company)
    tokens = json.loads(read(f"{IDENTITY}/tokens.json"))
    for mode in ("light", "dark"):
        if not all(isinstance(tokens.get(mode, {}).get(k), str) and brand.HEX.match(tokens[mode][k]) for k in brand.COLOURS):
            raise Refused("the palette is not set yet: choose it first (the palette page, then the playground)")
    if not os.path.isfile(f"{IDENTITY}/tokens.css"):
        raise Refused("tokens.css is not made yet: run the company's brand check with tokens --write")
    digest = brand.reference_inputs_hash()
    css = COMPONENTS_CSS.replace("INPUTS_HASH", digest)
    logos = {m: f"{IDENTITY}/logo/{n}" for m, n in (("light", "logo.svg"), ("dark", "logo-dark.svg"))}
    has_logo = all(os.path.isfile(p) for p in logos.values())
    html = body(has_logo)
    if has_logo:
        html = html.replace("LOGO_LIGHT", inline_svg(logos["light"])).replace("LOGO_DARK", inline_svg(logos["dark"]))
    page = ("<!doctype html>\n<html lang=\"en\"><head><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>The design system</title>\n<style>\n/* Generated from tokens.json: do not edit. */\n"
            + read(f"{IDENTITY}/tokens.css") + "\n" + "\n".join(font_faces(brand, tokens)) + "\n" + css + PAGE_CSS +
            "</style></head><body>\n" + html + "\n</body></html>\n")
    os.makedirs(f"{REFERENCE}/screenshots", exist_ok=True)
    with open(f"{REFERENCE}/components.css", "w", encoding="utf-8") as fh:
        fh.write(css)
    with open(f"{REFERENCE}/playground.html", "w", encoding="utf-8") as fh:
        fh.write(page)
    shots(company)
    return digest


def shots(company):
    import pagecheck
    from playwright.sync_api import Error, sync_playwright
    options = pagecheck.launch_options(company)
    page_path = os.path.abspath(f"{REFERENCE}/playground.html")
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(**options)
        except Error as e:
            raise Refused(f"the headless browser could not start: {str(e).splitlines()[0]}")
        for mode in ("light", "dark"):
            ctx = browser.new_context(color_scheme=mode, reduced_motion="reduce", viewport={"width": 1280, "height": 900})
            for width in WIDTHS:
                page = ctx.new_page()
                page.set_viewport_size({"width": width, "height": 900})
                page.goto("file://" + page_path)
                page.wait_for_load_state("load")
                page.evaluate("document.fonts.ready.then(() => true)")
                page.screenshot(path=os.path.abspath(f"{REFERENCE}/screenshots/{mode}-{width}.png"), full_page=True)
                page.close()
            ctx.close()
        browser.close()


def main(argv):
    if len(argv) != 1:
        print("usage: brand.sh reference DIR", file=sys.stderr)
        return 2
    try:
        build(argv[0])
    except (Refused, pagecheck_cannot()) as e:
        print(f"brand.sh reference: {e}", file=sys.stderr)
        return 2
    print(f"The reference is written: {REFERENCE}/ (components.css, playground.html, screenshots/)")
    return 0


def pagecheck_cannot():
    import pagecheck
    return pagecheck.Cannot


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
