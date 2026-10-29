#!/usr/bin/env python3
"""The brand checks: the palettes and fonts in docs/7-branding/identity/tokens.json.

    python3 .ouroboric/checks/brand.py contrast [--json]   every text and shape pair, in light and dark mode
    python3 .ouroboric/checks/brand.py fonts [--json]      the licence evidence of each font the company ships
    python3 .ouroboric/checks/brand.py foundations         the foundations are set and reach their minimums
    python3 .ouroboric/checks/brand.py type                the shipped fonts: glyphs, weights and the body face's italic
    python3 .ouroboric/checks/brand.py components          what the chosen component variants need from the palette
    python3 .ouroboric/checks/brand.py accepted            the accepted exceptions are complete
    python3 .ouroboric/checks/brand.py tokens [--write]    tokens.css and fonts.css from tokens.json; fail when stale
    python3 .ouroboric/checks/brand.py board-fresh         the brand board matches its inputs
    python3 .ouroboric/checks/brand.py reference-fresh     the reference (identity/reference/) matches its inputs
    python3 .ouroboric/checks/brand.py check               every brand check; run.sh runs this

The contrast check needs only the standard library; the font checks read font files with fontTools.

A failure the founder keeps is an accepted exception: an entry of `accepted` in tokens.json with the check's id, the
value that fails, her reason, who and when. A failure whose id and value match is reported as accepted and does not
fail the check. An entry whose value no longer matches is stale: the check fails again. The ids are
`contrast:<mode>:<fg>/<bg>`, `type:<role>:glyphs`, `type:<role>:weights`, `type:body:italic`, `type:body:size`,
`type:scale:minimum`, `type:body:leading`, `focus:width`, `focus:<mode>:<bg>` and `target`.

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
ROLES = ("wordmark", "display", "heading", "body", "ui")
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


ACCEPTED_FIELDS = ("check", "value", "reason", "by", "date")
USED = set()


def accepted_entries(tokens):
    entries = tokens.get("accepted")
    return [e for e in entries if isinstance(e, dict)] if isinstance(entries, list) else []


def judge(tokens, check_id, value, message, findings, report):
    """Record a failed check: as accepted when an entry matches its id and value, as stale when an entry for the id
    has another value, else as a finding. `message` has no path; the finding gets TOKENS in front of it."""
    value = str(value)
    same = [e for e in accepted_entries(tokens) if e.get("check") == check_id]
    for e in same:
        if str(e.get("value")) == value:
            USED.add(id(e))
            report.append(f"{TOKENS}: {message}: accepted: {e.get('reason')} ({e.get('by')}, {e.get('date')})")
            return False
    stale = ""
    if same:
        USED.update(id(e) for e in same)
        stale = f"; the accepted exception for it is stale: it covers {same[0].get('value')}, not {value}"
    findings.append(f"{TOKENS}: {message}{stale}")
    return True


def accepted():
    tokens = load_tokens()
    findings = []
    entries = tokens.get("accepted")
    if entries is not None and not isinstance(entries, list):
        findings.append(f"{TOKENS}: accepted is not a list")
        entries = []
    for i, e in enumerate(entries or []):
        if not isinstance(e, dict):
            findings.append(f"{TOKENS}: accepted[{i}]: is not an entry")
            continue
        for field in ACCEPTED_FIELDS:
            if not isinstance(e.get(field), (str, int, float)) or e.get(field) == "":
                findings.append(f"{TOKENS}: accepted[{i}]: {field} is missing")
    for line in findings:
        print(line)
    return 1 if findings else 0


def unused_exceptions():
    """Entries no check used in this run: the failure they kept is gone. Information, not a failure."""
    for e in accepted_entries(load_tokens()):
        if id(e) not in USED:
            print(f"{TOKENS}: the accepted exception for {e.get('check')} ({e.get('value')}) is no longer needed")


def palette_rows(palettes):
    """The contrast rows of {mode: {token: #RRGGBB}} as data: the same pairs and minimums as the contrast check."""
    rows = []
    for mode, palette in palettes.items():
        for fgs, bgs, kind, minimum in PAIRS:
            for fg in fgs:
                for bg in bgs:
                    if fg not in palette or bg not in palette:
                        continue
                    r = ratio(palette[fg], palette[bg])
                    result = "reported" if minimum is None else ("passes" if r >= minimum else "fails")
                    rows.append({"mode": mode, "fg": fg, "bg": bg, "kind": kind, "ratio": round(r, 4),
                                 "minimum": minimum, "result": result})
    return rows


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
                    kept = None
                    if result == "fails":
                        sub = []
                        message = f"{mode}: {fg} on {bg} is {shown(r)}, under the minimum {minimum:g}:1"
                        if not judge(tokens, f"contrast:{mode}:{fg}/{bg}",
                                     f"{usable[mode][fg].upper()}/{usable[mode][bg].upper()}", message, findings, sub):
                            result, kept = "accepted", sub[0]
                    line = f"{mode}: {fg} on {bg} is {shown(r)}"
                    if minimum is None:
                        line += f", {kind}: no minimum"
                    else:
                        line += f", {kind}, minimum {minimum:g}:1: {result}"
                        if kept:
                            line += kept[kept.index(": accepted:") + len(": accepted"):]
                        if kind == "text":
                            line += f"; {'meets' if r >= ENHANCED else 'under'} the enhanced 7:1"
                    report.append(line)
                    rows.append({"mode": mode, "fg": fg, "bg": bg, "kind": kind, "ratio": round(r, 4),
                                 "minimum": minimum, "result": result})
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


def open_font(path):
    """A font file read with fontTools, which only the checks that read font files need."""
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        raise CannotRun("the font check needs fontTools 4.66.1 and Brotli 1.2.0 to read the font files: "
                        "pip install fonttools==4.66.1 brotli==1.2.0")
    return TTFont(path, lazy=True)


def font_facts(path):
    """The family name, the licence description and URL, and fsType of one font file."""
    font = open_font(path)
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


MIN_BODY, MIN_LEADING, MIN_FOCUS, MIN_FOCUS_CONTRAST, MIN_TARGET = 16, 1.5, 2, 3.0, 24
SIZES = ("small", "body", "h3", "h2", "h1", "display")
LEADINGS = ("body", "heading", "display")
RADII = ("sm", "md", "lg", "button")
ELEVATIONS = ("card", "overlay")


def is_number(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def numbers(v):
    return isinstance(v, list) and bool(v) and all(is_number(x) for x in v)


def missing_foundations(tokens):
    """The foundation keys that are absent or of the wrong shape, as the names a person reads."""
    scale = (tokens.get("type") or {}).get("scale") or {}
    out = []

    def need(name, ok):
        if not ok:
            out.append(name)

    def group(name, value, keys, kind):
        need(name, isinstance(value, dict))
        if isinstance(value, dict):
            for k in keys:
                need(f"{name}.{k}", kind(value.get(k)))

    need("languages", isinstance(tokens.get("languages"), list) and bool(tokens.get("languages")))
    for k in ("base", "ratio", "minimum"):
        need(f"type.scale.{k}", is_number(scale.get(k)))
    group("type.scale.sizes", scale.get("sizes"), SIZES, is_number)
    group("type.scale.lineHeight", scale.get("lineHeight"), LEADINGS, is_number)
    need("space", numbers(tokens.get("space")))
    group("radius", tokens.get("radius"), RADII, is_number)
    group("elevation", tokens.get("elevation"), ELEVATIONS, lambda v: isinstance(v, str) and v != "")
    motion = tokens.get("motion")
    need("motion", isinstance(motion, dict))
    if isinstance(motion, dict):
        need("motion.distance", is_number(motion.get("distance")))
        need("motion.duration", is_number(motion.get("duration")))
        need("motion.easing", isinstance(motion.get("easing"), str) and motion.get("easing") != "")
        need("motion.reduced", motion.get("reduced") in ("none", "fade"))
    focus = tokens.get("focus")
    need("focus", isinstance(focus, dict))
    if isinstance(focus, dict):
        need("focus.role", focus.get("role") in COLOURS)
        need("focus.width", is_number(focus.get("width")))
        need("focus.offset", is_number(focus.get("offset")))
    need("target", is_number(tokens.get("target")))
    need("breakpoints", numbers(tokens.get("breakpoints")))
    need("components", isinstance(tokens.get("components"), dict))
    need("accepted", isinstance(tokens.get("accepted"), list))
    return out


def foundations():
    tokens = load_tokens()
    findings, report = [], []
    absent = missing_foundations(tokens)
    for name in absent:
        findings.append(f"{TOKENS}: {name} is missing")
    scale = (tokens.get("type") or {}).get("scale") or {}

    def minimum(check_id, value, floor, message):
        if is_number(value) and value < floor:
            judge(tokens, check_id, f"{value:g}", message, findings, report)

    sizes, leading = scale.get("sizes") or {}, scale.get("lineHeight") or {}
    if is_number(sizes.get("body")):
        minimum("type:body:size", sizes["body"], MIN_BODY,
                f"the body text is {sizes['body']:g} px, under the minimum {MIN_BODY} px")
    minimum("type:scale:minimum", scale.get("minimum"), MIN_BODY,
            f"the scale's minimum is {scale.get('minimum', 0):g} px, under the minimum {MIN_BODY} px")
    minimum("type:body:leading", leading.get("body"), MIN_LEADING,
            f"the body line height is {leading.get('body', 0):g}, under the minimum {MIN_LEADING:g}")
    focus = tokens.get("focus") if isinstance(tokens.get("focus"), dict) else {}
    minimum("focus:width", focus.get("width"), MIN_FOCUS,
            f"the focus indicator is {focus.get('width', 0):g} px thick, under the minimum {MIN_FOCUS} px")
    minimum("target", tokens.get("target"), MIN_TARGET,
            f"the touch target is {tokens.get('target', 0):g} px, under the minimum {MIN_TARGET} px")
    role = focus.get("role")
    if role in COLOURS:
        for mode in ("light", "dark"):
            palette = tokens.get(mode) or {}
            fg = palette.get(role)
            for bg in ("bg", "surface"):
                other = palette.get(bg)
                if not all(isinstance(v, str) and HEX.match(v) for v in (fg, other)):
                    continue
                r = ratio(fg, other)
                if r < MIN_FOCUS_CONTRAST:
                    judge(tokens, f"focus:{mode}:{bg}", f"{fg.upper()}/{other.upper()}",
                          f"{mode}: the focus colour {role} on {bg} is {shown(r)}, under the minimum "
                          f"{MIN_FOCUS_CONTRAST:g}:1", findings, report)
    for line in report:
        print(line)
    for line in findings:
        print(line)
    if not findings:
        print("The foundations are set and reach their minimums.")
    return 1 if findings else 0


def mix(a, b, pct):
    """The colour `a` at `pct` percent over `b`, as #RRGGBB."""
    ca = [int(a[i:i + 2], 16) for i in (1, 3, 5)]
    cb = [int(b[i:i + 2], 16) for i in (1, 3, 5)]
    return "#%02X%02X%02X" % tuple(round(x * pct / 100 + y * (100 - pct) / 100) for x, y in zip(ca, cb))


def components():
    """What a component variant needs from the palette: the recipes of the token contract use tints and plain text
    colours that the palette pairs do not cover. Link text without an underline must differ from the text by 3:1
    (WCAG 2.2 SC 1.4.1)."""
    tokens = load_tokens()
    findings, report = [], []
    chosen = tokens.get("components") if isinstance(tokens.get("components"), dict) else {}
    seen = False
    for mode in ("light", "dark"):
        p = {k: v for k, v in (tokens.get(mode) or {}).items() if isinstance(v, str) and HEX.match(v)}
        if not all(k in p for k in ("bg", "text", "accent", "accent-text")):
            continue
        seen = True

        def low(check_id, fg, bg, minimum, text):
            r = ratio(fg, bg)
            if r < minimum:
                judge(tokens, check_id, f"{fg.upper()}/{bg.upper()}", f"{mode}: {text} {shown(r)}, under the minimum {minimum:g}:1",
                      findings, report)

        if chosen.get("button") == "soft":
            low(f"components:button:soft:{mode}", p["accent-text"], mix(p["accent"], p["bg"], 16), 4.5,
                "the soft button's accent text on its tint is")
        if chosen.get("button") == "outlined":
            low(f"components:button:outlined:{mode}", p["accent-text"], p["bg"], 4.5,
                "the outlined button's accent text on the background is")
        if chosen.get("link") == "colour":
            low(f"components:link:{mode}", p["accent-text"], p["text"], 3.0, "a link without an underline differs from the text by")
        if chosen.get("message") == "tint":
            for k in ("ok", "warn", "crit"):
                if k in p:
                    low(f"components:message:{k}:{mode}", p[k], mix(p[k], p["bg"], 10), 4.5, f"the {k} message on its tint is")
    if not seen:
        print("The palette is not set yet: nothing to check.")
        return 0
    for line in report:
        print(line)
    for line in findings:
        print(line)
    if not findings:
        print("The chosen components read on the palette.")
    return 1 if findings else 0


TYPOGRAPHY = "\u2019\u201c\u201d\u2013\u2014\u2026\u20ac"  # ’ “ ” – — … €
LANGUAGE_LETTERS = {
    "en": "",
    "pt": "áàâãçéêíóôõúüÁÀÂÃÇÉÊÍÓÔÕÚÜ",
    "es": "áéíñóúüÁÉÍÑÓÚÜ¿¡",
    "fr": "àâæçéèêëîïôœùûüÿÀÂÆÇÉÈÊËÎÏÔŒÙÛÜŸ",
    "de": "äöüßÄÖÜ",
    "it": "àèéìíòóùúÀÈÉÌÒÓÙ",
    "nl": "éèëïÉ",
    "sv": "åäöÅÄÖ",
    "da": "æøåÆØÅ",
    "nb": "æøåÆØÅ",
    "fi": "äöåÄÖÅ",
}


def required_characters(language):
    """The characters a font must cover to set text in the language, or None when the check has no list for it."""
    letters = LANGUAGE_LETTERS.get(str(language).split("-")[0].lower())
    if letters is None:
        return None
    return list(dict.fromkeys(letters + TYPOGRAPHY + "".join(chr(c) for c in range(0x20, 0x7F))))


def font_weights(font):
    """(low, high) of a variable font's weight axis, else (usWeightClass, usWeightClass)."""
    if "fvar" in font:
        for axis in font["fvar"].axes:
            if axis.axisTag == "wght":
                return axis.minValue, axis.maxValue
    w = font["OS/2"].usWeightClass
    return w, w


def font_is_italic(font):
    if "fvar" in font and any(a.axisTag == "ital" for a in font["fvar"].axes):
        return True
    return bool(font["OS/2"].fsSelection & 1) or bool(font["head"].macStyle & 2)


def type_checks():
    tokens = load_tokens()
    findings, report = [], []
    languages = tokens.get("languages") if isinstance(tokens.get("languages"), list) else []
    lists = {}
    for lang in languages:
        chars = required_characters(lang)
        if chars is None:
            judge(tokens, f"languages:{lang}", lang,
                  f"the language {lang} has no list of characters in this check, so its glyphs are not verified",
                  findings, report)
        else:
            lists[str(lang)] = chars
    for role in ROLES:
        spec = ((tokens.get("type") or {}).get("fonts") or {}).get(role) or {}
        family, files = spec.get("family"), spec.get("files")
        if not family or not files:
            continue
        folder = os.path.join(IDENTITY, files)
        if not os.path.isdir(folder):
            continue
        label = f"{role} ({family})"
        opened = [open_font(os.path.join(folder, n)) for n in sorted(os.listdir(folder))
                  if n.lower().endswith(FONT_FILES)]
        if not opened:
            continue
        for lang, chars in lists.items():
            covered = [set(f.getBestCmap()) for f in opened]
            gone = max(([c for c in chars if ord(c) not in cmap] for cmap in covered), key=len)
            if gone:
                judge(tokens, f"type:{role}:glyphs", family,
                      f"{label}: lacks {len(gone)} characters of {lang}, such as {' '.join(gone[:5])}",
                      findings, report)
        have = [font_weights(f) for f in opened]
        ranges = sorted({(lo, hi) for lo, hi in have if lo != hi})
        statics = sorted({lo for lo, hi in have if lo == hi and not any(a <= lo <= b for a, b in ranges)})
        shown_have = ", ".join([f"{a:g} to {b:g}" for a, b in ranges] + [f"{w:g}" for w in statics])
        for w in spec.get("weights") or []:
            if not any(lo <= w <= hi for lo, hi in have):
                judge(tokens, f"type:{role}:weights", w,
                      f"{label}: weight {w} is not in the font files (they have {shown_have})", findings, report)
        if role == "body" and not any(font_is_italic(f) for f in opened):
            judge(tokens, "type:body:italic", family, f"{label} has no italic", findings, report)
    for line in report:
        print(line)
    for line in findings:
        print(line)
    return 1 if findings else 0



CSS = f"{IDENTITY}/tokens.css"
FONTS_CSS = f"{IDENTITY}/fonts.css"
BOARD = f"{IDENTITY}/board.md"
FORMATS = {".ttf": "truetype", ".otf": "opentype", ".woff": "woff", ".woff2": "woff2"}
INPUTS = re.compile(r"<!-- inputs: (sha256:[0-9a-f]{64}) -->")


def declarations(palette, keys):
    return [f"  --color-{k}: {palette[k]};" for k in keys if isinstance(palette.get(k), str) and HEX.match(palette[k])]


def number(value):
    """A JSON number as CSS text: 8 and 8.0 are '8', 1.25 stays '1.25'; anything else is None."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return f"{value:g}"


def px(value):
    n = number(value)
    return None if n is None else f"{n}px"


def foundation_declarations(tokens):
    """(always, reduced): the foundation variables, and the ones a device that asks for reduced motion overrides."""
    out, scale = [], (tokens.get("type") or {}).get("scale") or {}

    def add(name, value):
        if value is not None:
            out.append(f"  --{name}: {value};")

    for name, value in (scale.get("sizes") or {}).items():
        add(f"text-{name}", px(value))
    for name, value in (scale.get("lineHeight") or {}).items():
        add(f"leading-{name}", number(value))
    space = tokens.get("space")
    for i, value in enumerate(space if isinstance(space, list) else [], 1):
        add(f"space-{i}", px(value))
    for name, value in (tokens.get("radius") or {}).items():
        add(f"radius-{name}", px(value))
    for name, value in (tokens.get("elevation") or {}).items():
        if isinstance(value, str):
            add(f"shadow-{name}", value)
    motion = tokens.get("motion") or {}
    add("motion-distance", px(motion.get("distance")))
    duration = number(motion.get("duration"))
    add("motion-duration", None if duration is None else f"{duration}ms")
    if isinstance(motion.get("easing"), str):
        add("motion-easing", motion["easing"])
    focus = tokens.get("focus") or {}
    if focus.get("role") in COLOURS:
        add("focus-color", f"var(--color-{focus['role']})")
    add("focus-width", px(focus.get("width")))
    add("focus-offset", px(focus.get("offset")))
    add("target", px(tokens.get("target")))
    bps = tokens.get("breakpoints")
    for i, value in enumerate(bps if isinstance(bps, list) else [], 1):
        add(f"bp-{i}", px(value))
    # a device that asks for reduced motion: "none" removes the movement and the time, "fade" keeps the time only
    reduced = []
    if motion.get("reduced") in ("none", "fade"):
        reduced.append("  --motion-distance: 0px;")
        if motion["reduced"] == "none":
            reduced.append("  --motion-duration: 0ms;")
    return out, reduced


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
    found, reduced = foundation_declarations(tokens)
    out = ["/* Generated from tokens.json: do not edit. The light palette is the default; the dark palette applies",
           "   under prefers-color-scheme: dark and under data-theme=\"dark\". */",
           ":root {", *declarations(light, keys), *fonts_, *found, "}",
           "@media (prefers-color-scheme: dark) {", "  :root:not([data-theme=\"light\"]) {",
           *["  " + d for d in dark_lines], "  }", "}",
           ":root[data-theme=\"dark\"] {", *dark_lines, "}"]
    if reduced:
        out += ["@media (prefers-reduced-motion: reduce) {", "  :root {", *["  " + r for r in reduced], "  }", "}"]
    return "\n".join(out) + "\n"


WEB = "web"


def web_path(files, name):
    """Where the web (WOFF2) form of a shipped font lives, relative to identity/."""
    return f"{files.rstrip('/')}/{WEB}/{os.path.splitext(name)[0]}.woff2"


def web_characters(tokens):
    """The characters a web font keeps: the clients' languages and Latin-1; None keeps every glyph, for a language
    this check has no list for or when no language is set."""
    languages = tokens.get("languages")
    if not isinstance(languages, list) or not languages:
        return None
    keep = {chr(c) for c in range(0xA0, 0x100)}
    for language in languages:
        chars = required_characters(language)
        if chars is None:
            return None
        keep.update(chars)
    return keep


def shipped_fonts(tokens):
    """(spec, source path, web path) for each shipped font file, once."""
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
            rel = f"{files.rstrip('/')}/{n}"
            if os.path.splitext(n)[1].lower() not in FORMATS or rel in seen:
                continue
            seen.add(rel)
            yield spec, os.path.join(folder, n), os.path.join(IDENTITY, web_path(files, n))


def make_web_font(source, target, keep):
    """Write the WOFF2 form of a font file, subset to `keep` (every glyph when None). The name table stays whole, so
    the licence text travels with the file."""
    try:
        from fontTools import subset
        from fontTools.ttLib import TTFont
        os.makedirs(os.path.dirname(target), exist_ok=True)
        if keep is None:
            font = TTFont(source)
            font.flavor = "woff2"
            font.save(target)
            return
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["*"]
        options.name_IDs = ["*"]
        options.name_languages = ["*"]
        options.notdef_outline = True
        font = subset.load_font(source, options)
        subsetter = subset.Subsetter(options)
        subsetter.populate(unicodes=sorted(ord(c) for c in keep))
        subsetter.subset(font)
        subset.save_font(font, target, options)
    except ImportError:
        raise CannotRun("the web fonts need fontTools 4.66.1 and Brotli 1.2.0: "
                        "pip install fonttools==4.66.1 brotli==1.2.0")


def web_font_fresh(source, target, keep):
    """Does the WOFF2 file hold exactly the glyphs the source keeps?"""
    if not os.path.isfile(target):
        return False
    wanted = set(open_font(source).getBestCmap())
    if keep is not None:
        wanted &= {ord(c) for c in keep}
    try:
        return set(open_font(target).getBestCmap()) == wanted
    except Exception:  # a file that is not a font
        return False


def web_fonts(tokens, write):
    findings = []
    keep = web_characters(tokens)
    for _, source, target in shipped_fonts(tokens):
        if web_font_fresh(source, target, keep):
            continue
        if write:
            make_web_font(source, target, keep)
            print(f"{target}: written")
        else:
            findings.append(f"{target}: out of date with the font and tokens.json; generate it again")
    return findings


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
            font = open_font(os.path.join(folder, n))
            web = web_path(files, n)
            # a variable font covers a range of weights: its weight axis, not its default instance
            axes = {a.axisTag: a for a in font["fvar"].axes} if "fvar" in font else {}
            if "wght" in axes:
                weight = f"{axes['wght'].minValue:g} {axes['wght'].maxValue:g}"
            else:
                weight = font["OS/2"].usWeightClass
            italic = bool(font["OS/2"].fsSelection & 1)
            out += ["@font-face {", f'  font-family: "{spec["family"]}";',
                    f'  src: url("{web}") format("woff2");', f"  font-weight: {weight};",
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
    findings += web_fonts(tokens, write)
    if not findings and not write:
        print("tokens.css, fonts.css and the web fonts are up to date.")
    for line in findings:
        print(line)
    return 1 if findings else 0


def board_inputs_hash():
    """One SHA-256 over the board's inputs: tokens.json, fonts.css, the font files, the logo folder, the logo's choice record,
    the sample images and imagery.md. The board records it; the freshness check compares it."""
    paths = [TOKENS, FONTS_CSS, "docs/7-branding/imagery.md", f"{IDENTITY}/choices/logo.json"]
    for folder in (f"{IDENTITY}/fonts", f"{IDENTITY}/logo", "docs/7-branding/imagery"):
        for base, _, names in os.walk(folder):
            paths += [os.path.join(base, n) for n in names]
    lines = []
    for path in sorted(set(paths)):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                lines.append(f"{path}\t{hashlib.sha256(fh.read()).hexdigest()}")
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()


REFERENCE = f"{IDENTITY}/reference"
REFERENCE_INPUTS = re.compile(r"/\* inputs: (sha256:[0-9a-f]{64}) \*/")


def reference_inputs_hash():
    """One SHA-256 over the reference's inputs: tokens.json, the generated CSS, the font files and the logo's SVGs. The
    reference records it; the freshness check compares it."""
    paths = [TOKENS, CSS, FONTS_CSS]
    for folder in (f"{IDENTITY}/fonts", f"{IDENTITY}/logo"):
        for base, _, names in os.walk(folder):
            paths += [os.path.join(base, n) for n in names if n.lower().endswith((".svg", ".ttf", ".otf", ".woff", ".woff2"))]
    lines = []
    for path in sorted(set(paths)):
        if os.path.isfile(path):
            with open(path, "rb") as fh:
                lines.append(f"{path}\t{hashlib.sha256(fh.read()).hexdigest()}")
    return "sha256:" + hashlib.sha256("\n".join(lines).encode()).hexdigest()


def reference_fresh():
    try:
        with open(f"{REFERENCE}/components.css", encoding="utf-8") as fh:
            m = REFERENCE_INPUTS.search(fh.read())
    except OSError:
        m = None
    if not m:
        print("The reference is not made yet: nothing to compare.")
        return 0
    if m.group(1) != reference_inputs_hash():
        print(f"{REFERENCE}: out of date with its inputs; make the reference again")
        return 1
    print("The reference matches its inputs.")
    return 0


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
        if command == "foundations":
            return foundations()
        if command == "type":
            return type_checks()
        if command == "components":
            return components()
        if command == "accepted":
            return accepted()
        if command == "tokens":
            return generated(write="--write" in args)
        if command == "reference-fresh":
            return reference_fresh()
        if command == "board-fresh":
            return board_fresh()
        if command == "check":
            code = max(contrast(), fonts(), foundations(), type_checks(), components(), generated(), board_fresh(), reference_fresh(), accepted())
            unused_exceptions()
            return code
    except CannotRun as e:
        print(e)
        return 2
    print("usage: brand.py contrast [--json] | fonts [--json] | foundations | type | components | accepted | tokens [--write] | "
          "board-fresh | reference-fresh | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
