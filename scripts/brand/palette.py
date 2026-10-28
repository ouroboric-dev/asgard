"""Palette rounds for step 6b (brand tools spec §3.2): every preset is checked with the company's own contrast rules
before it is shown, and a failing preset refuses the round.

    palette.py DIR ROUND.json

ROUND.json: {"round": 1, "presets": [{"id": "calm", "name": "Calm blue", "light": {...}, "dark": {...}}]}. Each mode
holds every colour token (#RRGGBB) and, for each brand token (brand-1, ...), a value in both modes. The result is
DIR/docs/7-branding/identity/choices/palette-round-<round>.json, which the palette page reads; nothing is written for a refused round.
"""
import json
import os
import re
import sys

MAX_PRESETS, MAX_ROUNDS = 4, 3
OUT = "docs/7-branding/identity/choices/palette-round-{}.json"


def main(argv):
    if len(argv) != 2:
        print("usage: brand.sh palette DIR ROUND.json", file=sys.stderr)
        return 2
    company, path = argv
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"brand.sh palette: cannot read {path} as JSON ({e})", file=sys.stderr)
        return 2
    checks = os.path.join(company, ".ouroboric", "checks")
    if not os.path.isfile(os.path.join(checks, "brand.py")):
        print(f"brand.sh palette: {company} is not a company folder: no .ouroboric/checks/brand.py", file=sys.stderr)
        return 2
    sys.dont_write_bytecode = True
    sys.path.insert(0, os.path.abspath(checks))
    import brand

    problems = []
    presets = spec.get("presets") if isinstance(spec, dict) else None
    rnd = spec.get("round") if isinstance(spec, dict) else None
    if not isinstance(rnd, int) or rnd < 1:
        problems.append("the round needs its number: \"round\": 1")
    elif rnd > MAX_ROUNDS:
        problems.append("three rounds have been shown without a choice: ask the founder what is missing "
                        f"instead of offering round {rnd}")
    if not isinstance(presets, list) or not presets:
        problems.append("the round needs a list of presets")
        presets = []
    if len(presets) > MAX_PRESETS:
        problems.append(f"a round has four presets at most; this one has {len(presets)}")
    seen, kept = set(), []
    for i, preset in enumerate(presets, 1):
        name = preset.get("id") if isinstance(preset, dict) and isinstance(preset.get("id"), str) else f"preset {i}"
        if name in seen:
            problems.append(f"the preset id {name} appears twice")
        seen.add(name)
        if not isinstance(preset, dict) or not isinstance(preset.get("name"), str):
            problems.append(f"{name}: needs a name")
            continue
        palettes, ok = {}, True
        for mode in ("light", "dark"):
            values = preset.get(mode)
            if not isinstance(values, dict):
                problems.append(f"{name}: {mode} is not a palette")
                ok = False
                continue
            palettes[mode] = {}
            for key in brand.COLOURS:
                value = values.get(key)
                if value is None:
                    problems.append(f"{name}: {mode}: {key} is not set")
                    ok = False
                elif not isinstance(value, str) or not brand.HEX.match(value):
                    problems.append(f"{name}: {mode}: {key} is {value!r}, not #RRGGBB")
                    ok = False
                else:
                    palettes[mode][key] = value.upper()
        if ok:
            brands = {k for m in ("light", "dark") for k in preset[m] if brand.BRAND.match(k)}
            for key in sorted(brands, key=lambda k: int(k[6:])):
                for mode, other in (("light", "dark"), ("dark", "light")):
                    value = preset[mode].get(key)
                    if value is None:
                        problems.append(f"{name}: {key} has no {mode} value; a brand token needs both")
                        ok = False
                    elif not isinstance(value, str) or not brand.HEX.match(value):
                        problems.append(f"{name}: {mode}: {key} is {value!r}, not #RRGGBB")
                        ok = False
        if ok:
            kept.append((name, preset, palettes))
    if problems:
        for line in problems:
            print(f"brand.sh palette: {line}", file=sys.stderr)
        return 2
    roles = spec.get("roles", {}) if isinstance(spec, dict) else {}
    if not isinstance(roles, dict):
        problems.append("roles is the candidate values for single colours: {\"accent\": [{\"id\": ..., \"name\": ..., "
                        "\"light\": \"#RRGGBB\", \"dark\": \"#RRGGBB\"}]}")
        roles = {}
    for role, candidates in roles.items():
        if role not in brand.COLOURS or not isinstance(candidates, list):
            problems.append(f"roles: {role} is not a colour role with a list of candidates")
            continue
        for c in candidates:
            ok = (isinstance(c, dict) and isinstance(c.get("id"), str) and re.match(r"^[a-z0-9-]+$", c["id"])
                  and c["id"] not in ("keep", "custom") and isinstance(c.get("name"), str)
                  and all(isinstance(c.get(m), str) and brand.HEX.match(c[m]) for m in ("light", "dark")))
            if not ok:
                problems.append(f"roles: {role}: a candidate needs an id, a name and a light and a dark #RRGGBB")
    if problems:
        for line in problems:
            print(f"brand.sh palette: {line}", file=sys.stderr)
        return 2
    results, failing = [], []
    for name, preset, palettes in kept:
        rows = brand.palette_rows(palettes)
        fails = [r for r in rows if r["result"] == "fails"]
        for r in fails:
            failing.append(f"{name}: {r['mode']}: {r['fg']} on {r['bg']} is {brand.shown(r['ratio'])}, "
                           f"under the minimum {r['minimum']:g}:1")
        results.append({**{k: v for k, v in preset.items() if k not in ("light", "dark")},
                        "light": preset["light"], "dark": preset["dark"], "contrast": rows,
                        "result": "fails" if fails else "passes"})
    if failing:
        print("brand.sh palette: the round is refused: a preset fails the company's contrast rules. Change its "
              "colours, then run the round again.", file=sys.stderr)
        for line in failing:
            print(f"  {line}", file=sys.stderr)
        return 2
    out = os.path.join(company, OUT.format(rnd))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"round": rnd, "presets": results, **({"roles": roles} if roles else {})}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for r in results:
        text = [row["ratio"] for row in r["contrast"] if row["kind"] == "text"]
        print(f"{r['id']}: passes (lowest text contrast {brand.shown(min(text))})")
    print(f"The round is written: {OUT.format(rnd)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
