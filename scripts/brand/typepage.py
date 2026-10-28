"""The typography pages of step 6c (brand tools spec §5.7): width first, then depth where she likes, then the roles.

    typepage.py DIR CANDIDATES.json [--stage taste|depth|roles]

A static page cannot fetch fonts, so the three guided pages are built one after the other, each from what the one before
saved in the company's docs/7-branding/identity/choices/:

- taste: one card for each style direction (geometric sans, old-style serif, a formal script, ...), with the two faces
  that start it, in her own words. She says which she likes. Width: every direction, two faces each.
- depth: only the directions she liked, with the faces held back there. She picks the ones that go further.
- roles: a card for each role (wordmark, display, heading, body, interface), offering her favourites that suit it.

The stage is the next one after the last saved, or --stage. CANDIDATES.json: {"languages": ["pt"], "sample": {"name", "tagline",
"about"}, "directions": [ids to offer; default all]}. The faces are Asgard's curated list (scripts/brand/faces.json, pinned by
SHA-256 at one commit of the library; ASGARD_FACES changes the list). Every fact the pages show is read from the font files, and
the faces are embedded, subset to the words shown, so no page needs a network.
"""
import base64
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choicepage  # noqa: E402
import fonts as library  # noqa: E402

ROLES = ("wordmark", "display", "heading", "body", "ui")
ROLE_INFO = {
    "wordmark": ("Wordmark", "The company's name in the logo.", "The logo, the favicon set, the signature.",
                 "Everywhere, but always the same few words.", [500], False),
    "display": ("Display", "The few big words: a hero line, a post's title.", "The website's top, social post images, covers.",
                "Rarely, and large.", [500], False),
    "heading": ("Heading", "Section titles and card titles.", "Website sections, price cards, documents.",
                "Often, at a medium size.", [600], False),
    "body": ("Body", "Everything people read: the about text, prices, terms.", "Website text, notes, contracts.",
             "All the time, and small.", [400, 700], True),
    "ui": ("Interface", "Buttons, labels, fields and menus.", "Navigation, forms, controls.",
           "All the time, and small.", [400, 600], False),
}
TITLES = {"wordmark": "Choose the wordmark", "display": "Choose the display face", "heading": "Choose the heading face",
          "body": "Choose the body face", "ui": "Choose the interface face"}
FALLBACK = {"sans": "Helvetica, Arial, sans-serif", "serif": "Georgia, 'Times New Roman', serif", "script": "cursive",
            "mono": "ui-monospace, monospace"}
NEUTRAL = {"light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "text": "#1A1A1A", "muted": "#555555", "accent": "#0B5FCC",
                     "on-accent": "#FFFFFF"},
           "dark": {"bg": "#121212", "surface": "#1E1E1E", "text": "#EDEDED", "muted": "#B0B0B0", "accent": "#6EA8FE",
                    "on-accent": "#121212"}}
