"""The playground of step 6f (brand tools spec §5.6): the last look at everything together.

    playground.py DIR [CANDIDATES.json]            write DIR/docs/7-branding/identity/choices/playground.html
    playground.py --apply DIR --by NAME            validate the saved export with brand.py, then write it into tokens.json

The page opens on what the founder saved on the guided pages (palette, typefaces, foundations) and on the company's tokens.json,
and lets her change any of it once more: the palette (a preset, a colour at a time, or her own value), the typeface of each
role, the foundations, and a variant of each component. A sample site, painted only from tokens, shows light and dark, phone,
tablet and desktop. The company's rules are checked live: the same pairs and minimums as brand.py (a test proves it), and a
failure she keeps, with a reason, becomes an accepted exception. The export is a token file; `--apply` validates it with
brand.py in a copy before anything is written, copies the shipped fonts beside the identity and makes the CSS again.

CANDIDATES.json: {"languages": ["pt"], "sample": {"name", "tagline", "about"}} as for the typography pages.
"""
import base64
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import choicepage  # noqa: E402
import foundationspage  # noqa: E402
import palettepage  # noqa: E402
import typepage  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
IDENTITY = "docs/7-branding/identity"
ROLE_KEYS = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent")
MESSAGE_KEYS = ("ok", "warn", "crit")
NEEDS = {"wordmark": [500], "display": [500], "heading": [600], "body": [400, 700], "ui": [400, 600]}
CSS = r"""
.pg { display: grid; gap: 16px; grid-template-columns: minmax(280px, 380px) minmax(0, 1fr); align-items: start; }
@media (max-width: 900px) { .pg { grid-template-columns: 1fr; } }
.tabs-nav { display: flex; flex-wrap: wrap; gap: 4px; margin-bottom: 8px; }
.tabs-nav button { font: inherit; font-weight: 600; border-radius: 8px; padding: 6px 10px; cursor: pointer; border: 1px solid var(--line); background: var(--bg); color: var(--text); }
.tabs-nav button[aria-selected="true"] { background: var(--accent); color: var(--on-accent); border-color: var(--accent); }
.tabs-nav .n:empty { display: none; }
.tabs-nav .n { font-size: .7rem; margin-left: 4px; background: var(--warn-bg); color: var(--warn); border-radius: 8px; padding: 0 5px; }
.controls { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 12px; display: grid; gap: 10px; align-content: start; max-height: 80vh; overflow: auto; }
.grp { border: 1px solid var(--line); border-radius: 10px; padding: 8px 10px; background: var(--bg); display: grid; gap: 6px; }
.grp h3 { margin: 0; font-size: .9rem; }
.grp .opts { display: flex; flex-wrap: wrap; gap: 6px; }
.grp .opts label { display: flex; gap: 4px; align-items: center; border: 1px solid var(--line); border-radius: 7px; padding: 3px 8px; font-size: .85rem; cursor: pointer; }
.grp .why { color: var(--muted); font-size: .8rem; margin: 0; }
.grp input[type=text] { font: inherit; font-size: .8rem; padding: 3px 6px; border: 1px solid var(--line); border-radius: 6px; background: var(--bg); color: var(--text); width: 100%; box-sizing: border-box; }
.checklist { list-style: none; margin: 0; padding: 0; display: grid; gap: 6px; }
.checklist li { border: 1px solid var(--line); border-radius: 8px; padding: 6px 8px; font-size: .82rem; background: var(--bg); display: grid; gap: 4px; }
.checklist li.fail { background: var(--warn-bg); color: var(--warn); }
.checklist li.kept { opacity: .85; }
.checklist .id { font-family: ui-monospace, monospace; font-size: .72rem; opacity: .8; }
.checklist input[type=text] { font: inherit; font-size: .8rem; padding: 2px 6px; width: 100%; box-sizing: border-box; }
.sitebar { display: flex; gap: 8px; flex-wrap: wrap; align-items: center; margin-bottom: 8px; }
.sitebar button { font: inherit; font-size: .85rem; border-radius: 8px; padding: 4px 10px; cursor: pointer; border: 1px solid var(--line); background: var(--bg); color: var(--text); }
.sitebar button[aria-pressed="true"] { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent); }
.viewport { overflow: auto; border-radius: 12px; border: 1px solid var(--line); background: var(--surface); padding: 8px; }
#site { margin: 0 auto; width: 100%; background: var(--c-bg); color: var(--c-text); font: 400 var(--fs-body)/var(--lh-body) var(--f-body); border-radius: 10px; overflow: hidden; }
#site[data-width="phone"] { max-width: 390px; } #site[data-width="tablet"] { max-width: 820px; } #site[data-width="desktop"] { max-width: 1200px; }
#site section, #site nav, #site footer { padding: var(--s4) var(--s4); display: grid; gap: var(--s3); }
#site section + section { border-top: 1px solid var(--c-border); }
#site nav { display: flex; align-items: center; justify-content: space-between; gap: var(--s3); flex-wrap: wrap; border-bottom: 1px solid var(--c-border); font: 500 var(--fs-small) var(--f-ui); }
#site[data-nav="centre"] nav { flex-direction: column; }
#site .logo { display: flex; align-items: center; gap: var(--s2); }
#site .logo .mk { position: relative; width: 36px; aspect-ratio: var(--logo-aspect, 1); }
#site .logo .mk i { position: absolute; inset: 0; -webkit-mask-repeat: no-repeat; mask-repeat: no-repeat; -webkit-mask-size: contain; mask-size: contain; }
#site .logo .wm { font: 500 1.35rem var(--f-wordmark); }
#site .links { display: flex; gap: var(--s3); flex-wrap: wrap; }
#site a, #site .a { color: var(--c-accent-text); }
#site[data-link="underlined"] .a { text-decoration: underline; text-underline-offset: 3px; }
#site[data-link="colour"] .a { text-decoration: none; }
#site[data-link="colour"] .a:hover { text-decoration: underline; }
#site .display { font: 500 var(--fs-display)/var(--lh-display) var(--f-display); margin: 0; }
#site h2 { font: 600 var(--fs-h2)/var(--lh-heading) var(--f-heading); margin: 0; }
#site h3 { font: 600 var(--fs-h3)/var(--lh-heading) var(--f-heading); margin: 0; }
#site p { margin: 0; max-width: 62ch; }
#site .small { font-size: var(--fs-small); color: var(--c-muted); }
#site .btn { font: 600 var(--fs-small)/1 var(--f-ui); min-height: var(--target); padding: 0 var(--s4); border-radius: var(--r-button); border: 1.5px solid var(--c-accent); display: inline-flex; align-items: center; width: max-content; }
#site[data-button="filled"] .btn.p { background: var(--c-accent); color: var(--c-on-accent); }
#site[data-button="outlined"] .btn.p { background: transparent; color: var(--c-accent-text); }
#site[data-button="soft"] .btn.p { background: var(--c-tint); color: var(--c-accent-text); border-color: var(--c-tint); }
#site .btn.s { background: transparent; color: var(--c-accent-text); }
#site .btn.focused, #site .field.focused { outline: var(--focus-w) solid var(--focus-c); outline-offset: var(--focus-o); }
#site .grid { display: grid; grid-template-columns: repeat(var(--cols, 2), minmax(0, 1fr)); gap: var(--s2); }
#site .ph { aspect-ratio: 1 / 1; background: linear-gradient(160deg, color-mix(in srgb, var(--c-accent) 30%, var(--c-surface)), color-mix(in srgb, var(--c-accent) 70%, var(--c-bg))); }
#site[data-image="rounded"] .ph { border-radius: var(--r-md); }
#site[data-image="framed"] .ph { border: var(--s1) solid var(--c-bg); box-shadow: 0 1px 3px color-mix(in srgb, var(--c-text) 25%, transparent); }
#site .cards { display: grid; grid-template-columns: repeat(var(--ccols, 1), minmax(0, 1fr)); gap: var(--s3); }
#site .card { padding: var(--s3); border-radius: var(--r-lg); display: grid; gap: var(--s1); align-content: start; }
#site[data-card="bordered"] .card { border: 1px solid var(--c-border); background: var(--c-bg); }
#site[data-card="surface"] .card { background: var(--c-surface); }
#site[data-card="raised"] .card { background: var(--c-surface); border: 1px solid var(--c-border); box-shadow: var(--sh-card); }
#site .ic { width: 22px; height: 22px; color: var(--c-accent-text); }
#site[data-icons="filled"] .ic path { fill: currentColor; } #site[data-icons="outline"] .ic path { fill: none; stroke: currentColor; stroke-width: 1.6; }
#site .field { min-height: var(--target); border: 1px solid var(--c-border); background: var(--c-surface); border-radius: var(--r-md); color: var(--c-muted); display: flex; align-items: center; padding: 0 var(--s3); font: 400 var(--fs-small) var(--f-body); }
#site .msg { font-size: var(--fs-small); border-radius: var(--r-md); padding: var(--s2) var(--s3); display: flex; gap: 8px; align-items: center; }
#site[data-message="tint"] .msg { background: color-mix(in srgb, var(--c) 10%, var(--c-bg)); color: var(--c); }
#site[data-message="bar"] .msg { border-left: 3px solid var(--c); background: var(--c-surface); color: var(--c); border-radius: 0 var(--r-md) var(--r-md) 0; }
#site footer { background: var(--c-surface); font-size: var(--fs-small); color: var(--c-muted); }
#site .overlay { background: var(--c-surface); border-radius: var(--r-lg); padding: var(--s2) var(--s3); box-shadow: var(--sh-overlay); width: max-content; font-size: var(--fs-small); }
#motion-ball { width: 14px; height: 14px; border-radius: 50%; background: var(--c-accent); animation: glide var(--m-loop) var(--m-ease) infinite alternate; }
@keyframes glide { from { transform: translateX(0); } to { transform: translateX(calc(var(--m-dist) * 3)); } }
@media (prefers-reduced-motion: reduce) { #motion-ball { animation: none; } }
[data-tab][hidden] { display: none; }
"""
JS = r"""
(function () {
  var d = JSON.parse(document.getElementById("data").textContent);
  var stage = document.getElementById("stage"), site = document.getElementById("site");
  function lum(h) { var c = [1, 3, 5].map(function (i) { var v = parseInt(h.substr(i, 2), 16) / 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }); return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]; }
  function ratio(a, b) { var x = lum(a), y = lum(b); return (Math.max(x, y) + 0.05) / (Math.min(x, y) + 0.05); }
  function shown(r) { return (Math.floor(r * 100) / 100).toFixed(2); }
  function mix(a, b, pct) { var p = function (h) { return [1, 3, 5].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }, x = p(a), y = p(b);
    return "#" + x.map(function (v, i) { return ("0" + Math.round(v * pct / 100 + y[i] * (100 - pct) / 100).toString(16)).slice(-2); }).join("").toUpperCase(); }
  function valid(h) { return /^#[0-9A-Fa-f]{6}$/.test(h || ""); }
  function checked(name) { var r = document.querySelector('input[name="' + name + '"]:checked'); return r ? r.value : null; }
  window.__data = function () { return d; };
  window.__rules = { rows: function (light, dark) {
    var out = [];
    [["light", light], ["dark", dark]].forEach(function (m) {
      d.pairs.forEach(function (p) { p.fgs.forEach(function (fg) { p.bgs.forEach(function (bg) {
        if (!m[1][fg] || !m[1][bg]) { return; }
        var r = ratio(m[1][fg], m[1][bg]);
        out.push({ mode: m[0], fg: fg, bg: bg, kind: p.kind, ratio: r, minimum: p.minimum, result: p.minimum === null ? "reported" : (r >= p.minimum ? "passes" : "fails") });
      }); }); });
    });
    return out; } };
  var kept = {};
  (d.accepted || []).forEach(function (a) { kept[a.check + "=" + a.value] = { id: a.check, value: String(a.value), reason: a.reason, by: a.by, date: a.date }; });
  function pick(group, list, id) { return list.filter(function (c) { return String(c.id) === String(id); })[0]; }
  function settings() {
    var preset = pick("preset", d.presets, checked("preset")) || d.presets[0];
    var pal = { light: Object.assign({}, preset.light), dark: Object.assign({}, preset.dark) };
    Object.keys(d.roles).forEach(function (role) { var c = pick("p-" + role, d.roles[role], checked("p-" + role)); if (c) { pal.light[role] = c.light; pal.dark[role] = c.dark; } });
    d.roleKeys.forEach(function (role) {
      var f = document.querySelector('input[data-choice-field="custom-' + role + '"]'), parts = f && f.value ? f.value.split("|").map(function (s) { return s.trim(); }) : [];
      if (parts.length === 2 && valid(parts[0]) && valid(parts[1])) { pal.light[role] = parts[0].toUpperCase(); pal.dark[role] = parts[1].toUpperCase(); }
    });
    var found = {};
    d.foundations.forEach(function (f) { found[f.id] = pick("f-" + f.id, f.cands, checked("f-" + f.id)) || f.cands[0]; });
    var comps = {};
    d.components.forEach(function (c) { comps[c.id] = checked("c-" + c.id) || c.cands[0].id; });
    var faces = {};
    d.roleNames.forEach(function (r) { var id = checked("t-" + r); faces[r] = d.faces.filter(function (f) { return f.id === id; })[0] || null; });
    var base = found.base.v, rt = found.ratio.v;
    function step(n) { return Math.round(base * Math.pow(rt, n) * 10) / 10; }
    var sizes = { small: Math.max(14, step(-1)), body: base, h3: step(1), h2: step(2), h1: step(3), display: step(4) };
    return { pal: pal, preset: preset, found: found, comps: comps, faces: faces, sizes: sizes, base: base, ratio: rt, leading: found.leading.v };
  }
  function checks(s) {
    var out = [];
    function add(id, value, pass, text) { out.push({ id: id, value: String(value), pass: pass, text: text }); }
    window.__rules.rows(s.pal.light, s.pal.dark).forEach(function (r) {
      if (r.kind === "decorative") { return; }
      add("contrast:" + r.mode + ":" + r.fg + "/" + r.bg, (s.pal[r.mode][r.fg] + "/" + s.pal[r.mode][r.bg]).toUpperCase(), r.result !== "fails",
          r.mode + ": " + r.fg + " on " + r.bg + " is " + shown(r.ratio) + ":1, needs at least " + r.minimum + ":1");
    });
    d.roleNames.forEach(function (r) {
      var f = s.faces[r]; if (!f) { return; }
      NEEDS[r].forEach(function (w) {
        var has = f.weights.some(function (x) { return x.min <= w && w <= x.max; });
        add("type:" + r + ":weights", w, has, f.family + (has ? " has" : " has no") + " weight " + w + ", which the " + r + " needs.");
      });
      if (r === "body") { add("type:body:italic", f.family, f.italic, f.family + (f.italic ? " has" : " has no") + " italic, which the body uses for emphasis."); }
      Object.keys(f.glyphs).forEach(function (lang) {
        var ok = f.glyphs[lang].covers !== false;
        add("type:" + r + ":glyphs", f.family, ok, f.family + (ok ? " covers" : " lacks " + f.glyphs[lang].missing + " characters of") + " " + (ok ? "every character of " : "") + lang + ".");
      });
    });
    add("type:body:size", s.base, s.base >= d.min.body, "The body text is " + s.base + " px, the minimum is " + d.min.body + " px.");
    add("type:body:leading", s.leading, s.leading >= d.min.leading, "The body line height is " + s.leading + ", the minimum is " + d.min.leading + ".");
    var fo = s.found.focus.v, target = s.found.target.v;
    add("focus:width", fo.width, fo.width >= d.min.focus, "The focus indicator is " + fo.width + " px thick, the minimum is " + d.min.focus + " px.");
    add("target", target, target >= d.min.target, "The touch target is " + target + " px, the minimum is " + d.min.target + " px.");
    ["light", "dark"].forEach(function (mode) {
      var p = s.pal[mode], fg = fo.role === "text" ? p.text : p[fo.role];
      ["bg", "surface"].forEach(function (bg) { var r = ratio(fg, p[bg]); add("focus:" + mode + ":" + bg, (fg + "/" + p[bg]).toUpperCase(), r >= d.min.contrast, mode + ": the focus colour " + fo.role + " on " + bg + " is " + shown(r) + ":1, the minimum is " + d.min.contrast + ":1."); });
      function low(id, fg2, bg2, min, text) { var r = ratio(fg2, bg2); add(id + ":" + mode, (fg2 + "/" + bg2).toUpperCase(), r >= min, mode + ": " + text + " " + shown(r) + ":1, the minimum is " + min + ":1."); }
      if (s.comps.button === "soft") { low("components:button:soft", p["accent-text"], mix(p.accent, p.bg, 16), 4.5, "the soft button's accent text on its tint is"); }
      if (s.comps.button === "outlined") { low("components:button:outlined", p["accent-text"], p.bg, 4.5, "the outlined button's accent text on the background is"); }
      if (s.comps.link === "colour") { low("components:link", p["accent-text"], p.text, 3, "a link without an underline differs from the text by"); }
      if (s.comps.message === "tint") { ["ok", "warn", "crit"].forEach(function (k) { if (p[k]) { low("components:message:" + k, p[k], mix(p[k], p.bg, 10), 4.5, "the " + k + " message on its tint is"); } }); }
    });
    out.forEach(function (c) {
      var k = kept[c.id + "=" + c.value];
      var other = Object.keys(kept).some(function (key) { return kept[key].id === c.id && kept[key].value !== c.value; });
      c.kept = !c.pass && !!k;
      c.stale = !c.pass && !k && other;
      c.reason = k ? k.reason : "";
    });
    return out;
  }
  function stack(f) { return "'" + f.family + "', " + d.fallback[f.kind]; }
  function apply(s) {
    var v = stage.style;
    ["bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent"].forEach(function (k) { v.setProperty("--c-" + k, "var(--m-" + k + ")"); });
    var mode = document.documentElement.getAttribute("data-theme") === "dark" || (document.documentElement.getAttribute("data-theme") !== "light" && window.matchMedia("(prefers-color-scheme: dark)").matches) ? "dark" : "light";
    var p = s.pal[mode];
    Object.keys(p).forEach(function (k) { v.setProperty("--m-" + k, p[k]); });
    v.setProperty("--c-tint", mix(p.accent, p.bg, 16));
    v.setProperty("--logo-0", p.text); v.setProperty("--logo-1", p.accent); v.setProperty("--logo-2", p.muted);
    ["small", "body", "h3", "h2", "h1", "display"].forEach(function (k) { v.setProperty("--fs-" + k, s.sizes[k] + "px"); });
    v.setProperty("--lh-body", s.leading); v.setProperty("--lh-heading", 1.25); v.setProperty("--lh-display", 1.1);
    s.found.space.v.forEach(function (n, i) { v.setProperty("--s" + (i + 1), n + "px"); });
    ["sm", "md", "lg", "button"].forEach(function (k) { v.setProperty("--r-" + k, s.found.radius.v[k] + "px"); });
    v.setProperty("--sh-card", s.found.elevation.v.card); v.setProperty("--sh-overlay", s.found.elevation.v.overlay);
    var mo = s.found.motion.v; v.setProperty("--m-dist", mo.distance + "px"); v.setProperty("--m-ease", mo.easing); v.setProperty("--m-loop", Math.max(mo.duration * 4, 800) + "ms");
    var fo = s.found.focus.v; v.setProperty("--focus-w", fo.width + "px"); v.setProperty("--focus-o", fo.offset + "px"); v.setProperty("--focus-c", fo.role === "text" ? "var(--m-text)" : "var(--m-" + fo.role + ")");
    v.setProperty("--target", s.found.target.v + "px");
    d.roleNames.forEach(function (r) { if (s.faces[r]) { v.setProperty("--f-" + r, stack(s.faces[r])); } });
    Object.keys(s.comps).forEach(function (k) { site.setAttribute("data-" + (k === "nav" ? "nav" : k), s.comps[k]); });
    var bps = s.found.breakpoints.v, w = { phone: 390, tablet: 820, desktop: 1200 }[site.getAttribute("data-width")];
    var cols = s.found.breakpoints.cols[bps.filter(function (b) { return w >= b; }).length];
    v.setProperty("--cols", Math.min(cols, 4)); v.setProperty("--ccols", w >= bps[0] ? 3 : 1);
    document.getElementById("motion-words").textContent = "An entrance moves " + mo.distance + " px over " + mo.duration + " ms, easing " + mo.easing + ".";
  }
  function exportTokens(s) {
    var t = JSON.parse(JSON.stringify(d.tokens));
    ["light", "dark"].forEach(function (m) { Object.keys(s.pal[m]).forEach(function (k) { t[m][k] = s.pal[m][k]; }); });
    t.type = { fonts: {}, scale: { base: s.base, ratio: s.ratio, minimum: d.min.body, sizes: s.sizes, lineHeight: { body: s.leading, heading: 1.25, display: 1.1 } } };
    d.roleNames.forEach(function (r) { var f = s.faces[r]; if (f) { t.type.fonts[r] = { family: f.family, fallback: d.fallback[f.kind], weights: NEEDS[r], files: "fonts/" + f.dir, licence: f.licence, source: f.source }; } });
    t.space = s.found.space.v; t.radius = s.found.radius.v; t.elevation = s.found.elevation.v;
    t.motion = { distance: s.found.motion.v.distance, duration: s.found.motion.v.duration, easing: s.found.motion.v.easing, reduced: "none" };
    t.focus = s.found.focus.v; t.target = s.found.target.v; t.breakpoints = s.found.breakpoints.v; t.components = s.comps; t.accepted = [];
    return t;
  }
  var NEEDS = d.needs;
  function current() { return checks(settings()); }
  window.__checks = current;
  window.__keep = function (id, reason) {
    var c = current().filter(function (x) { return x.id === id; })[0];
    if (c) { kept[id + "=" + c.value] = { id: id, value: c.value, reason: reason }; render(); }
  };
  window.__choiceResult = function () {
    var s = settings(), faces = [];
    d.roleNames.forEach(function (r) { var f = s.faces[r]; if (f && !faces.some(function (x) { return x.dir === f.dir; })) { faces.push({ dir: f.dir, files: f.files }); } });
    return { tokens: exportTokens(s), kept: current().filter(function (c) { return c.kept; }).map(function (c) { return { check: c.id, value: c.value, reason: c.reason }; }), copy: faces };
  };
  function renderChecks(list) {
    var ul = document.getElementById("checklist"); ul.innerHTML = "";
    var open = list.filter(function (c) { return !c.pass && !c.kept; });
    document.getElementById("open-count").textContent = open.length ? String(open.length) : "";
    list.slice().sort(function (a, b) { return (a.pass ? 1 : 0) - (b.pass ? 1 : 0); }).forEach(function (c) {
      var li = document.createElement("li");
      li.className = c.pass ? "pass" : (c.kept ? "kept" : "fail");
      var head = document.createElement("span"); head.textContent = (c.pass ? "passes: " : (c.kept ? "kept: " : "open: ")) + c.text; li.appendChild(head);
      var id = document.createElement("span"); id.className = "id"; id.textContent = c.id + (c.stale ? " (an exception for another value is out of date)" : ""); li.appendChild(id);
      if (!c.pass) {
        var box = document.createElement("input"); box.type = "text"; box.placeholder = "Keep it anyway: why?"; box.value = c.reason || "";
        box.addEventListener("change", function () { if (box.value.trim()) { kept[c.id + "=" + c.value] = { id: c.id, value: c.value, reason: box.value.trim() }; } else { delete kept[c.id + "=" + c.value]; } render(); });
        li.appendChild(box);
      }
      ul.appendChild(li);
    });
  }
  function render() { var s = settings(); apply(s); renderChecks(checks(s)); }
  document.querySelectorAll("[data-tab-button]").forEach(function (b) {
    b.addEventListener("click", function () {
      document.querySelectorAll("[data-tab-button]").forEach(function (x) { x.setAttribute("aria-selected", x === b ? "true" : "false"); });
      document.querySelectorAll("[data-tab]").forEach(function (t) { t.hidden = t.getAttribute("data-tab") !== b.getAttribute("data-tab-button"); });
    });
  });
  document.querySelectorAll("[data-width-button]").forEach(function (b) {
    b.addEventListener("click", function () { site.setAttribute("data-width", b.getAttribute("data-width-button")); document.querySelectorAll("[data-width-button]").forEach(function (x) { x.setAttribute("aria-pressed", x === b ? "true" : "false"); }); render(); });
  });
  document.getElementById("mode-button").addEventListener("click", function () {
    var now = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    document.documentElement.setAttribute("data-theme", now); render();
  });
  document.querySelectorAll("input").forEach(function (i) { i.addEventListener("change", render); i.addEventListener("input", render); });
  render();
})();
"""


