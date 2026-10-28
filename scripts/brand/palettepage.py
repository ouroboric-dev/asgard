"""The palette page of step 6b (brand tools spec §5.7): a guided page that shows one option at a time.

    palettepage.py DIR

Reads the latest checked round (brand.sh palette) and writes DIR/docs/7-branding/identity/choices/palette.html. The page
has a card for the choice of a preset, one for each colour role (what it is for, candidate values one at a time, or her
own), and a summary. A live panel shows the working palette in light and dark with the logo recoloured through masks of
its own colours, and checks every pair with the company's own rules, in words. She confirms with a reason; the choice
and the final palette are saved as choices/palette.json.
"""
import base64
import io
import json
import os
import re
import sys

from PIL import Image

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choicepage  # noqa: E402

ROLES = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent")
ROLE_TEXT = {
    "bg": ("Background", "The page background", "The colour behind everything, and the largest area of the site."),
    "surface": ("Surface", "A raised or inset area", "Cards, fields and the footer sit on it."),
    "border": ("Border", "Lines and outlines", "The lines between sections and the outline of cards and fields. It needs no minimum contrast."),
    "text": ("Text", "Text on a plain background", "Body text and headings. It must be easy to read on the background and on a surface."),
    "muted": ("Muted text", "Quieter text", "Captions and hints. It is quieter, and it must still be easy to read."),
    "accent": ("Accent", "The brand colour", "Buttons, the focus ring and the selected state. As a shape it needs at least 3:1 against the background."),
    "accent-text": ("Accent text", "The brand colour as text", "Links and outlined buttons. As text it needs at least 4.5:1 against the background."),
    "on-accent": ("Text on accent", "Text on a brand-colour fill", "The label inside a filled button. It needs at least 4.5:1 against the accent."),
}
LABEL = {"bg": "background", "surface": "surface", "border": "border", "text": "text", "muted": "muted text",
         "accent": "accent", "accent-text": "accent text", "on-accent": "text on accent", "ok": "success colour",
         "warn": "attention colour", "crit": "error colour"}