UI_WORDS = "Book a date Work About Contact About us Bold for emphasis, italic for a title."
STEPS = {"taste": "type-taste", "depth": "type-depth", "roles": "type"}
CSS = """
.stage { display: grid; gap: 16px; }
.live { display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 16px; }
.panel { border: 1px solid var(--line); border-radius: 12px; padding: 20px; background: var(--p-bg); color: var(--p-text); display: grid; gap: 10px; align-content: start; }
.panel .wm { font-family: var(--f-wordmark); font-size: 2rem; margin: 0; line-height: 1.1; }
.panel .disp { font-family: var(--f-display); font-size: 1.9rem; margin: 0; line-height: 1.15; }
.panel .head { font-family: var(--f-heading); font-size: 1.25rem; font-weight: 600; margin: 0; }
.panel .body { font-family: var(--f-body); margin: 0; }
.panel .ui { font-family: var(--f-ui); display: flex; gap: 12px; align-items: center; flex-wrap: wrap; }
.panel .btn { background: var(--p-accent); color: var(--p-on-accent); border-radius: 6px; padding: 6px 14px; font-weight: 600; }
.panel .small { color: var(--p-muted); font-size: .8rem; margin: 0; }
.favs { border: 1px dashed var(--line); border-radius: 12px; padding: 10px 14px; display: flex; gap: 12px; flex-wrap: wrap; align-items: baseline; min-height: 2.4rem; }
.favs .none { color: var(--muted); font-size: .9rem; }
.favs span.chip { font-size: 1.3rem; }
.specimens { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 12px; }
.spec { border: 2px solid var(--line); border-radius: 12px; padding: 14px; background: var(--bg); display: grid; gap: 4px; }
.spec.liked { border-color: var(--accent); outline: 3px solid var(--accent); }
.spec .nm { font-size: 1.8rem; margin: 0; line-height: 1.1; }
.spec .tg { font-size: 1.25rem; margin: 0; }
.spec .ab { margin: 0; }
.spec .tag, .tag { color: var(--muted); font-size: .8rem; margin: 0; }
[data-card][hidden], [data-view][hidden] { display: none; }
.card { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; display: grid; gap: 8px; }
.progress { color: var(--muted); font-size: .85rem; }
.tabs { display: flex; flex-wrap: wrap; gap: 8px; }
.tabs label { display: flex; gap: 6px; align-items: center; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: var(--bg); cursor: pointer; }
.facts { margin: 0; padding-left: 1.2rem; font-size: .9rem; }
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
  function face(id) { return d.faces.filter(function (f) { return f.id === id; })[0]; }
  function stack(f) { return "'" + f.family + "', " + d.fallback[f.kind]; }
  function chips(ids) {
    var el = document.getElementById("favs");
    el.innerHTML = "";
    if (!ids.length) { var n = document.createElement("span"); n.className = "none"; n.textContent = "Nothing yet."; el.appendChild(n); return; }
    ids.forEach(function (id) { var f = face(id), s = document.createElement("span"); s.className = "chip"; s.style.fontFamily = stack(f); s.textContent = f.family; el.appendChild(s); });
  }
  var kept = {};
  function taste() {
    var likes = [], dirs = [];
    d.directions.forEach(function (x) {
      var v = checked("like-" + x.id), ids = v === "both" ? x.start : (v && v !== "neither" ? [v] : []);
      if (ids.length) { dirs.push(x.id); }
      ids.forEach(function (i) { likes.push(i); });
    });
    document.querySelectorAll(".spec").forEach(function (s) { s.classList.toggle("liked", likes.indexOf(s.getAttribute("data-face")) >= 0); });
    return { likes: likes, directions: dirs };
  }
  function depth() {
    var fav = d.likes.slice();
    d.directions.forEach(function (x) { var v = checked("more-" + x.id); if (v && v !== "none") { fav.push(v); } });
    document.querySelectorAll(".spec").forEach(function (s) { s.classList.toggle("liked", fav.indexOf(s.getAttribute("data-face")) >= 0); });
    return { favourites: fav };
  }
  function picks() { var o = {}; d.roles.forEach(function (r) { o[r] = checked("type-" + r); }); return o; }
  function roles() {
    var p = picks(), stage = document.getElementById("stage");
    d.roles.forEach(function (r) {
      var f = face(p[r]); if (f) { stage.style.setProperty("--f-" + r, stack(f)); }
      document.querySelectorAll('[data-view="face-' + r + '"]').forEach(function (v) { v.hidden = v.getAttribute("data-face") !== p[r]; });
    });
    var warn = document.getElementById("warnings");
    warn.innerHTML = "";
    function add(id, value, text) {
      var li = document.createElement("li"); li.textContent = text + " ";
      var lab = document.createElement("label"), cb = document.createElement("input"); cb.type = "checkbox"; cb.checked = !!kept[id + "=" + value];
      cb.addEventListener("change", function () { kept[id + "=" + value] = cb.checked; });
      lab.appendChild(cb); lab.appendChild(document.createTextNode(" keep it")); li.appendChild(lab); warn.appendChild(li);
    }
    d.roles.forEach(function (r) {
      var f = face(p[r]); if (!f) { return; }
      var need = d.needs[r];
      need.weights.forEach(function (w) {
        if (!f.weights.some(function (x) { return x.min <= w && w <= x.max; })) { add("type:" + r + ":weights", w, f.family + " has no weight " + w + ", which the " + d.names[r].toLowerCase() + " needs."); }
      });
      if (need.italic && !f.italic) { add("type:" + r + ":italic", f.family, f.family + " has no italic, which the " + d.names[r].toLowerCase() + " uses for emphasis. Emphasis would be in bold. Keep it only if you accept that."); }
      Object.keys(f.glyphs).forEach(function (lang) { if (f.glyphs[lang].covers === false) { add("type:" + r + ":glyphs", f.family, f.family + " lacks " + f.glyphs[lang].missing + " characters of " + lang + "."); } });
    });
  }
  function update() {
    if (d.mode === "taste") { chips(taste().likes); }
    else if (d.mode === "depth") { chips(depth().favourites); }
    else { roles(); }
  }
  window.__choiceResult = function () {
    if (d.mode === "taste") { return taste(); }
    if (d.mode === "depth") { return depth(); }
    var p = picks(), out = { fonts: {}, kept: Object.keys(kept).filter(function (k) { return kept[k]; }) };
    d.roles.forEach(function (r) { var f = face(p[r]); if (f) { out.fonts[r] = { id: f.id, family: f.family, licence: f.licence, source: f.source, files: f.files, weights: f.weights }; } });
    return out;
  };
  document.querySelectorAll("input[type=radio]").forEach(function (i) { i.addEventListener("change", update); });
  showCard(); update();
})();
"""


