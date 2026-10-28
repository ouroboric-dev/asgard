"""The foundations page of step 6e (brand tools spec §5.7): a guided page, one foundation at a time, each shown and not
described.

    foundationspage.py DIR [CANDIDATES.json]

A card for each foundation (body size, type scale, line height, spacing, corners, depth, motion, focus, touch size,
breakpoints), each with a few candidates; a look sets them all at once. One live sample shows every choice together: text
at its sizes, a card with a button and a field, depth, motion played on a loop and still where the device asks for reduced
motion, and a ruler of screen widths with the usual devices and a width slider. The company's rules are checked as she
chooses, in words (the same minimums as brand.py, and the focus colour against her saved palette). Her choice and the
final foundations, with the keys of the token contract, are saved as choices/foundations.json.

The default candidates are scripts/brand/foundations.json (ASGARD_FOUNDATIONS changes the file). CANDIDATES.json may replace the
options of any foundation: {"foundations": {"base": [{"id": "16", "name": "16 px", "note": "...", "v": 16}]}}.
"""
import json
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choicepage  # noqa: E402

NEUTRAL = {"light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "border": "#DDDDDD", "text": "#1A1A1A", "muted": "#555555",
                     "accent": "#0B5FCC", "on-accent": "#FFFFFF"},
           "dark": {"bg": "#121212", "surface": "#1E1E1E", "border": "#333333", "text": "#EDEDED", "muted": "#B0B0B0",
                    "accent": "#6EA8FE", "on-accent": "#121212"}}
