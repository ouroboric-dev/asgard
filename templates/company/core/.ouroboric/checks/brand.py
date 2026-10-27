#!/usr/bin/env python3
"""The brand checks: the palettes and fonts in docs/7-branding/identity/tokens.json.

    python3 .ouroboric/checks/brand.py contrast [--json]   every text and shape pair, in light and dark mode
    python3 .ouroboric/checks/brand.py fonts [--json]      the licence evidence of each font the company ships
    python3 .ouroboric/checks/brand.py tokens [--write]    tokens.css and fonts.css from tokens.json; fail when stale
    python3 .ouroboric/checks/brand.py board-fresh         the brand board matches its inputs
    python3 .ouroboric/checks/brand.py check               every brand check; run.sh runs this

The contrast check needs only the standard library; the font check reads font files with fontTools.

Each finding prints as `path: what is wrong`. Exit codes: 0 when every check passes, 1 when a check has a finding,
2 when a check cannot run (tokens.json is not valid JSON).
"""
import hashlib
import json
import math
import os
import re
import subprocess
import sys

TOKENS = "docs/7-branding/identity/tokens.json"
COLOURS = ("bg", "surface", "border", "text", "muted", "accent", "accent-text", "on-accent", "ok", "warn", "crit")
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
BRAND = re.compile(r"^brand-[1-9][0-9]*$")
# (foregrounds, backgrounds, kind, minimum): WCAG 2.2 SC 1.4.3 for text, SC 1.4.11 for shapes.
PAIRS = (
    (("text", "muted", "accent-text"), ("bg", "surface"), "text", 4.5),
    (("on-accent",), ("accent",), "text", 4.5),
    (("ok", "warn", "crit"), ("bg", "surface"), "text", 4.5),
    (("accent",), ("bg", "surface"), "shape", 3.0),
    (("border",), ("bg", "surface"), "decorative", None),
)
ENHANCED = 7.0

IDENTITY = "docs/7-branding/identity"
ROLES = ("heading", "body", "ui")
FONT_FILES = (".ttf", ".otf", ".woff", ".woff2")
CLOSING = "This check compares licence files and font data. It is not legal advice."
# The licences the font check knows by their text: the licences of the Google Fonts library's ofl/, apache/ and ufl/.
KNOWN = {
    "OFL-1.1": (("sil open font license version 1.1",), ("open font license",), ("openfontlicense.org", "scripts.sil.org/ofl")),
    "Apache-2.0": (("apache license", "version 2.0, january 2004"), ("apache license",), ("apache.org/licenses/license-2.0",)),
    "UFL-1.0": (("ubuntu font licence version 1.0",), ("ubuntu font licence",), ("ubuntu.com/legal/terms-and-policies/font-licence",)),
}
LIMITS = ("personal use", "non-commercial", "noncommercial", "demo", "trial", "evaluation")


class CannotRun(Exception):
    pass


def luminance(value):
    """WCAG 2.2 relative luminance of #RRGGBB."""
    channels = []
    for i in (1, 3, 5):
        c = int(value[i:i + 2], 16) / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    r, g, b = channels
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(a, b):
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def shown(r):
    """The ratio rounded down to two decimals, so a ratio never looks higher than it is."""
    return f"{math.floor(r * 100) / 100:.2f}:1"