class Refused(Exception):
    pass


def curated():
    path = os.environ.get("ASGARD_FACES") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "faces.json")
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def pick_stage(company, wanted):
    if wanted:
        if wanted not in STEPS:
            raise Refused(f"the stage is taste, depth or roles, not {wanted}")
        return wanted
    saved = lambda step: choicepage.saved_choice(company, step)  # noqa: E731
    if saved("type") or saved("type-depth"):
        return "roles"
    return "depth" if saved("type-taste") else "taste"


def gather(brand, ids, by_id, ref, base, root, languages, keep, work):
    """Facts read from the files of the faces, and the @font-face rules that embed them."""
    rows, embeds = [], []
    for i in ids:
        c = by_id[i]
        cand = {"id": i, "family": c["family"], "dir": c["dir"], "files": [f["name"] for f in c["files"]],
                "sha256": {f["name"]: f["sha256"] for f in c["files"]}}
        try:
            facts = library.facts_for(brand, cand, base, root, languages)
        except library.Refused as e:
            raise Refused(str(e))
        rows.append({"id": i, "family": facts["family_in_file"], "kind": c.get("kind", "sans") if c.get("kind") in FALLBACK else "sans",
                     "direction": c.get("direction"), "tier": c.get("tier", "start"), "voices": c.get("voices", []),
                     "suits": c.get("suits", list(ROLES)), "note": c.get("note", ""), "weights": facts["weights"],
                     "italic": facts["italic"], "licence": facts["licence"].get("spdx") or "unknown",
                     "source": f"{curated().get('library', 'https://github.com/google/fonts')}/tree/{ref}/ofl/{c['dir']}",
                     "files": [f["name"] for f in facts["files"]], "glyphs": facts["glyphs"], "notes": facts["notes"]})
        for n, f in enumerate(facts["files"]):
            dst = os.path.join(work, f"{i}-{n}.woff2")
            brand.make_web_font(os.path.join(root, facts["dir"], f["name"]), dst, keep)
            with open(dst, "rb") as fh:
                uri = "data:font/woff2;base64," + base64.b64encode(fh.read()).decode()
            lo, hi = f["weights"]["min"], f["weights"]["max"]
            embeds.append(f"@font-face {{ font-family: {choicepage.quote_family(rows[-1]['family'])}; src: url({uri}) format('woff2'); "
                          f"font-weight: {lo:g}{'' if lo == hi else f' {hi:g}'}; font-style: {'italic' if f['italic'] else 'normal'}; "
                          "font-display: block; }")
    return rows, embeds