MAX_LOGO_PX = 360
CSS = """
.stage { display: grid; gap: 16px; }
.live { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.panel { border: 1px solid var(--line); border-radius: 12px; padding: 16px; background: var(--p-bg); color: var(--p-text); display: grid; gap: 8px; align-content: start; }
.panel h2 { color: var(--p-text); }
.panel .muted { color: var(--p-muted); margin: 0; }
.panel .row { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; }
.panel .btn { background: var(--p-accent); color: var(--p-on-accent); border-radius: 6px; padding: 6px 12px; font-weight: 600; }
.panel .link { color: var(--p-accent-text); text-decoration: underline; }
.panel .box { background: var(--p-surface); border: 1px solid var(--p-border); border-radius: 8px; padding: 8px; }
.swatches { display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; }
.swatches span { display: grid; gap: 2px; font-size: .72rem; }
.swatches i { display: block; height: 28px; border-radius: 4px; border: 1px solid var(--p-border); }
.logo { position: relative; width: 100%; max-width: 200px; }
.logo i { position: absolute; inset: 0; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-size: contain; mask-size: contain; -webkit-mask-position: left center; mask-position: left center; }
[data-card][hidden], [data-view][hidden] { display: none; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: grid; gap: 8px; }
.progress { color: var(--muted); font-size: .85rem; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tabs label, .options label { display: flex; gap: 6px; align-items: center; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: var(--bg); cursor: pointer; }
.options { display: grid; gap: 8px; }
.options code { font-size: .85rem; }
.nav { display: flex; gap: 8px; }
.nav button { font: inherit; border-radius: 8px; padding: 6px 12px; cursor: pointer; border: 1px solid var(--accent); background: transparent; color: var(--accent); }
.nav button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.words { margin: 0; padding-left: 1.2rem; font-size: .9rem; }
#warnings { list-style: none; padding: 0; margin: 0; display: grid; gap: 4px; }
#warnings li { background: var(--warn-bg); color: var(--warn); border-radius: 6px; padding: 4px 8px; font-size: .85rem; }
"""
JS = """
(function () {
  var d = JSON.parse(document.getElementById("data").textContent);
  var KEYS = d.keys;
  function lum(h) { var c = [1, 3, 5].map(function (i) { var v = parseInt(h.substr(i, 2), 16) / 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function shown(r) { return (Math.floor(r * 100) / 100).toFixed(2); }
  window.__rules = { rows: function (light, dark) {
    var out = [];
    [["light", light], ["dark", dark]].forEach(function (m) {
      d.pairs.forEach(function (p) { p.fgs.forEach(function (fg) { p.bgs.forEach(function (bg) {
        if (!m[1][fg] || !m[1][bg]) { return; }
        var r = ratio(m[1][fg], m[1][bg]);
        out.push({ mode: m[0], fg: fg, bg: bg, kind: p.kind, ratio: r, minimum: p.minimum,
                   result: p.minimum === null ? "reported" : (r >= p.minimum ? "passes" : "fails") });
      }); }); });
    });
    return out; } };
  window.__data = function () { return d; };
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-card]"));
  var at = 0;
  function showCard() {
    cards.forEach(function (c, i) { c.hidden = i !== at; });
    document.getElementById("progress").textContent = "Step " + (at + 1) + " of " + cards.length;
    document.getElementById("back").disabled = at === 0;
    document.getElementById("next").disabled = at === cards.length - 1;
  }
  document.getElementById("back").addEventListener("click", function () { if (at > 0) { at -= 1; showCard(); } });
  document.getElementById("next").addEventListener("click", function () { if (at < cards.length - 1) { at += 1; showCard(); } });
  function checked(name) { var r = document.querySelector('input[name="' + name + '"]:checked'); return r ? r.value : null; }
  function valid(h) { return /^#[0-9A-Fa-f]{6}$/.test(h || ""); }
  var kept = {};
  function working() {
    var preset = d.presets.filter(function (p) { return p.id === checked("preset"); })[0] || d.presets[0];
    var out = { light: Object.assign({}, preset.light), dark: Object.assign({}, preset.dark) };
    Object.keys(d.roles).forEach(function (role) {
      var pick = checked("role-" + role);
      var cand = d.roles[role].filter(function (c) { return c.id === pick; })[0];
      if (cand) { out.light[role] = cand.light; out.dark[role] = cand.dark; }
    });
    KEYS.forEach(function (role) {
      var f = document.querySelector('input[data-choice-field="custom-' + role + '"]');
      var parts = f && f.value ? f.value.split("|").map(function (s) { return s.trim(); }) : [];
      if (parts.length === 2 && valid(parts[0]) && valid(parts[1])) { out.light[role] = parts[0].toUpperCase(); out.dark[role] = parts[1].toUpperCase(); }
    });
    return { preset: preset, light: out.light, dark: out.dark };
  }
  function label(k) { return d.labels[k] || k; }
  function render() {
    var w = working();
    document.querySelectorAll("[data-view=preset]").forEach(function (v) { v.hidden = v.getAttribute("data-preset") !== w.preset.id; });
    ["light", "dark"].forEach(function (mode) {
      var el = document.getElementById("live-" + mode);
      Object.keys(w[mode]).forEach(function (k) { el.style.setProperty("--p-" + k, w[mode][k]); });
      el.style.setProperty("--logo-0", w[mode].text); el.style.setProperty("--logo-1", w[mode].accent); el.style.setProperty("--logo-2", w[mode].muted);
      var sw = el.querySelector(".swatches");
      sw.innerHTML = "";
      KEYS.forEach(function (k) { var s = document.createElement("span"); var i = document.createElement("i"); i.style.background = w[mode][k]; s.appendChild(i); s.appendChild(document.createTextNode(label(k) + " " + w[mode][k])); sw.appendChild(s); });
    });
    var rows = window.__rules.rows(w.light, w.dark), list = document.getElementById("words"), warn = document.getElementById("warnings");
    list.innerHTML = ""; warn.innerHTML = "";
    rows.forEach(function (r) {
      if (r.kind === "decorative") { return; }
      var li = document.createElement("li");
      li.textContent = r.mode + ": " + (r.fg === "on-accent" ? "text on an accent fill" : label(r.fg) + " on " + label(r.bg)) + ": " + shown(r.ratio) + ":1, needs at least " + r.minimum + ":1: " + r.result;
      list.appendChild(li);
      if (r.result === "fails") {
        var id = "contrast:" + r.mode + ":" + r.fg + "/" + r.bg;
        var wl = document.createElement("li");
        wl.textContent = r.mode + ": " + r.fg + " on " + r.bg + " is " + shown(r.ratio) + ":1. It needs at least " + r.minimum + ":1, so " + label(r.fg) + " is hard to see on the " + label(r.bg) + ". Keep it only if you accept that.";
        var cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!kept[id];
        cb.addEventListener("change", function () { kept[id] = cb.checked; });
        wl.appendChild(document.createTextNode(" ")); var lab = document.createElement("label"); lab.appendChild(cb); lab.appendChild(document.createTextNode(" keep it")); wl.appendChild(lab);
        warn.appendChild(wl);
      }
    });
    window.__choiceResult = function () {
      var x = working();
      return { preset: x.preset.id, light: x.light, dark: x.dark, kept: Object.keys(kept).filter(function (k) { return kept[k]; }) };
    };
  }
  document.querySelectorAll("input").forEach(function (i) { i.addEventListener("change", render); i.addEventListener("input", render); });
  showCard(); render();
  var stepRadios = document.querySelectorAll('[data-option-group="preset"] input');
  stepRadios.forEach(function (r) { r.addEventListener("change", function () { at = 0; showCard(); }); });
})();
"""