class Refused(Exception):
    pass


def components_defaults():
    with open(os.path.join(HERE, "components.json"), encoding="utf-8") as fh:
        return json.load(fh)["components"]


def same(a, b):
    return json.dumps(a, sort_keys=True) == json.dumps(b, sort_keys=True)


def current_value(tokens, fid):
    scale = (tokens.get("type") or {}).get("scale") or {}
    motion = tokens.get("motion") or {}
    return {"base": scale.get("base"), "ratio": scale.get("ratio"), "leading": (scale.get("lineHeight") or {}).get("body"),
            "space": tokens.get("space"), "radius": tokens.get("radius"), "elevation": tokens.get("elevation"),
            "motion": {k: motion.get(k) for k in ("duration", "easing", "distance")} if motion else None,
            "focus": tokens.get("focus"), "target": tokens.get("target"), "breakpoints": tokens.get("breakpoints")}.get(fid)


def build(company, candidates):
    import html as htmllib
    checks = os.path.join(company, ".ouroboric", "checks")
    if not os.path.isfile(os.path.join(checks, "brand.py")):
        raise Refused(f"{company} is not a company folder: no .ouroboric/checks/brand.py")
    sys.path.insert(0, os.path.abspath(checks))
    import brand
    with open(os.path.join(company, IDENTITY, "tokens.json"), encoding="utf-8") as fh:
        tokens = json.load(fh)
    spec = {}
    if candidates:
        try:
            with open(candidates, encoding="utf-8") as fh:
                spec = json.load(fh)
        except (OSError, ValueError) as e:
            raise Refused(f"cannot read {candidates} as JSON ({e})")
    saved_pal = (choicepage.saved_choice(company, "palette") or {}).get("result") or {}
    yours = {}
    for mode in ("light", "dark"):
        have = saved_pal.get(mode) if isinstance(saved_pal.get(mode), dict) else tokens.get(mode) or {}
        yours[mode] = {k: v.upper() for k, v in have.items() if isinstance(v, str) and brand.HEX.match(v)}
        if not all(k in yours[mode] for k in ROLE_KEYS):
            raise Refused("there is no palette to look at yet: choose one first (brand.sh palette-page), or set it in tokens.json")
    try:
        rnd, _ = palettepage.latest_round(company)
    except palettepage.Refused:
        rnd = {"presets": [], "roles": {}}
    presets = [{"id": "yours", "name": "As you have it", "light": yours["light"], "dark": yours["dark"]}]
    presets += [{"id": p["id"], "name": p["name"], "light": {k: v.upper() for k, v in p["light"].items()},
                 "dark": {k: v.upper() for k, v in p["dark"].items()}} for p in rnd["presets"]]
    for p in presets:   # the message colours and brand colours stay as the company has them when a preset leaves them out
        for mode in ("light", "dark"):
            for k in MESSAGE_KEYS:
                p[mode].setdefault(k, yours[mode].get(k, "#000000"))
    roles = {}
    for role, cands in (rnd.get("roles") or {}).items():
        mine = [{k: (v.upper() if k in ("light", "dark") else v) for k, v in c.items()} for c in cands
                if not (c["light"].upper() == yours["light"][role] and c["dark"].upper() == yours["dark"][role])]
        if mine:
            roles[role] = mine
    # the foundations: the company's own values, then the default candidates
    foundations = foundationspage.defaults()["foundations"]
    for f in foundations:
        cur = current_value(tokens, f["id"])
        if cur is not None and not any(same(c["v"], cur) for c in f["cands"]):
            f["cands"] = [{"id": "yours", "name": "As you have it", "note": "The company's own value.", "v": cur,
                           **({"cols": [1, 2, 3, 4, 5, 6][:len(cur) + 1]} if f["id"] == "breakpoints" else {})}] + f["cands"]
    start_found = {}
    for f in foundations:
        cur = current_value(tokens, f["id"])
        start_found[f["id"]] = next((str(c["id"]) for c in f["cands"] if cur is not None and same(c["v"], cur)), str(f["cands"][0]["id"]))
    components = components_defaults()
    chosen = tokens.get("components") if isinstance(tokens.get("components"), dict) else {}
    start_comp = {c["id"]: chosen.get(c["id"]) if chosen.get(c["id"]) in [x["id"] for x in c["cands"]] else c["cands"][0]["id"] for c in components}
    # the faces: her favourites and the ones she chose, embedded subset to the words shown
    pool_spec = typepage.curated()
    by_id = {f["id"]: f for f in pool_spec["faces"]}
    saved_type = (choicepage.saved_choice(company, "type") or {}).get("result") or {}
    chosen_faces = {r: v.get("id") for r, v in (saved_type.get("fonts") or {}).items() if isinstance(v, dict) and v.get("id") in by_id}
    fav = ((choicepage.saved_choice(company, "type-depth") or {}).get("result") or {}).get("favourites") or \
        ((choicepage.saved_choice(company, "type-taste") or {}).get("result") or {}).get("likes") or []
    ids = [i for i in dict.fromkeys(list(chosen_faces.values()) + list(fav)) if i in by_id]
    languages = [str(x) for x in spec.get("languages") or tokens.get("languages") or []] or ["en"]
    sample = {"name": "Your company name", "tagline": "What you do, in a line",
              "about": "A short paragraph about the company, in the words its clients read.", **(spec.get("sample") or {})}
    keep = set(sample["name"] + sample["tagline"] + sample["about"] + typepage.UI_WORDS + "Home Work About Contact Send Message Your name Hello 0123456789")
    rows, embeds = [], []
    if ids:
        ref = pool_spec.get("ref", "")
        base = typepage.library.library() if os.environ.get("ASGARD_FONTS_BASE") else f"https://github.com/google/fonts/raw/{ref}/ofl"
        with tempfile.TemporaryDirectory() as work:
            try:
                rows, embeds = typepage.gather(brand, ids, by_id, ref, base, typepage.library.downloads(), languages, keep, work)
            except typepage.Refused as e:
                raise Refused(str(e))
        for r in rows:
            r["dir"] = by_id[r["id"]]["dir"]
    role_names = ["wordmark", "display", "heading", "body", "ui"]
    start_face = {r: chosen_faces.get(r) or next((x["id"] for x in rows if r in x["suits"]), rows[0]["id"] if rows else None) for r in role_names}
    layers = palettepage.logo_layers(company)
    expected = brand.palette_rows(yours)
    saved = choicepage.saved_choice(company, "playground")
    choice = (saved or {}).get("choice") or {}
    e = htmllib.escape

    def group(name, title, why, cands, current, label=lambda c: c["name"]):
        cur = str(choice.get(name, current))
        if cur not in [str(c["id"]) for c in cands]:
            cur = str(current)
        opts = "".join(f'<label><input type="radio" name="{e(name)}" value="{e(str(c["id"]))}"{" checked" if str(c["id"]) == cur else ""}> {e(label(c))}</label>' for c in cands)
        return f'<div class="grp" data-option-group="{e(name)}"><h3>{e(title)}</h3><p class="why">{e(why)}</p><div class="opts">{opts}</div></div>'

    pal_html = group("preset", "Palette", "Start from one of the palettes, then change a colour at a time.", presets, "yours")
    labels = {"bg": "Background", "surface": "Surface", "border": "Border", "text": "Text", "muted": "Muted text", "accent": "Accent",
              "accent-text": "Accent text", "on-accent": "Text on accent"}
    for role in ROLE_KEYS:
        if role in roles:
            pal_html += group("p-" + role, labels[role], palettepage.ROLE_TEXT[role][2],
                              [{"id": "keep", "name": "As the palette has it"}] + roles[role], "keep",
                              lambda c: c["name"] + (f" {c['light']} / {c['dark']}" if "light" in c else ""))
        pal_html += (f'<div class="grp"><h3>{e(labels[role])}: your own value</h3><input type="text" data-choice-field="custom-{e(role)}" '
                     f'placeholder="#0B5FCC | #6EA8FE" aria-label="Your own value for {e(labels[role])}, light and dark"></div>')
    type_html = ""
    if rows:
        for r in role_names:
            mine = [x for x in rows if r in x["suits"]] or rows
            type_html += group("t-" + r, typepage.ROLE_INFO[r][0], typepage.ROLE_INFO[r][1], mine, start_face[r], lambda c: c["family"])
    else:
        type_html = '<p class="why">No typefaces are chosen yet: choose them first (brand.sh type-page).</p>'
    found_html = "".join(group("f-" + f["id"], f["name"], f["why"], f["cands"], start_found[f["id"]]) for f in foundations)
    comp_html = "".join(group("c-" + c["id"], c["name"], c["why"], c["cands"], start_comp[c["id"]]) for c in components)
    star = "M11 1 L14 8 L21 8.5 L15.5 13 L17.5 20.5 L11 16.5 L4.5 20.5 L6.5 13 L1 8.5 L8 8 Z"
    logo = ""
    if layers:
        logo = f'<span class="mk" style="--logo-aspect: {layers["aspect"]}">' + "".join(
            f'<i style="background: var(--logo-{i}); -webkit-mask-image: url({l}); mask-image: url({l})"></i>' for i, l in enumerate(layers["layers"])) + "</span>"
    links = '<span class="links"><span class="a">Work</span><span class="a">About</span><span class="a">Contact</span></span>'
    site = (f'<div id="site" data-width="desktop"><nav id="site-nav"><span class="logo">{logo}<span class="wm">{e(sample["name"])}</span></span>{links}</nav>'
            f'<section id="site-hero"><p class="display">{e(sample["tagline"])}</p><p>{e(sample["about"])}</p>'
            '<span class="btn p">Book a date</span></section>'
            '<section id="site-grid"><div class="grid"><div class="ph"></div><div class="ph"></div><div class="ph"></div><div class="ph"></div><div class="ph"></div><div class="ph"></div></div></section>'
            f'<section id="site-about"><h2>About us</h2><p>{e(sample["about"])} <strong>Bold for emphasis,</strong> <em>italic for a title.</em></p>'
            '<p class="small">A caption, a little quieter.</p></section>'
            f'<section id="site-cards"><h2>What we offer</h2><div class="cards">'
            + "".join(f'<div class="card"><svg class="ic" viewBox="0 0 22 22"><path d="{star}"/></svg><h3>Service {i}</h3><p class="small">A few words about it.</p></div>' for i in (1, 2, 3)) +
            '</div></section>'
            '<section id="site-contact"><h2>Say hello</h2><div class="field focused">Your name</div><span class="btn p focused">Send</span>'
            '<p class="msg" style="--c: var(--m-ok)">Your message has been sent.</p><p class="msg" style="--c: var(--m-crit)">Something went wrong. Try again.</p>'
            '<div class="overlay">Something that floats above the page</div>'
            '<div class="small">Motion: <span id="motion-ball"></span> <span id="motion-words"></span></div></section>'
            f'<footer id="site-footer"><span>{e(sample["name"])}</span><span class="a">Privacy</span></footer></div>')
    tabs = (("palette", "Palette", pal_html), ("type", "Type", type_html), ("foundations", "Foundations", found_html), ("components", "Components", comp_html),
            ("checks", "Checks", '<ul class="checklist" id="checklist"></ul>'))
    nav = "".join(f'<button type="button" data-tab-button="{k}" aria-selected="{"true" if k == "palette" else "false"}">{n}'
                  f'{"<span class=n id=open-count></span>" if k == "checks" else ""}</button>' for k, n, _ in tabs)
    panels = "".join(f'<div class="tabbody" data-tab="{k}"{"" if k == "palette" else " hidden"}>{h}</div>' for k, _, h in tabs)
    data = {"presets": presets, "roles": roles, "roleKeys": list(ROLE_KEYS), "foundations": foundations, "components": components, "faces": rows,
            "roleNames": role_names, "fallback": typepage.FALLBACK, "needs": NEEDS, "palette": yours, "tokens": tokens,
            "accepted": [a for a in tokens.get("accepted") or [] if isinstance(a, dict)],
            "pairs": [{"fgs": list(f), "bgs": list(b), "kind": k, "minimum": m} for f, b, k, m in brand.PAIRS],
            "expected": [r for r in expected], "min": {"body": brand.MIN_BODY, "leading": brand.MIN_LEADING, "focus": brand.MIN_FOCUS,
                                                         "target": brand.MIN_TARGET, "contrast": brand.MIN_FOCUS_CONTRAST}}
    body = (f'<div class="pg" id="stage" data-preview><div><div class="tabs-nav">{nav}</div><div class="controls">{panels}</div></div>'
            '<div><div class="sitebar"><button type="button" data-width-button="phone" aria-pressed="false">Phone</button>'
            '<button type="button" data-width-button="tablet" aria-pressed="false">Tablet</button>'
            '<button type="button" data-width-button="desktop" aria-pressed="true">Desktop</button>'
            f'<button type="button" id="mode-button">Light / dark</button></div><div class="viewport">{site}</div></div></div>')
    page = choicepage.skeleton("playground", "Your design system, together",
                               "This is everything you chose, on a sample site. Change anything once more; the checks on the Checks tab say "
                               "what each change costs, and you may keep a failure with your reason.", body, data, saved,
                               css=CSS + "".join(embeds), js=JS)
    out = os.path.join(company, choicepage.CHOICES)
    os.makedirs(out, exist_ok=True)
    with open(os.path.join(out, "playground.html"), "w", encoding="utf-8") as fh:
        fh.write(page)