DEVICES = [[390, "phone"], [820, "tablet"], [1280, "laptop"], [1440, "desktop"]]
CSS = """
:root { --p-bg: __LBG__; --p-surface: __LSURFACE__; --p-border: __LBORDER__; --p-text: __LTEXT__; --p-muted: __LMUTED__; --p-accent: __LACCENT__; --p-on-accent: __LONACCENT__; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --p-bg: __DBG__; --p-surface: __DSURFACE__; --p-border: __DBORDER__; --p-text: __DTEXT__; --p-muted: __DMUTED__; --p-accent: __DACCENT__; --p-on-accent: __DONACCENT__; } }
.stage { display: grid; gap: 16px; }
.sample { background: var(--p-bg); color: var(--p-text); border: 1px solid var(--line); border-radius: 12px; padding: var(--s4); display: grid; gap: var(--s3); }
.sample .display { font-size: var(--fs-display); line-height: var(--lh-display); margin: 0; font-weight: 600; }
.sample .h1 { font-size: var(--fs-h1); line-height: var(--lh-heading); margin: 0; font-weight: 600; }
.sample .h2 { font-size: var(--fs-h2); line-height: var(--lh-heading); margin: 0; font-weight: 600; }
.sample .h3 { font-size: var(--fs-h3); line-height: var(--lh-heading); margin: 0; font-weight: 600; }
.sample .body { font-size: var(--fs-body); line-height: var(--lh-body); margin: 0; max-width: 62ch; }
.sample .small { font-size: var(--fs-small); color: var(--p-muted); margin: 0; }
.sample .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: var(--s4); align-items: start; }
.sample .card { background: var(--p-surface); border: 1px solid var(--p-border); border-radius: var(--r-lg); padding: var(--s4); box-shadow: var(--sh-card); display: grid; gap: var(--s3); }
.sample .btn { background: var(--p-accent); color: var(--p-on-accent); border: 0; border-radius: var(--r-button); min-height: var(--target); padding: 0 var(--s4); font: 600 var(--fs-small) system-ui, sans-serif; width: max-content; }
.sample .btn.focused, .sample .field.focused { outline: var(--focus-w) solid var(--focus-c); outline-offset: var(--focus-o); }
.sample .field { min-height: var(--target); border: 1px solid var(--p-border); border-radius: var(--r-md); background: var(--p-bg); color: var(--p-muted); display: flex; align-items: center; padding: 0 var(--s3); font-size: var(--fs-small); }
.sample .overlay { background: var(--p-surface); border-radius: var(--r-lg); padding: var(--s3) var(--s4); box-shadow: var(--sh-overlay); width: max-content; font-size: var(--fs-small); }
.motion { display: grid; gap: 6px; }
.track { height: 36px; position: relative; background: var(--p-surface); border-radius: 8px; overflow: hidden; }
#motion-ball { position: absolute; top: 6px; left: 8px; width: 24px; height: 24px; border-radius: 50%; background: var(--p-accent); animation: glide var(--m-loop) var(--m-ease) infinite alternate; }
@keyframes glide { from { transform: translateX(0); opacity: .6; } to { transform: translateX(calc(var(--m-dist) * 6 + 8px)); opacity: 1; } }
@media (prefers-reduced-motion: reduce) { #motion-ball { animation: none; } }
#curve { width: 120px; height: 60px; border: 1px solid var(--p-border); border-radius: 6px; background: var(--p-bg); }
.ruler { position: relative; height: 56px; background: var(--p-surface); border-radius: 8px; border: 1px solid var(--p-border); }
.ruler .tick { position: absolute; top: 6px; bottom: 6px; border-left: 2px solid var(--p-accent); padding-left: 4px; font-size: .75rem; }
.ruler .dev { position: absolute; bottom: 4px; font-size: .68rem; color: var(--p-muted); transform: translateX(-50%); }
.cells { display: grid; grid-template-columns: repeat(var(--cols), 1fr); gap: 4px; }
.cells span { background: var(--p-accent); opacity: .5; border-radius: 4px; height: 20px; }
[data-card][hidden] { display: none; }
.card.q { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: grid; gap: 8px; }
.progress { color: var(--muted); font-size: .85rem; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tabs label { display: flex; gap: 6px; align-items: center; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: var(--bg); cursor: pointer; }
.note { color: var(--muted); font-size: .85rem; margin: 0; }
.nav { display: flex; gap: 8px; }
.nav button { font: inherit; border-radius: 8px; padding: 6px 12px; cursor: pointer; border: 1px solid var(--accent); background: transparent; color: var(--accent); }
#warnings { list-style: none; padding: 0; margin: 0; display: grid; gap: 4px; }
#warnings li { background: var(--warn-bg); color: var(--warn); border-radius: 6px; padding: 4px 8px; font-size: .85rem; }
"""
JS = """
(function () {
  var d = JSON.parse(document.getElementById("data").textContent);
  var cards = Array.prototype.slice.call(document.querySelectorAll("[data-card]")), at = 0;
  function showCard() {
    cards.forEach(function (c, i) { c.hidden = i !== at; });
    document.getElementById("progress").textContent = "Step " + (at + 1) + " of " + cards.length;
    document.getElementById("back").disabled = at === 0;
    document.getElementById("next").disabled = at === cards.length - 1;
  }
  document.getElementById("back").addEventListener("click", function () { if (at > 0) { at -= 1; showCard(); } });
  document.getElementById("next").addEventListener("click", function () { if (at < cards.length - 1) { at += 1; showCard(); } });
  function checked(name) { var r = document.querySelector('input[name="' + name + '"]:checked'); return r ? r.value : null; }
  function cand(id) { var f = d.foundations.filter(function (x) { return x.id === id; })[0]; var v = checked("f-" + id); return f.cands.filter(function (c) { return String(c.id) === v; })[0] || f.cands[0]; }
  function lum(h) { var c = [1, 3, 5].map(function (i) { var v = parseInt(h.substr(i, 2), 16) / 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function px(n) { return n + "px"; }
  var kept = {};
  function values() {
    var base = cand("base").v, r = cand("ratio").v, lead = cand("leading").v;
    function step(n) { return Math.round(base * Math.pow(r, n) * 10) / 10; }
    var sizes = { small: Math.max(14, step(-1)), body: base, h3: step(1), h2: step(2), h1: step(3), display: step(4) };
    var mo = cand("motion").v, fo = cand("focus").v, bp = cand("breakpoints");
    return { sizes: sizes, leading: lead, space: cand("space").v, radius: cand("radius").v, elevation: cand("elevation").v,
             motion: { distance: mo.distance, duration: mo.duration, easing: mo.easing, reduced: "none" }, focus: fo,
             target: cand("target").v, breakpoints: bp.v, cols: bp.cols, base: base, ratio: r };
  }
  function curve(easing) {
    var m = /cubic-bezier\\(([^)]+)\\)/.exec(easing);
    var p = m ? m[1].split(",").map(Number) : [0, 0, 1, 1];
    return "M0,60 C" + (p[0] * 120) + "," + (60 - p[1] * 60) + " " + (p[2] * 120) + "," + (60 - p[3] * 60) + " 120,0";
  }
  function render() {
    var v = values(), s = document.getElementById("stage").style;
    ["small", "body", "h3", "h2", "h1", "display"].forEach(function (k) { s.setProperty("--fs-" + k, px(v.sizes[k])); });
    s.setProperty("--lh-body", v.leading); s.setProperty("--lh-heading", 1.25); s.setProperty("--lh-display", 1.1);
    v.space.forEach(function (n, i) { s.setProperty("--s" + (i + 1), px(n)); });
    ["sm", "md", "lg", "button"].forEach(function (k) { s.setProperty("--r-" + k, px(v.radius[k])); });
    s.setProperty("--sh-card", v.elevation.card); s.setProperty("--sh-overlay", v.elevation.overlay);
    s.setProperty("--m-dist", px(v.motion.distance)); s.setProperty("--m-ease", v.motion.easing); s.setProperty("--m-loop", Math.max(v.motion.duration * 4, 800) + "ms");
    s.setProperty("--focus-w", px(v.focus.width)); s.setProperty("--focus-o", px(v.focus.offset));
    s.setProperty("--focus-c", v.focus.role === "text" ? "var(--p-text)" : "var(--p-" + v.focus.role + ")");
    s.setProperty("--target", px(v.target));
    document.getElementById("motion-words").textContent = "An entrance moves " + v.motion.distance + " px over " + v.motion.duration + " ms, easing " + v.motion.easing + ". Where the device asks for reduced motion, nothing moves.";
    document.getElementById("curve-path").setAttribute("d", curve(v.motion.easing));
    var ruler = document.getElementById("ruler");
    ruler.innerHTML = "";
    var max = 1600;
    v.breakpoints.forEach(function (b) { var t = document.createElement("span"); t.className = "tick"; t.style.left = (b / max * 100) + "%"; t.textContent = b + " px"; ruler.appendChild(t); });
    d.devices.forEach(function (dv) { var t = document.createElement("span"); t.className = "dev"; t.style.left = (dv[0] / max * 100) + "%"; t.textContent = dv[1] + " " + dv[0]; ruler.appendChild(t); });
    var w = Number(document.getElementById("width-slider").value);
    var cols = v.cols[v.breakpoints.filter(function (b) { return w >= b; }).length];
    document.getElementById("width-words").textContent = "At " + w + " px the layout has " + cols + " column" + (cols === 1 ? "" : "s") + ".";
    var cells = document.getElementById("cells"); cells.style.setProperty("--cols", cols); cells.innerHTML = "";
    for (var i = 0; i < cols * 2; i += 1) { cells.appendChild(document.createElement("span")); }
    warnings(v);
  }
  function warnings(v) {
    var warn = document.getElementById("warnings"); warn.innerHTML = "";
    function add(id, value, text) {
      var li = document.createElement("li"); li.textContent = text + " ";
      var lab = document.createElement("label"), cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!kept[id];
      cb.addEventListener("change", function () { kept[id] = cb.checked; });
      lab.appendChild(cb); lab.appendChild(document.createTextNode(" keep it")); li.appendChild(lab); warn.appendChild(li);
    }
    if (v.sizes.body < d.min.body) { add("type:body:size", v.sizes.body, "The body text is " + v.sizes.body + " px, under the minimum " + d.min.body + " px, so it is harder to read."); }
    if (v.leading < d.min.leading) { add("type:body:leading", v.leading, "The body line height is " + v.leading + ", under the minimum " + d.min.leading + "."); }
    if (v.focus.width < d.min.focus) { add("focus:width", v.focus.width, "The focus indicator is " + v.focus.width + " px thick, under the minimum " + d.min.focus + " px."); }
    if (v.target < d.min.target) { add("target", v.target, "The touch target is " + v.target + " px, under the minimum " + d.min.target + " px."); }
    ["light", "dark"].forEach(function (mode) {
      var p = d.palette[mode], fg = v.focus.role === "text" ? p.text : p[v.focus.role];
      ["bg", "surface"].forEach(function (bg) {
        var r = ratio(fg, p[bg]);
        if (r < d.min.contrast) { add("focus:" + mode + ":" + bg, fg.toUpperCase() + "/" + p[bg].toUpperCase(), mode + ": the focus colour " + v.focus.role + " on " + bg + " is " + (Math.floor(r * 100) / 100).toFixed(2) + ":1, under the minimum " + d.min.contrast + ":1, so the focus ring is hard to see."); }
      });
    });
  }
  window.__choiceResult = function () {
    var v = values();
    return { type: { scale: { base: v.base, ratio: v.ratio, minimum: d.min.body, sizes: v.sizes, lineHeight: { body: v.leading, heading: 1.25, display: 1.1 } } },
             space: v.space, radius: v.radius, elevation: v.elevation, motion: v.motion,
             focus: v.focus, target: v.target, breakpoints: v.breakpoints, kept: Object.keys(kept).filter(function (k) { return kept[k]; }) };
  };
  document.querySelectorAll("input[name=look]").forEach(function (l) {
    l.addEventListener("change", function () {
      var look = d.looks.filter(function (x) { return x.id === l.value; })[0];
      Object.keys(look.pick).forEach(function (k) { var r = document.querySelector('input[name="f-' + k + '"][value="' + look.pick[k] + '"]'); if (r) { r.checked = true; } });
      render();
    });
  });
  document.querySelectorAll("input[name^=f-]").forEach(function (i) {
    i.addEventListener("change", function () {
      var v = values(), match = d.looks.filter(function (l) { return Object.keys(l.pick).every(function (k) { return checked("f-" + k) === l.pick[k]; }); })[0];
      document.querySelectorAll("input[name=look]").forEach(function (l) { l.checked = !!match && l.value === match.id; });
      render();
    });
  });
  document.getElementById("width-slider").addEventListener("input", render);
  showCard(); render();
})();
"""