class Refused(Exception):
    pass


def latest_round(company):
    folder = os.path.join(company, choicepage.CHOICES)
    rounds = sorted(int(m.group(1)) for n in (os.listdir(folder) if os.path.isdir(folder) else [])
                    if (m := re.match(r"^palette-round-(\d+)\.json$", n)))
    if not rounds:
        raise Refused("there is no checked round of presets: run brand.sh palette first")
    with open(os.path.join(folder, f"palette-round-{rounds[-1]}.json"), encoding="utf-8") as fh:
        return json.load(fh), rounds[-1]


def logo_layers(company):
    """The logo's flat colours as masks, so the page can recolour it live; None when there is no logo yet."""
    path = os.path.join(company, "docs/7-branding/identity/logo/source/logo.png")
    if not os.path.isfile(path):
        return None
    im = Image.open(path).convert("RGBA")
    alpha = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    solid = Image.new("RGB", im.size, (0, 0, 0))
    solid.paste(im.convert("RGB"), mask=alpha)
    counts = {c: n for n, c in (solid.getcolors(1 << 24) or [])}
    counts[(0, 0, 0)] = counts.get((0, 0, 0), 0) - alpha.histogram()[0]
    opaque = alpha.histogram()[255]
    found = [c for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
             if n >= 0.005 * max(opaque, 1)][:3]
    if not found:
        return None
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in found for v in c])
    q = solid.quantize(palette=pal, dither=Image.Dither.NONE)
    scale = min(1.0, MAX_LOGO_PX / max(im.size))
    size = (max(1, round(im.width * scale)), max(1, round(im.height * scale)))
    layers = []
    for i in range(len(found)):
        on = Image.composite(q.point([255 if v == i else 0 for v in range(256)], "L"), Image.new("L", im.size, 0), alpha)
        mask = Image.new("RGBA", im.size, (0, 0, 0, 0))
        mask.putalpha(on)
        buf = io.BytesIO()
        mask.resize(size, Image.LANCZOS).save(buf, "PNG")
        layers.append("data:image/png;base64," + base64.b64encode(buf.getvalue()).decode())
    return {"aspect": round(im.width / im.height, 4), "layers": layers}


def words(row, label):
    minimum = f"needs at least {row['minimum']:g}:1" if row["minimum"] else "no minimum"
    pair = ("text on an accent fill" if row["fg"] == "on-accent"
            else f"{label[row['fg']]} on {label[row['bg']]}")
    return (f"{row['mode']}: {pair}: "
            f"{int(row['ratio'] * 100) / 100:.2f}:1, {minimum}: {row['result']}")