def run_check(root, command):
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(root, ".ouroboric/checks/brand.py"), command], cwd=root,
                       capture_output=True, text=True)
    return r.returncode, [l for l in (r.stdout + r.stderr).splitlines() if l.startswith("docs/7-branding/identity/tokens.json:")]


def apply(company, by):
    import datetime
    saved = choicepage.saved_choice(company, "playground")
    result = (saved or {}).get("result") or {}
    tokens = result.get("tokens")
    if not isinstance(tokens, dict):
        raise Refused("there is nothing to apply: the founder has not saved the playground (brand.sh serve, then Save my choice)")
    path = os.path.join(company, IDENTITY, "tokens.json")
    with open(path, encoding="utf-8") as fh:
        current = json.load(fh)
    old = {(a.get("check"), str(a.get("value"))): a for a in current.get("accepted") or [] if isinstance(a, dict)}
    today = datetime.date.today().isoformat()
    accepted = []
    for k in result.get("kept") or []:
        before = old.get((k.get("check"), str(k.get("value"))))
        accepted.append({"check": k["check"], "value": str(k["value"]), "reason": k.get("reason", ""),
                         "by": before["by"] if before else by, "date": before["date"] if before else today})
    new = {**current, **tokens, "accepted": accepted}
    root = os.path.join(company, IDENTITY)
    from_downloads = typepage.library.downloads()
    with tempfile.TemporaryDirectory() as tmp:
        shutil.copytree(os.path.join(company, ".ouroboric", "checks"), os.path.join(tmp, ".ouroboric", "checks"))
        os.makedirs(os.path.join(tmp, IDENTITY))
        if os.path.isdir(os.path.join(root, "fonts")):
            shutil.copytree(os.path.join(root, "fonts"), os.path.join(tmp, IDENTITY, "fonts"))
        for c in result.get("copy") or []:
            folder = os.path.join(from_downloads, c["dir"])
            target = os.path.join(tmp, IDENTITY, "fonts", c["dir"])
            os.makedirs(target, exist_ok=True)
            for n in list(c.get("files") or []) + ["OFL.txt"]:
                if os.path.isfile(os.path.join(folder, n)):
                    shutil.copy2(os.path.join(folder, n), os.path.join(target, n))
        with open(os.path.join(tmp, IDENTITY, "tokens.json"), "w", encoding="utf-8") as fh:
            json.dump(new, fh, indent=2, ensure_ascii=False)
        subprocess.run(["git", "init", "-q"], cwd=tmp, check=True)
        problems = []
        for command in ("contrast", "fonts", "foundations", "type", "components", "accepted"):
            code, lines = run_check(tmp, command)
            if code:
                problems += lines or [f"{command}: the check could not run (exit {code})"]
        if problems:
            print("brand.sh playground-apply: the export fails the company's checks, and nothing was written:", file=sys.stderr)
            for line in problems:
                print(f"  {line.replace('docs/7-branding/identity/tokens.json: ', '')}", file=sys.stderr)
            return 1
    for c in result.get("copy") or []:
        folder = os.path.join(from_downloads, c["dir"])
        target = os.path.join(root, "fonts", c["dir"])
        os.makedirs(target, exist_ok=True)
        for n in list(c.get("files") or []) + ["OFL.txt"]:
            if os.path.isfile(os.path.join(folder, n)):
                shutil.copy2(os.path.join(folder, n), os.path.join(target, n))
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(new, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    r = subprocess.run([sys.executable, "-I", "-B", os.path.join(company, ".ouroboric/checks/brand.py"), "tokens", "--write"], cwd=company,
                       capture_output=True, text=True)
    print(f"tokens.json is written; the generated files are made again: {', '.join(l.split(': ')[0].split('/')[-1] for l in r.stdout.splitlines() if 'written' in l) or 'tokens.css'}"
          f"{' and the web fonts' if 'woff2' in r.stdout else ''}")
    print(f"{len(accepted)} accepted exception(s) recorded, by {by}")
    return 0


def main(argv):
    args = list(argv)
    try:
        if args and args[0] == "--apply":
            args = args[1:]
            by = None
            if "--by" in args:
                i = args.index("--by")
                try:
                    by = args[i + 1]
                    del args[i:i + 2]
                except IndexError:
                    pass
            if len(args) != 1 or not by:
                print("usage: brand.sh playground-apply DIR --by NAME: NAME is who accepts the exceptions", file=sys.stderr)
                return 2
            return apply(args[0], by)
        if len(args) not in (1, 2):
            print("usage: brand.sh playground DIR [CANDIDATES.json]", file=sys.stderr)
            return 2
        build(args[0], args[1] if len(args) == 2 else None)
    except (Refused, typepage.Refused) as e:
        print(f"brand.sh playground: {e}", file=sys.stderr)
        return 2
    print(f"The playground is written: {choicepage.CHOICES}/playground.html")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