class Refused(Exception):
    pass


def defaults():
    path = os.environ.get("ASGARD_FOUNDATIONS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "foundations.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build(company, candidates):
    import html as htmllib
    spec = defaults()
    if candidates:
        try:
            with open(candidates, encoding="utf-8") as fh:
                extra = json.load(fh)
        except (OSError, ValueError) as e:
            raise Refused(f"cannot read {candidates} as JSON ({e})")
        for key, cands in (extra.get("foundations") or {}).items():
            target = next((f for f in spec["foundations"] if f["id"] == key), None)
            if target is None or not isinstance(cands, list) or not cands:
                raise Refused(f"the foundation {key} is not one of the design's, or has no candidates")
            target["cands"] = cands
    checks = os.path.join(company, ".ouroboric", "checks")
    if not os.path.isfile(os.path.join(checks, "brand.py")):
        raise Refused(f"{company} is not a company folder: no .ouroboric/checks/brand.py")
    sys.path.insert(0, os.path.abspath(checks))
    import brand
    saved = choicepage.saved_choice(company, "foundations")
    choice = (saved or {}).get("choice") or {}
    palette = ((choicepage.saved_choice(company, "palette") or {}).get("result") or {})
    colours = {m: {**NEUTRAL[m], **{k: v for k, v in (palette.get(m) or {}).items() if k in NEUTRAL[m]}} for m in ("light", "dark")}
    e = htmllib.escape
    looks = [l for l in spec.get("looks", []) if all(any(str(c["id"]) == str(v) for c in next(f for f in spec["foundations"] if f["id"] == k)["cands"])
                                                     for k, v in l["pick"].items() if any(f["id"] == k for f in spec["foundations"]))]
    start = {}
    for f in spec["foundations"]:
        ids = [str(c["id"]) for c in f["cands"]]
        want = str(choice.get("f-" + f["id"], ""))
        start[f["id"]] = want if want in ids else ids[0]
    match = next((l["id"] for l in looks if all(start.get(k) == str(v) for k, v in l["pick"].items())), None)
    cards = []
    if looks:
        cur = match
        tabs = "".join(f'<label><input type="radio" name="look" value="{e(l["id"])}"{" checked" if cur == l["id"] else ""}> {e(l["name"])}</label>' for l in looks)
        notes = "".join(f'<p class="note"><strong>{e(l["name"])}:</strong> {e(l["note"])}</p>' for l in looks)
        cards.append(f'<section class="card q" data-card="look" hidden><h2>Start from a look</h2><p>A look sets every foundation at once, as a starting point. '
                     f'You can change any of them afterwards.</p><fieldset data-option-group="look"><div class="tabs">{tabs}</div></fieldset>{notes}</section>')
    for f in spec["foundations"]:
        opts = "".join(f'<label><input type="radio" name="f-{e(f["id"])}" value="{e(str(c["id"]))}"{" checked" if str(c["id"]) == start[f["id"]] else ""}> {e(c["name"])}</label>' for c in f["cands"])
        notes = "".join(f'<p class="note"><strong>{e(c["name"])}:</strong> {e(c.get("note", ""))}</p>' for c in f["cands"])
        cards.append(f'<section class="card q" data-card="f-{e(f["id"])}" hidden><h2>{e(f["name"])}</h2><p>{e(f["why"])}</p>'
                     f'<fieldset data-option-group="f-{e(f["id"])}"><div class="tabs">{opts}</div></fieldset>{notes}'
                     f'<p class="note">The sample above changes with each option.</p></section>')
    cards.append('<section class="card q" data-card="summary" hidden><h2>Your foundations</h2><p>These are the foundations as you have them now. '
                 'Anything that breaks a rule is listed; you may keep it, and it is written down with your reason.</p><ul id="warnings"></ul></section>')
    sample = ('<div class="sample" id="sample"><p class="display">A big line</p><p class="h1">A large heading</p><p class="h2">A section title</p>'
              '<p class="h3">A smaller title</p><p class="body" id="sample-body">Everything people read is set at the body size, with room between the lines, '
              'so a paragraph like this one stays easy to follow from the first word to the last.</p><p class="small">A caption, a little smaller.</p>'
              '<div class="grid"><div class="card" id="sample-card"><p class="h3">A card</p><p class="body">With a button and a field.</p>'
              '<button type="button" class="btn focused">Book a date</button><div class="field focused">Your name</div></div>'
              '<div class="motion"><p class="small">Motion, played on a loop</p><div class="track"><div id="motion-ball"></div></div>'
              '<p class="small" id="motion-words"></p><svg id="curve" viewBox="0 0 120 60" aria-label="The easing curve"><path id="curve-path" d="M0,60 L120,0" fill="none" stroke="currentColor" stroke-width="2"></path></svg></div></div>'
              '<div class="overlay">Something that floats above the page</div>'
              '<p class="small">Screen widths and where the layout changes:</p><div class="ruler" id="ruler"></div>'
              '<label class="small">Width <input type="range" id="width-slider" min="320" max="1600" value="820"></label><p class="small" id="width-words"></p>'
              '<div class="cells" id="cells"></div></div>')
    data = {"foundations": spec["foundations"], "looks": looks, "devices": DEVICES, "palette": colours,
            "min": {"body": brand.MIN_BODY, "leading": brand.MIN_LEADING, "focus": brand.MIN_FOCUS, "target": brand.MIN_TARGET,
                    "contrast": brand.MIN_FOCUS_CONTRAST}}
    body = (f'<div class="stage" id="stage" data-preview>{sample}<p class="progress" id="progress"></p>' + "".join(cards) +
            '<div class="nav"><button type="button" id="back">Back</button><button type="button" id="next">Next</button></div></div>')
    css = CSS
    for mode, prefix in (("light", "L"), ("dark", "D")):
        for key, token in (("BG", "bg"), ("SURFACE", "surface"), ("BORDER", "border"), ("TEXT", "text"), ("MUTED", "muted"), ("ACCENT", "accent"), ("ONACCENT", "on-accent")):
            css = css.replace(f"__{prefix}{key}__", colours[mode][token])
    page = choicepage.skeleton("foundations", "Your foundations",
                               "Choose how the company feels beyond colour and type: the sizes, the space, the corners, the depth, the motion. "
                               "One at a time; the sample changes with every option.", body, data, saved, css=css, js=JS)
    out = os.path.join(company, choicepage.CHOICES)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "foundations.html"), "w", encoding="utf-8") as fh:
        fh.write(page)


def main(argv):
    if len(argv) not in (1, 2):
        print("usage: brand.sh foundations-page DIR [CANDIDATES.json]", file=sys.stderr)
        return 2
    try:
        build(argv[0], argv[1] if len(argv) == 2 else None)
    except Refused as e:
        print(f"brand.sh foundations-page: {e}", file=sys.stderr)
        return 2
    print(f"The foundations page is written: {choicepage.CHOICES}/foundations.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
