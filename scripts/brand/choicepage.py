"""The shared module of the choice pages (brand tools spec §5.7). Every page that offers the founder a choice is built
from `skeleton`, so the four rules hold in one place:

1. The page saves her confirmed choice and her reason where the agent reads them (docs/7-branding/identity/choices/
   <step>.json, through `brand.sh serve`, or as a download she hands over), and reopens on it.
2. The facts shown about a candidate are read from its files when the page is built (`facts_of`), never typed.
3. Every face the page offers loads: `brand.sh check-page` lists `document.fonts` in a headless browser.
4. Every option visibly changes the page: `brand.sh check-page` fingerprints the preview in both modes at three widths.

A page marks its options as groups of radio buttons inside `[data-option-group="name"]`, and what the options change
inside `[data-preview]`. Font names inside inline `style` attributes are single-quoted (`quote_family`).
"""
import hashlib
import json
import os

CHOICES = "docs/7-branding/identity/choices"
STEPS = ("logo", "palette", "fonts", "type", "foundations", "components", "playground")
TOKEN_PLACEHOLDER = "__CHOICE_TOKEN__"

CSS = """
:root { --bg: #fff; --surface: #f4f4f4; --text: #1a1a1a; --muted: #555; --line: #d8d8d8; --accent: #0b5fcc; --on-accent: #fff; --warn-bg: #fdf0d8; --warn: #6b3d08; }
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { --bg: #121212; --surface: #1e1e1e; --text: #ededed; --muted: #b0b0b0; --line: #333; --accent: #6ea8fe; --on-accent: #121212; --warn-bg: #3a2a16; --warn: #f3d3a8; } }
body { margin: 0; background: var(--bg); color: var(--text); font: 16px/1.5 system-ui, sans-serif; }
main { max-width: 1200px; margin: 0 auto; padding: 24px 16px 64px; }
h1 { font-size: 1.5rem; margin: 0 0 4px; } h2 { font-size: 1.1rem; margin: 0 0 4px; } h3 { font-size: .95rem; margin: 16px 0 4px; }
p.lead { color: var(--muted); margin: 0 0 24px; max-width: 70ch; }
fieldset { border: 0; padding: 0; margin: 0; }
.save { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-top: 32px; display: grid; gap: 8px; max-width: 70ch; }
.save textarea { width: 100%; box-sizing: border-box; font: inherit; background: var(--bg); color: var(--text); border: 1px solid var(--line); border-radius: 8px; padding: 8px; }
.save button { font: inherit; font-weight: 600; border-radius: 8px; padding: 8px 14px; cursor: pointer; border: 1px solid var(--accent); background: var(--accent); color: var(--on-accent); }
.save button.plain { background: transparent; color: var(--accent); }
.save button:focus-visible, input:focus-visible, textarea:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
#status { color: var(--muted); }
"""

SAVE_UI = """<section class="save" aria-label="Save your choice">
<label for="reason">Why this choice? (optional)</label>
<textarea id="reason" rows="2" maxlength="2000"></textarea>
<div><button type="button" id="save">Save my choice</button> <button type="button" id="download" class="plain">Download my choice</button> <span id="status" role="status"></span></div>
</section>"""

JS = """
(function () {
  var state = { step: STEP_JSON, token: window.__choiceToken || "", saved: JSON.parse(document.getElementById("saved").textContent) };
  if (state.token.indexOf("__") === 0) { state.token = ""; }
  window.__choiceState = state;
  function groups() { return Array.prototype.slice.call(document.querySelectorAll("[data-option-group]")); }
  function current() {
    var c = {};
    groups().forEach(function (g) { var r = g.querySelector("input[type=radio]:checked"); if (r) { c[g.getAttribute("data-option-group")] = r.value; } });
    document.querySelectorAll("input[data-choice-field]").forEach(function (i) { if (i.value) { c[i.getAttribute("data-choice-field")] = i.value; } });
    return c;
  }
  window.__currentChoice = current;
  function result() { return window.__choiceResult ? window.__choiceResult() : undefined; }
  RESTORE
  var status = document.getElementById("status");
  document.getElementById("save").addEventListener("click", function () {
    if (!state.token) { status.textContent = "Saving needs the page your helper opened for you. Use Download instead and give the file to your helper."; return; }
    fetch("/save/" + state.step, { method: "POST", headers: { "Content-Type": "application/json", "X-Choice-Token": state.token },
      body: JSON.stringify({ choice: current(), reason: document.getElementById("reason").value, result: result() }) })
      .then(function (r) { if (!r.ok) { throw new Error(r.status); } status.textContent = "Saved. Your helper can see it."; })
      .catch(function () { status.textContent = "It could not be saved. Use Download instead."; });
  });
  document.getElementById("download").addEventListener("click", function () {
    var blob = new Blob([JSON.stringify({ step: state.step, choice: current(), reason: document.getElementById("reason").value, result: result() }, null, 2)], { type: "application/json" });
    var a = document.createElement("a");
    a.href = URL.createObjectURL(blob); a.download = state.step + ".json";
    document.body.appendChild(a); a.click(); a.remove();
  });
})();
"""