def build(company, candidates, wanted):
    import html as htmllib
    try:
        with open(candidates, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as e:
        raise Refused(f"cannot read {candidates} as JSON ({e})")
    checks = os.path.join(company, ".ouroboric", "checks")
    if not os.path.isfile(os.path.join(checks, "brand.py")):
        raise Refused(f"{company} is not a company folder: no .ouroboric/checks/brand.py")
    sys.path.insert(0, os.path.abspath(checks))
    import brand
    stage = pick_stage(company, wanted)
    e = htmllib.escape
    pool = curated()
    ref = pool.get("ref", "")
    directions = [d for d in pool["directions"] if not spec.get("directions") or d["id"] in spec["directions"]]
    by_id = {f["id"]: f for f in pool["faces"]}
    languages = [str(x) for x in spec.get("languages") or []] or ["en"]
    sample = {"name": "Your company name", "tagline": "What you do, in a line",
              "about": "A short paragraph about the company, in the words its clients read.", **(spec.get("sample") or {})}
    keep = set(sample["name"] + sample["tagline"] + sample["about"] + UI_WORDS)
    base = library.library() if os.environ.get("ASGARD_FONTS_BASE") else f"https://github.com/google/fonts/raw/{ref}/ofl"
    root = library.downloads()
    taste = choicepage.saved_choice(company, "type-taste") or {}
    depth = choicepage.saved_choice(company, "type-depth") or {}
    likes = (taste.get("result") or {}).get("likes") or []
    liked_dirs = (taste.get("result") or {}).get("directions") or []
    start = {d["id"]: [f["id"] for f in pool["faces"] if f.get("direction") == d["id"] and f.get("tier") == "start"] for d in directions}
    deeper = {d["id"]: [f["id"] for f in pool["faces"] if f.get("direction") == d["id"] and f.get("tier") == "deeper"] for d in directions}
    saved = choicepage.saved_choice(company, STEPS[stage])
    choice = (saved or {}).get("choice") or {}

    def specimen(row, mark=""):
        fam = f"font-family: {choicepage.quote_family(row['family'])}, {FALLBACK[row['kind']]}"
        return (f'<div class="spec" data-face="{e(row["id"])}"><p class="tag">{e(row["family"])}{mark}</p>'
                f'<p class="nm" style="{fam}">{e(sample["name"])}</p><p class="tg" style="{fam}">{e(sample["tagline"])}</p>'
                f'<p class="ab" style="{fam}">{e(sample["about"])}</p></div>')

    cards, data, ids = [], {"mode": stage, "fallback": FALLBACK}, []
    extra_body = ""
    if stage == "taste":
        shown = [d for d in directions if start[d["id"]]]
        ids = [i for d in shown for i in start[d["id"]]]
    elif stage == "depth":
        if not taste:
            raise Refused("the depth page needs the taste saved first: build and save the taste page (brand.sh type-page DIR CANDIDATES), "
                          "then run this again")
        shown = [d for d in directions if d["id"] in liked_dirs]
        ids = list(dict.fromkeys([i for i in likes if i in by_id] + [i for d in shown for i in deeper[d["id"]]]))
    else:
        favourites = (depth.get("result") or {}).get("favourites") or likes
        favourites = [i for i in dict.fromkeys(favourites) if i in by_id]
        allstart = [f["id"] for f in pool["faces"] if f.get("tier") == "start"]
        offered, fallback = {}, {}
        for r in ROLES:
            mine = [i for i in favourites if r in by_id[i].get("suits", [])]
            if not mine:
                fallback[r] = True
                mine = [i for i in allstart if r in by_id[i].get("suits", [])]
            offered[r] = mine
        ids = list(dict.fromkeys(i for r in ROLES for i in offered[r]))
        shown = []
    if not ids:
        raise Refused("there are no faces to show: check the candidates file's directions")
    with tempfile.TemporaryDirectory() as work:
        rows, embeds = gather(brand, ids, by_id, ref, base, root, languages, keep, work)
    row = {r["id"]: r for r in rows}
    if stage == "taste":
        data["directions"] = [{"id": d["id"], "start": start[d["id"]]} for d in shown]
        for d in shown:
            faces = [row[i] for i in start[d["id"]]]
            cur = choice.get("like-" + d["id"], "neither")
            if cur not in [f["id"] for f in faces] + ["both", "neither"]:
                cur = "neither"
            option = lambda value, text: (f'<label><input type="radio" name="like-{e(d["id"])}" value="{e(value)}"'
                                          f'{" checked" if cur == value else ""}> {e(text)}</label>')
            opts = "".join(option(f["id"], f["family"]) for f in faces)
            both = option("both", "Both") if len(faces) > 1 else ""
            neither = option("neither", "Neither")
            cards.append(f'<section class="card" data-card="like-{e(d["id"])}" hidden><h2>{e(d["name"])}</h2><p>{e(d["text"])}</p>'
                         f'<div class="specimens">{"".join(specimen(f) for f in faces)}</div><p><strong>Which do you like?</strong></p>'
                         f'<fieldset data-option-group="like-{e(d["id"])}"><div class="tabs">{opts}{both}{neither}</div></fieldset></section>')
        intro = ("Look at one style at a time, in your own words. Say which you like; you do not have to like any. "
                 "Later you can go deeper in the styles you liked.")
        title = "What do you like?"
        step = "type-taste"
    elif stage == "depth":
        data["directions"] = [{"id": d["id"], "deeper": deeper[d["id"]]} for d in shown]
        data["likes"] = [i for i in likes if i in by_id]
        for d in shown:
            if not deeper[d["id"]]:
                continue
            mine = [row[i] for i in likes if i in row and row[i]["direction"] == d["id"]]
            more = [row[i] for i in deeper[d["id"]]]
            chosen = choice.get("more-" + d["id"], "none")
            opts = ('<label><input type="radio" name="more-%s" value="none"%s> None of these</label>' % (e(d["id"]), "" if chosen != "none" else " checked")) + "".join(
                f'<label><input type="radio" name="more-{e(d["id"])}" value="{e(f["id"])}"{" checked" if chosen == f["id"] else ""}> {e(f["family"])}</label>' for f in more)
            cards.append(f'<section class="card" data-card="more-{e(d["id"])}" hidden><h2>More {e(d["name"].lower())}</h2>'
                         f'<p>You liked this direction. Here are the faces that go further in it, next to the ones you liked.</p>'
                         f'<div class="specimens">{"".join(specimen(f, " (you liked it)") for f in mine)}{"".join(specimen(f) for f in more)}</div>'
                         f'<p><strong>Do any of these go further?</strong></p><fieldset data-option-group="more-{e(d["id"])}"><div class="tabs">{opts}</div></fieldset></section>')
        intro = "These are the styles you liked, with the faces that were held back. Pick one that goes further, if any does."
        title = "Go deeper"
        step = "type-depth"
        if not likes:
            intro = "You did not pick a face on the taste page. Go back to it, or go on to the roles with the faces to start with."
    else:
        data.update({"roles": list(ROLES), "names": {r: ROLE_INFO[r][0] for r in ROLES},
                     "needs": {r: {"weights": ROLE_INFO[r][4], "italic": ROLE_INFO[r][5]} for r in ROLES},
                     "roleFaces": {r: [{"id": i} for i in offered[r]] for r in ROLES}})
        picks = {}
        for r in ROLES:
            want = choice.get(f"type-{r}")
            picks[r] = want if want in offered[r] else offered[r][0]
            name, job, where, seen, _, _ = ROLE_INFO[r]
            radios = "".join(f'<label><input type="radio" name="type-{r}" value="{e(i)}"{" checked" if i == picks[r] else ""}> {e(row[i]["family"])}</label>' for i in offered[r])
            views = "".join(
                f'<div data-view="face-{r}" data-face="{e(i)}"{"" if i == picks[r] else " hidden"}><h3>{e(row[i]["family"])}</h3><p>{e(row[i]["note"])}</p>'
                f'<ul class="facts"><li>Weights: {", ".join(("%g" % w["min"]) if w["min"] == w["max"] else ("%g to %g" % (w["min"], w["max"])) for w in row[i]["weights"])}</li>'
                f'<li>Italic: {"yes" if row[i]["italic"] else "no"}</li><li>Licence: {e(row[i]["licence"])}</li>'
                + "".join(f'<li>{e(l)}: {"covers every character" if g["covers"] else ("not checked" if g["covers"] is None else str(g["missing"]) + " characters missing")}</li>'
                          for l, g in row[i]["glyphs"].items()) + '</ul></div>' for i in offered[r])
            note = ('<p class="tag">None of your favourites suit this role, so these are faces that do.</p>' if fallback.get(r) else "")
            cards.append(f'<section class="card" data-card="role-{r}" hidden><h2>{e(TITLES[r])}</h2><p><strong>{e(job)}</strong></p>'
                         f'<p>Where it appears: {e(where)} How often she sees it: {e(seen)}</p>{note}'
                         f'<fieldset data-option-group="type-{r}"><div class="tabs">{radios}</div></fieldset>{views}</section>')
        cards.append('<section class="card" data-card="summary" hidden><h2>Your typefaces</h2><p>These are the faces as you have them now. '
                     'Anything a role needs and a face does not have is listed; you may keep it, and it is written down with your reason.</p>'
                     '<ul id="warnings"></ul></section>')
        intro = "Choose how the company sounds on the page, one role at a time, from the faces you liked."
        title = "Your typefaces"
        step = "type"
    data["faces"] = rows
    palette = ((choicepage.saved_choice(company, "palette") or {}).get("result") or {})
    colours = {m: {**NEUTRAL[m], **{k: v for k, v in (palette.get(m) or {}).items() if k in NEUTRAL[m]}} for m in ("light", "dark")}
    style = ""
    live = ""
    if stage == "roles":
        style = "; ".join(f"--f-{r}: {choicepage.quote_family(row[picks[r]]['family'])}, {FALLBACK[row[picks[r]]['kind']]}" for r in ROLES)
        panel = lambda mode: (f'<div class="panel" style="--p-bg: {colours[mode]["bg"]}; --p-text: {colours[mode]["text"]}; '
                              f'--p-muted: {colours[mode]["muted"]}; --p-accent: {colours[mode]["accent"]}; '
                              f'--p-on-accent: {colours[mode]["on-accent"]}"><p class="wm">{e(sample["name"])}</p>'
                              f'<p class="disp">{e(sample["tagline"])}</p><p class="head">About us</p>'
                              f'<p class="body">{e(sample["about"])} <strong>Bold for emphasis,</strong> <em>italic for a title.</em></p>'
                              f'<div class="ui"><span class="btn">Book a date</span><span>Work</span><span>About</span><span>Contact</span></div>'
                              f'<p class="small">{mode.capitalize()}</p></div>')
        live = f'<div class="live">{panel("light")}{panel("dark")}</div>'
    else:
        live = '<div class="favs" id="favs" aria-live="polite"></div>'
    body = (f'<div class="stage" id="stage" data-preview style="{style}">{live}<p class="progress" id="progress"></p>' + "".join(cards) +
            '<div class="nav"><button type="button" id="back">Back</button><button type="button" id="next">Next</button></div></div>')
    page = choicepage.skeleton(step, title, intro, body, data, saved, css=CSS + "".join(embeds), js=JS)
    out = os.path.join(company, choicepage.CHOICES)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, f"{step}.html"), "w", encoding="utf-8") as fh:
        fh.write(page)
    return stage, step


def main(argv):
    args, wanted = list(argv), None
    if "--stage" in args:
        i = args.index("--stage")
        try:
            wanted = args[i + 1]
            del args[i:i + 2]
        except IndexError:
            print("usage: brand.sh type-page DIR CANDIDATES.json [--stage taste|depth|roles]", file=sys.stderr)
            return 2
    if len(args) != 2:
        print("usage: brand.sh type-page DIR CANDIDATES.json [--stage taste|depth|roles]", file=sys.stderr)
        return 2
    try:
        stage, step = build(args[0], args[1], wanted)
    except Refused as e:
        print(f"brand.sh type-page: {e}", file=sys.stderr)
        return 2
    print(f"The {stage} page is written: {choicepage.CHOICES}/{step}.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
