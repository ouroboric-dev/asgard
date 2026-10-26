#!/usr/bin/env python3
"""The brand checks: the palettes and fonts in docs/7-branding/identity/tokens.json.

    python3 .ouroboric/checks/brand.py contrast [--json]   every text and shape pair, in light and dark mode
    python3 .ouroboric/checks/brand.py check               every brand check; run.sh runs this

Each finding prints as `path: what is wrong`. Exit codes: 0 when every check passes, 1 when a check has a finding,
2 when a check cannot run (tokens.json is not valid JSON).
"""
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


def main(argv):
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True)
    if root.returncode != 0:
        print("not inside the company's repository", file=sys.stderr)
        return 2
    os.chdir(root.stdout.strip())
    command, args = (argv[0], argv[1:]) if argv else ("", [])
    try:
        if command == "contrast":
            return contrast(as_json="--json" in args)
        if command == "check":
            return contrast()
    except CannotRun as e:
        print(e)
        return 2
    print("usage: brand.py contrast [--json] | check", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