def build(company):
    import html as htmllib
    spec, rnd = latest_round(company)
    sys.path.insert(0, os.path.join(company, ".ouroboric", "checks"))
    import brand
    saved = choicepage.saved_choice(company, "palette")
    presets = spec["presets"]
    pick = ((saved or {}).get("choice") or {}).get("preset")
    first = next((p for p in presets if p["id"] == pick), presets[0])
    roles, dropped = {}, []
    for role, candidates in (spec.get("roles") or {}).items():
        kept = []
        for c in candidates:
            if c["light"].upper() == first["light"][role].upper() and c["dark"].upper() == first["dark"][role].upper():
                dropped.append(f"{role}: {c['id']} is the first preset's own value, so it is left out")
            else:
                kept.append({k: (v.upper() if k in ("light", "dark") else v) for k, v in c.items()})
        if kept:
            roles[role] = kept
    logo = logo_layers(company)
    e = htmllib.escape
    pairs = [{"fgs": list(f), "bgs": list(b), "kind": k, "minimum": m} for f, b, k, m in brand.PAIRS]
    data = {"round": rnd, "keys": list(ROLES), "labels": LABEL, "pairs": pairs, "roles": roles, "logo": logo,
            "presets": [{k: p.get(k) for k in ("id", "name", "mood", "light", "dark", "contrast", "result")} for p in presets]}
    tabs = "".join(
        f'<label><input type="radio" name="preset" value="{e(p["id"])}"{" checked" if p is first else ""}> {e(p["name"])}</label>'
        for p in presets)
    views = "".join(
        f'<div data-view="preset" data-preset="{e(p["id"])}"{"" if p is first else " hidden"}><h3>{e(p["name"])}</h3>'
        f'<p>{e(p.get("mood") or "")}</p><p>Checked before it is shown: <strong>{e(p["result"])}</strong>.</p>'
        f'<details><summary>{sum(1 for r in p["contrast"] if r["kind"] != "decorative")} contrast checks, in words</summary>'
        f'<ul class="words">{"".join("<li>" + e(words(r, LABEL)) + "</li>" for r in p["contrast"] if r["kind"] != "decorative")}</ul></details></div>'
        for p in presets)
    cards = [f'<section class="card" data-card="preset"><h2>Choose a palette</h2><p>Each palette was checked against the contrast '
             f'rules before you see it. Look at one at a time; the colours below change with it.</p>'
             f'<fieldset data-option-group="preset"><div class="tabs">{tabs}</div></fieldset>{views}</section>']
    for role in ROLES:
        short, title, why = ROLE_TEXT[role]
        cands = roles.get(role, [])
        opts = ('<label><input type="radio" name="role-%s" value="keep" checked> As the palette has it</label>' % role) + "".join(
            f'<label><input type="radio" name="role-{role}" value="{e(c["id"])}"> {e(c["name"])} '
            f'<code>{e(c["light"])} / {e(c["dark"])}</code></label>' for c in cands)
        cards.append(f'<section class="card" data-card="role-{role}" hidden><h2>{e(title)}</h2><p>{e(why)}</p>'
                     f'<fieldset data-option-group="role-{role}"><div class="options">{opts}</div></fieldset>'
                     f'<label>Your own value, light and dark, like <code>#0B5FCC | #6EA8FE</code> '
                     f'<input type="text" data-choice-field="custom-{role}" size="24"></label></section>')
    initial_rows = [r for r in first["contrast"] if r["kind"] != "decorative"]
    cards.append('<section class="card" data-card="summary" hidden><h2>Your palette</h2><p>This is the palette as you have '
                 'it now. Anything that fails a rule is listed; you may keep it, and it is written down with your reason.</p>'
                 f'<ul id="warnings"></ul><details><summary>All the contrast checks, in words</summary>'
                 f'<ul class="words" id="words">{"".join("<li>" + e(words(r, LABEL)) + "</li>" for r in initial_rows)}</ul></details></section>')
    logo_html, logo_css = "", ""
    if logo:
        logo_html = f'<div class="logo" style="aspect-ratio: {logo["aspect"]}">' + "".join(
            f'<i style="background: var(--logo-{i}); -webkit-mask-image: url({l}); mask-image: url({l})"></i>'
            for i, l in enumerate(logo["layers"])) + "</div>"
    panel = lambda mode: (f'<div class="panel" id="live-{mode}" style="--p-bg: {first[mode]["bg"]}; --p-surface: {first[mode]["surface"]}; '
                          f'--p-border: {first[mode]["border"]}; --p-text: {first[mode]["text"]}; --p-muted: {first[mode]["muted"]}; '
                          f'--p-accent: {first[mode]["accent"]}; --p-accent-text: {first[mode]["accent-text"]}; '
                          f'--p-on-accent: {first[mode]["on-accent"]}; --logo-0: {first[mode]["text"]}; --logo-1: {first[mode]["accent"]}; '
                          f'--logo-2: {first[mode]["muted"]}"><h2>{mode.capitalize()}</h2>{logo_html}'
                          '<p>A heading, then a few words of text.</p><p class="muted">Quieter text, for captions.</p>'
                          '<div class="row"><span class="btn">A button</span><span class="link">A link</span></div>'
                          '<div class="box">A card on a surface</div><div class="swatches"></div></div>')
    body = ('<div class="stage" data-preview>'
            f'<div class="live">{panel("light")}{panel("dark")}</div>'
            '<p class="progress" id="progress"></p>' + "".join(cards) +
            '<div class="nav"><button type="button" id="back">Back</button><button type="button" id="next">Next</button></div></div>')
    page = choicepage.skeleton("palette", "Your palette",
                               "Choose the colours of the company, one decision at a time. Every colour is shown in light and in dark, "
                               "and each rule is checked as you go.", body, data, saved, css=CSS, js=JS)
    out = os.path.join(company, choicepage.CHOICES)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "palette.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    return dropped


def main(argv):
    if len(argv) != 1:
        print("usage: brand.sh palette-page DIR", file=sys.stderr)
        return 2
    try:
        dropped = build(argv[0])
    except Refused as e:
        print(f"brand.sh palette-page: {e}", file=sys.stderr)
        return 2
    for line in dropped:
        print(f"note: {line}")
    print(f"The palette page is written: {choicepage.CHOICES}/palette.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