def load_tokens():
    try:
        with open(TOKENS, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as e:
        raise CannotRun(f"{TOKENS}: cannot read it as JSON ({e})")


def contrast(as_json=False):
    tokens = load_tokens()
    findings, report, rows = [], [], []
    palettes = {mode: tokens.get(mode) or {} for mode in ("light", "dark")}
    values = [palettes[m].get(k) for m in palettes for k in COLOURS]
    if all(v is None for v in values) and not any(BRAND.match(k) for p in palettes.values() for k in p):
        print("The palette is not set yet: nothing to check.")
        return 0
    usable = {}
    for mode, palette in palettes.items():
        usable[mode] = {}
        for key in COLOURS:
            value = palette.get(key)
            if value is None:
                findings.append(f"{TOKENS}: {mode}: {key} is not set")
            elif not isinstance(value, str) or not HEX.match(value):
                findings.append(f"{TOKENS}: {mode}: {key} is '{value}', not #RRGGBB")
            else:
                usable[mode][key] = value
    for mode, palette in palettes.items():
        for fgs, bgs, kind, minimum in PAIRS:
            for fg in fgs:
                for bg in bgs:
                    if fg not in usable[mode] or bg not in usable[mode]:
                        continue
                    r = ratio(usable[mode][fg], usable[mode][bg])
                    if minimum is None:
                        result = "reported"
                    else:
                        result = "passes" if r >= minimum else "fails"
                    line = f"{mode}: {fg} on {bg} is {shown(r)}"
                    if minimum is None:
                        line += f", {kind}: no minimum"
                    else:
                        line += f", {kind}, minimum {minimum:g}:1: {result}"
                        if kind == "text":
                            line += f"; {'meets' if r >= ENHANCED else 'under'} the enhanced 7:1"
                    report.append(line)
                    rows.append({"mode": mode, "fg": fg, "bg": bg, "kind": kind, "ratio": round(r, 4),
                                 "minimum": minimum, "result": result})
                    if result == "fails":
                        findings.append(f"{TOKENS}: {mode}: {fg} on {bg} is {shown(r)}, under the minimum "
                                        f"{minimum:g}:1")
    brands = sorted({k for p in palettes.values() for k in p if BRAND.match(k)}, key=lambda k: int(k[6:]))
    for key in brands:
        for mode, other in (("light", "dark"), ("dark", "light")):
            value = palettes[mode].get(key)
            if value is None:
                findings.append(f"{TOKENS}: {key} has no {mode} value; a brand token needs both")
            elif not isinstance(value, str) or not HEX.match(value):
                findings.append(f"{TOKENS}: {mode}: {key} is '{value}', not #RRGGBB")
            elif "bg" in usable[mode]:
                r = ratio(value, usable[mode]["bg"])
                report.append(f"{mode}: {key} on bg is {shown(r)}, logo colour: no minimum")
                rows.append({"mode": mode, "fg": key, "bg": "bg", "kind": "logo", "ratio": round(r, 4),
                             "minimum": None, "result": "reported"})
    if as_json:
        for row in rows:
            print(json.dumps(row))
    else:
        for line in report:
            print(line)
    for line in findings:
        print(line)
    return 1 if findings else 0


def licence_files(folder):
    return sorted(n for n in os.listdir(folder)
                  if n in ("OFL.txt", "UFL.txt") or n.upper().startswith(("LICENSE", "LICENCE")))


def known_licence(text):
    low = " ".join(text.lower().split())
    for spdx, (markers, _, _) in KNOWN.items():
        if all(m in low for m in markers):
            return spdx
    return None


def font_facts(path):
    """The family name, the licence description and URL, and fsType of one font file."""
    from fontTools.ttLib import TTFont
    font = TTFont(path, lazy=True)
    name = font["name"]
    family = name.getDebugName(16) or name.getDebugName(1)
    return family, name.getDebugName(13) or "", name.getDebugName(14) or "", font["OS/2"].fsType


def font_result(role, spec):
    """(result, reasons, suggest_person) for one font role; result is known, person, missing or not-shipped."""
    family = spec.get("family")
    files = spec.get("files")
    if files is None:
        return "not-shipped", [], False
    folder = os.path.join(IDENTITY, files)
    if not os.path.isdir(folder):
        return "missing", [f"the font folder {files} does not exist"], False
    fonts = sorted(n for n in os.listdir(folder) if n.lower().endswith(FONT_FILES))
    if not fonts:
        return "missing", [f"{files} holds no font file"], False
    lic = licence_files(folder)
    if len(lic) != 1:
        what = "no licence file" if not lic else f"more than one licence file ({', '.join(lic)})"
        return "missing", [f"{files} has {what}"], False
    with open(os.path.join(folder, lic[0]), encoding="utf-8", errors="replace") as fh:
        found = known_licence(fh.read())
    missing, person, suggest = [], [], False
    if found and spec.get("licence") != found:
        missing.append(f"tokens.json says {spec.get('licence')}, the licence file is {found}")
    for n in fonts:
        fam, desc, url, fstype = font_facts(os.path.join(folder, n))
        if fam != family:
            missing.append(f"{n} is of the family {fam}, not {family}")
        usage = fstype & 0x000F
        if usage in (2, 4) or fstype & 0x0200:
            kind = {2: "restricted", 4: "preview and print only"}.get(usage, "bitmap only")
            person.append(f"{n} limits its embedding ({kind})")
            suggest = True
        text = f"{desc} {url}".lower()
        for word in LIMITS:
            if word in text:
                person.append(f"{n} says '{word}' in its own licence text")
                suggest = True
        if found and (desc or url):
            _, names, urls = KNOWN[found]
            if not any(m in text for m in names + urls):
                person.append(f"{n} names another licence in its own licence text")
    if not found:
        person.insert(0, "the licence file is not one the check knows")
    if missing:
        return "missing", missing, False
    if person:
        return "person", person, suggest
    return "known", [found], False


def fonts(as_json=False):
    tokens = load_tokens()
    roles = ((tokens.get("type") or {}).get("fonts") or {})
    findings, report, rows = [], [], []
    for role in ROLES:
        spec = roles.get(role) or {}
        family = spec.get("family")
        if not family:
            continue
        label = f"{role} ({family})"
        result, reasons, suggest = font_result(role, spec)
        review = spec.get("licence_review") or {}
        if result == "known":
            report.append(f"{label}: known open licence {reasons[0]}")
        elif result == "not-shipped":
            report.append(f"{label}: not shipped; the reader's device supplies it")
        elif result == "person" and review.get("by") and review.get("date"):
            report.append(f"{label}: read by {review['by']} on {review['date']}: this is their reading")
        elif result == "person":
            line = f"{TOKENS}: {label}: needs a person: {'; '.join(reasons)}"
            if suggest:
                line += ". A qualified person should read this licence before the company uses the font"
            findings.append(line)
            report.append(f"{label}: needs a person")
        else:
            findings.append(f"{TOKENS}: {label}: missing evidence: {'; '.join(reasons)}")
            report.append(f"{label}: missing evidence")
        rows.append({"role": role, "family": family, "result": result, "reasons": reasons,
                     "review": review or None})
    if as_json:
        for row in rows:
            print(json.dumps(row))
    else:
        if not rows:
            print("No font is chosen yet: nothing to check.")
        for line in report:
            print(line)
    for line in findings:
        print(line)
    if not as_json:
        print(CLOSING)
    return 1 if findings else 0


CSS = f"{IDENTITY}/tokens.css"
FONTS_CSS = f"{IDENTITY}/fonts.css"
BOARD = f"{IDENTITY}/board.md"
FORMATS = {".ttf": "truetype", ".otf": "opentype", ".woff": "woff", ".woff2": "woff2"}
INPUTS = re.compile(r"<!-- inputs: (sha256:[0-9a-f]{64}) -->")


def declarations(palette, keys):
    return [f"  --color-{k}: {palette[k]};" for k in keys if isinstance(palette.get(k), str) and HEX.match(palette[k])]


def tokens_css(tokens):
    light, dark = tokens.get("light") or {}, tokens.get("dark") or {}
    keys = list(COLOURS) + sorted({k for p in (light, dark) for k in p if BRAND.match(k)}, key=lambda k: int(k[6:]))
    fonts_ = []
    for role in ROLES:
        spec = ((tokens.get("type") or {}).get("fonts") or {}).get(role) or {}
        if spec.get("family"):
            stack = f'"{spec["family"]}"' + (f", {spec['fallback']}" if spec.get("fallback") else "")
            fonts_.append(f"  --font-{role}: {stack};")
    dark_lines = declarations(dark, keys)
    out = ["/* Generated from tokens.json: do not edit. The light palette is the default; the dark palette applies",
           "   under prefers-color-scheme: dark and under data-theme=\"dark\". */",
           ":root {", *declarations(light, keys), *fonts_, "}",
           "@media (prefers-color-scheme: dark) {", "  :root:not([data-theme=\"light\"]) {",
           *["  " + d for d in dark_lines], "  }", "}",
           ":root[data-theme=\"dark\"] {", *dark_lines, "}"]
    return "\n".join(out) + "\n"


def fonts_css(tokens):
    out = ["/* Generated from tokens.json and the font files: do not edit. One @font-face for each shipped font file. */"]
    seen = set()
    for role in ROLES:
        spec = ((tokens.get("type") or {}).get("fonts") or {}).get(role) or {}
        files = spec.get("files")
        if not spec.get("family") or not files:
            continue
        folder = os.path.join(IDENTITY, files)
        if not os.path.isdir(folder):
            continue
        for n in sorted(os.listdir(folder)):
            ext = os.path.splitext(n)[1].lower()
            rel = f"{files.rstrip('/')}/{n}"
            if ext not in FORMATS or rel in seen:
                continue
            seen.add(rel)
            from fontTools.ttLib import TTFont
            font = TTFont(os.path.join(folder, n), lazy=True)
            weight = font["OS/2"].usWeightClass
            italic = bool(font["OS/2"].fsSelection & 1)
            out += ["@font-face {", f'  font-family: "{spec["family"]}";',
                    f'  src: url("{rel}") format("{FORMATS[ext]}");', f"  font-weight: {weight};",
                    f"  font-style: {'italic' if italic else 'normal'};", "  font-display: swap;", "}"]
    return "\n".join(out) + "\n"


def generated(write=False):
    tokens = load_tokens()
    findings = []
    for path, text in ((CSS, tokens_css(tokens)), (FONTS_CSS, fonts_css(tokens))):
        try:
            with open(path, encoding="utf-8") as fh:
                current = fh.read()
        except OSError:
            current = None
        if current == text:
            continue
        if write:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(text)
            print(f"{path}: written")
        else:
            findings.append(f"{path}: out of date with tokens.json; generate it again")
    if not findings and not write:
        print("tokens.css and fonts.css are up to date.")
    for line in findings:
        print(line)
    return 1 if findings else 0


def board_inputs_hash():
    """One SHA-256 over the board's inputs: tokens.json, fonts.css, the font files, the logo folder, the sample images
    and imagery.md. The board records it; the freshness check compares it."""
    paths = [TOKENS, FONTS_CSS, "docs/7-branding/imagery.md"]
    for folder in (f"{IDENTITY}/fonts", f"{IDENTITY}/logo", "docs/7-branding/imagery"):
        for base, _, names in os.walk(folder):
            paths += [os.path.join(base, n) for n in names]
    lines = []
    for path in sorted(set(paths)):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                lines.append(f"{path}\t{hashlib.sha256(fh.read()).hexdigest()}")
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()


def board_fresh():
    try:
        with open(BOARD, encoding="utf-8") as fh:
            m = INPUTS.search(fh.read())
    except OSError:
        m = None
    if not m:
        print("The brand board is not made yet: nothing to compare.")
        return 0
    if m.group(1) != board_inputs_hash():
        print(f"{BOARD}: out of date with its inputs; make the board again")
        return 1
    print("The brand board matches its inputs.")
    return 0


def main(argv):
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], check=False, capture_output=True, text=True)
    if root.returncode != 0:
        print("not inside the company's repository", file=sys.stderr)
        return 2
    os.chdir(root.stdout.strip())
    command, args = (argv[0], argv[1:]) if argv else ("", [])
    try:
        if command == "contrast":
            return contrast(as_json="--json" in args)
        if command == "fonts":
            return fonts(as_json="--json" in args)
        if command == "tokens":
            return generated(write="--write" in args)
        if command == "board-fresh":
            return board_fresh()
        if command == "check":
            return max(contrast(), fonts(), generated(), board_fresh())
    except CannotRun as e:
        print(e)
        return 2
    print("usage: brand.py contrast [--json] | fonts [--json] | tokens [--write] | board-fresh | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