RESTORE = """
  if (state.saved && state.saved.choice) {
    groups().forEach(function (g) {
      var name = g.getAttribute("data-option-group"), value = state.saved.choice[name];
      if (value === undefined) { return; }
      var radios = g.querySelectorAll("input[type=radio]");
      for (var i = 0; i < radios.length; i++) {
        if (radios[i].value === value) { radios[i].checked = true; radios[i].dispatchEvent(new Event("change", { bubbles: true })); }
      }
    });
    document.querySelectorAll("input[data-choice-field]").forEach(function (i) {
      var v = state.saved.choice[i.getAttribute("data-choice-field")];
      if (v !== undefined) { i.value = v; i.dispatchEvent(new Event("input", { bubbles: true })); }
    });
    document.getElementById("reason").value = state.saved.reason || "";
  }
"""


def esc(text):
    return str(text).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def quote_family(name):
    """A font family for an inline style attribute: single-quoted, so the attribute's own double quotes stay whole."""
    return "'" + esc(str(name).replace("\\", "\\\\").replace("'", "\\'")) + "'"


def saved_choice(company, step):
    """The founder's saved choice for a step, or None."""
    try:
        with open(os.path.join(company, CHOICES, f"{step}.json"), encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def facts_of(path):
    """A font file's facts, read from the file now: its weights, whether it has an italic, its family and its hash."""
    from fontTools.ttLib import TTFont
    font = TTFont(path, lazy=True)
    lo = hi = font["OS/2"].usWeightClass
    italic = bool(font["OS/2"].fsSelection & 1) or bool(font["head"].macStyle & 2)
    if "fvar" in font:
        for axis in font["fvar"].axes:
            if axis.axisTag == "wght":
                lo, hi = axis.minValue, axis.maxValue
            if axis.axisTag == "ital":
                italic = True
    name = font["name"]
    with open(path, "rb") as fh:
        digest = hashlib.sha256(fh.read()).hexdigest()
    return {"family": name.getDebugName(16) or name.getDebugName(1), "weights": [{"min": lo, "max": hi}],
            "italic": italic, "sha256": digest}


def script_json(value):
    return json.dumps(value, ensure_ascii=False).replace("</", "<\\/")


def skeleton(step, title, lead, body, data, saved, css="", js="", restore=True):
    """One choice page. `body` holds the options (radio groups in `[data-option-group]`) and the preview
    (`[data-preview]`); `data` is the page's own data, `saved` the founder's saved choice or None."""
    if step not in STEPS:
        raise ValueError(f"{step} is not one of the design's steps")
    code = JS.replace("STEP_JSON", json.dumps(step)).replace("RESTORE", RESTORE if restore else "")
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title>
<style>{CSS}{css}</style>
</head>
<body>
<main>
<h1>{esc(title)}</h1>
<p class="lead">{esc(lead)}</p>
{body}
{SAVE_UI}
</main>
<script type="application/json" id="data">{script_json(data)}</script>
<script type="application/json" id="saved">{script_json(saved)}</script>
<script>window.__choiceToken = "{TOKEN_PLACEHOLDER}"; window.__choiceStep = {json.dumps(step)};</script>
<script>{code}{js}</script>
</body>
</html>
"""
