"""Prove a choice page in a headless browser (brand tools spec §5.7), before it is shared:

- every face the page offers loads (`document.fonts`), and every image decodes (rule 3);
- every option visibly changes the page: for each group of options the preview's computed styles are fingerprinted per
  option, in light and dark mode at 390, 820 and 1280 pixels, and two options with the same fingerprint everywhere fail
  (rule 4);
- the page reopens on the founder's saved choice (rule 1);
- font names in inline style attributes are single-quoted.

    pagecheck.py DIR PAGE.html

The browser is Playwright's Chromium. A company may use its own browser: DIR/.ouroboric/browser.json,
{"executable": "/path/to/chrome"} or {"channel": "chrome"}. Exit 0 when the page passes, 1 when it does not, 2 when it
cannot be checked.
"""
import hashlib
import json
import os
import re
import sys

WIDTHS, MODES = (390, 820, 1280), ("light", "dark")

FONTS_JS = """async () => {
  const out = [];
  for (const f of Array.from(document.fonts)) {
    const family = f.family.replace(/^["']|["']$/g, "");
    try { await f.load(); out.push([family, f.status]); } catch (e) { out.push([family, "error"]); }
  }
  return out;
}"""
IMAGES_JS = """() => Array.from(document.images).filter(i => !(i.complete && i.naturalWidth > 0)).map(i => i.alt || i.src.slice(0, 40))"""
GROUPS_JS = """() => {
  const out = {};
  document.querySelectorAll("[data-option-group]").forEach(g => {
    out[g.getAttribute("data-option-group")] = Array.from(g.querySelectorAll("input[type=radio]")).map(r => r.value);
  });
  return out;
}"""
SELECT_JS = """([name, value]) => {
  const g = document.querySelector('[data-option-group="' + name + '"]');
  const r = Array.from(g.querySelectorAll("input[type=radio]")).find(x => x.value === value);
  r.checked = true;
  r.dispatchEvent(new Event("change", { bubbles: true }));
  return new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
}"""
FINGERPRINT_JS = """() => {
  const root = document.querySelector("[data-preview]") || document.querySelector("main") || document.body;
  const props = ["color", "background-color", "background-image", "font-family", "font-size", "font-weight", "font-style",
    "letter-spacing", "line-height", "border-top-width", "border-top-style", "border-top-color", "border-radius",
    "box-shadow", "opacity", "display", "margin-top", "padding-top", "gap", "transform", "text-decoration-line",
    "outline-style", "filter", "grid-template-columns"];
  const out = [];
  [root, ...root.querySelectorAll("*")].forEach(el => {
    const cs = getComputedStyle(el);
    if (cs.display === "none") { return; }
    const r = el.getBoundingClientRect();
    out.push(el.tagName + "|" + props.map(p => cs.getPropertyValue(p)).join(",") + "|" + Math.round(r.width) + "x" +
      Math.round(r.height) + "|" + (el.currentSrc || el.getAttribute("src") || "") + "|" +
      (el.children.length ? "" : el.textContent.trim()));
  });
  return out.join("\\n");
}"""
STATE_JS = """() => ({ saved: (window.__choiceState || {}).saved || null,
  current: window.__currentChoice ? window.__currentChoice() : {} })"""
CALM = "*, *::before, *::after { transition: none !important; animation: none !important; }"


class Cannot(Exception):
    pass


def launch_options(company):
    path = os.path.join(company, ".ouroboric", "browser.json")
    if not os.path.isfile(path):
        return {}
    try:
        with open(path, encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as e:
        raise Cannot(f"{path} is not valid JSON ({e})")
    options = {}
    if cfg.get("executable"):
        if not os.path.isfile(cfg["executable"]):
            raise Cannot(f"the browser {cfg['executable']} set in {path} is not there")
        options["executable_path"] = cfg["executable"]
    if cfg.get("channel"):
        options["channel"] = cfg["channel"]
    return options


def check(company, page_path):
    if not os.path.isfile(page_path):
        raise Cannot(f"{page_path} is not a file")
    with open(page_path, encoding="utf-8") as fh:
        html = fh.read()
    options = launch_options(company)
    problems, report = [], []
    if re.search(r'style="[^"]*font-family:\s*"', html):
        problems.append("a font name inside an inline style attribute is in double quotes, which breaks the attribute: "
                        "font names there are single-quoted")
    from playwright.sync_api import Error, sync_playwright
    prints = {}
    families = {}
    broken_images = set()
    reopen = None
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch(**options)
        except Error as e:
            raise Cannot(f"the headless browser could not start: {str(e).splitlines()[0]}")
        first = True
        for mode in MODES:
            ctx = browser.new_context(color_scheme=mode, viewport={"width": 1280, "height": 900})
            for width in WIDTHS:
                page = ctx.new_page()
                page.set_viewport_size({"width": width, "height": 900})
                page.goto("file://" + os.path.abspath(page_path))
                page.wait_for_load_state("load")
                page.add_style_tag(content=CALM)
                for family, status in page.evaluate(FONTS_JS):
                    families.setdefault(family, set()).add(status)
                broken_images.update(page.evaluate(IMAGES_JS))
                if first:
                    state = page.evaluate(STATE_JS)
                    saved = (state["saved"] or {}).get("choice")
                    if saved:
                        reopen = [f"{k}: saved {v}, the page shows {state['current'].get(k)}"
                                  for k, v in saved.items() if k in state["current"] and state["current"][k] != v]
                        reopen = reopen if reopen else True
                    first = False
                for name, values in page.evaluate(GROUPS_JS).items():
                    for value in values:
                        page.evaluate(SELECT_JS, [name, value])
                        fp = hashlib.sha256(page.evaluate(FINGERPRINT_JS).encode()).hexdigest()
                        prints.setdefault(name, {}).setdefault(value, []).append(fp)
                page.close()
            ctx.close()
        browser.close()
    for family, statuses in sorted(families.items()):
        if statuses == {"loaded"}:
            report.append(f"{family}: loaded")
        else:
            problems.append(f"{family}: did not load")
    for image in sorted(broken_images):
        problems.append(f"an image did not decode: {image}")
    for name, options_ in prints.items():
        values = list(options_)
        if len(values) < 2:
            continue
        same = [(a, b) for i, a in enumerate(values) for b in values[i + 1:] if options_[a] == options_[b]]
        for a, b in same:
            problems.append(f"{name}: the options {a} and {b} do not change what the page shows")
        if not same:
            report.append(f"{name}: {len(values)} options, each changes the page "
                          f"(light and dark, {', '.join(str(w) for w in WIDTHS[:-1])} and {WIDTHS[-1]} px)")
    if reopen is True:
        report.append("reopens on the saved choice")
    elif reopen:
        problems += reopen
    return problems, report


def main(argv):
    if len(argv) != 2:
        print("usage: brand.sh check-page DIR PAGE.html", file=sys.stderr)
        return 2
    try:
        problems, report = check(*argv)
    except Cannot as e:
        print(f"brand.sh check-page: {e}", file=sys.stderr)
        return 2
    for line in report:
        print(line)
    for line in problems:
        print(f"problem: {line}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
