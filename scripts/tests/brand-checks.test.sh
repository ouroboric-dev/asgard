#!/usr/bin/env bash
# Tests for the company template's brand checks: .ouroboric/checks/brand.py (the contrast check, the font licence
# check, the generated files).   scripts/tests/brand-checks.test.sh   (needs python3)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
T="$(mktemp -d)"
trap 'rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
says() { grep -q -- "$2" "$1"; }
# shellcheck disable=SC2329
quiet_about() { ! grep -q -- "$2" "$1"; }
# shellcheck disable=SC2329
builds() { (cd "$1" && mkdocs build --strict --quiet --config-file .ouroboric/mkdocs.yml); }
# shellcheck disable=SC2329
says_all() { local f="$1" p; shift; for p in "$@"; do grep -q -- "$p" "$f" || return 1; done; }

# A company to change: scaffolded, a git repository (the checks find its root through git).
"$NEW" --name "Example Studio" --date 2026-10-27 "$T/a" >/dev/null 2>&1
git -C "$T/a" init -q -b main
TOKENS="$T/a/docs/7-branding/identity/tokens.json"
cp "$TOKENS" "$T/tokens.template.json"
for f in tokens.css fonts.css board.md; do cp "$T/a/docs/7-branding/identity/$f" "$T/$f.template" 2>/dev/null; done

# brand MODE ... : run brand.py in the company; stdout and stderr to $T/out, the exit code to $T/code.
brand() { (cd "$T/a" && python3 .ouroboric/checks/brand.py "$@") >"$T/out" 2>&1; echo $? >"$T/code"; }
# shellcheck disable=SC2329 # code runs through check
code() { [ "$(cat "$T/code")" = "$1" ]; }
# palette KEY=VALUE ... : the template's tokens.json, then each light.KEY or dark.KEY set (null for null).
palette() {
  python3 - "$T/tokens.template.json" "$TOKENS" "$@" <<'EOF'
import json, sys
src, dst, *pairs = sys.argv[1:]
t = json.load(open(src))
for pair in pairs:
    key, value = pair.split("=", 1)
    mode, name = key.split(".", 1)
    t[mode][name] = None if value == "null" else value
json.dump(t, open(dst, "w"), indent=2)
EOF
}
GOOD=(light.bg=#FFFFFF light.surface=#F5F5F5 light.border=#DDDDDD light.text=#1A1A1A light.muted=#555555
  light.accent=#0B5FCC light.accent-text=#0B5FCC light.on-accent=#FFFFFF light.ok=#1B6E20 light.warn=#8A5A00
  light.crit=#B00020
  dark.bg=#121212 dark.surface=#1E1E1E dark.border=#333333 dark.text=#EDEDED dark.muted=#B0B0B0
  dark.accent=#6EA8FE dark.accent-text=#6EA8FE dark.on-accent=#121212 dark.ok=#81C784 dark.warn=#FFB74D
  dark.crit=#EF9A9A)

# The contrast check (spec §5.1).
brand contrast
check "the template's empty palette passes (5.1.8)" code 0
check "and says the palette is not set" says "$T/out" "not set"

palette "${GOOD[@]}"; brand contrast
check "a palette whose pairs all reach their minimum passes" code 0
check "it tests the light palette and the dark palette (5.1.1)" says_all "$T/out" "^light" "^dark"
check "it reports the enhanced level for text, for information" says "$T/out" "7:1"
check "it reports the border, which has no minimum" says "$T/out" "border"

palette "${GOOD[@]}" light.muted=#999999; brand contrast
check "a text pair below 4.5:1 fails (5.1.4)" code 1
check "the failure names the mode, the tokens, the ratio and the minimum (5.1.5)" \
  says "$T/out" "tokens.json: light: muted on bg is 2.84:1, under the minimum 4.5:1"

palette "${GOOD[@]}" dark.accent=#2A2A2A dark.on-accent=#FFFFFF; brand contrast
check "a shape below 3:1 fails" code 1
check "and names it as a shape" says "$T/out" "dark: accent on bg is .*minimum 3:1"

palette "${GOOD[@]}" light.border=#FEFEFE; brand contrast
check "a border with no contrast does not fail: it is decorative" code 0

palette "${GOOD[@]}" light.text=#767676 light.muted=#767676 light.surface=#FFFFFF; brand contrast
check "#767676 on #FFFFFF passes at 4.54:1 (5.1.10)" code 0
check "the ratio is shown rounded down to two decimals (5.1.6)" says "$T/out" "4.54:1"
palette "${GOOD[@]}" light.text=#777777 light.surface=#FFFFFF; brand contrast
check "#777777 on #FFFFFF fails at 4.47:1 (5.1.10)" code 1
check "and is not rounded up to pass (5.1.3)" says "$T/out" "text on bg is 4.47:1"

palette "${GOOD[@]}" light.text=red; brand contrast
check "a value that is not #RRGGBB fails (5.1.7)" code 1
check "and names the token" says "$T/out" "light: text is 'red', not #RRGGBB"

palette "${GOOD[@]}" light.warn=null dark.crit=null; brand contrast
check "a palette with some values missing fails (5.1.9)" code 1
check "and names each missing token" says_all "$T/out" "light: warn is not set" "dark: crit is not set"

palette "${GOOD[@]}" light.brand-1=#FFF5F5 dark.brand-1=#151515; brand contrast
check "a brand token never fails by its contrast (5.1.11)" code 0
check "but it is reported, for information" says "$T/out" "brand-1"
palette "${GOOD[@]}" light.brand-1=#C2185B; brand contrast
check "a brand token with a value in one mode only fails (5.1.11)" code 1
check "and says the other mode is missing" says "$T/out" "brand-1 has no dark value"

echo '{ not json' >"$TOKENS"; brand contrast
check "tokens.json that is not JSON stops the check with code 2" code 2

palette "${GOOD[@]}"; brand contrast --json
check "--json prints one object per pair" python3 -c '
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
keys = {"mode", "fg", "bg", "kind", "ratio", "minimum", "result"}
assert rows and all(keys <= r.keys() for r in rows), rows[:1]
' "$T/out"

# The font licence check (spec §5.2). Fonts are built here with fontTools; no font file is committed.
ID="$T/a/docs/7-branding/identity"
# font FILE FAMILY [FSTYPE] [DESCRIPTION] [URL] [variable]: a minimal TrueType font with those name and OS/2
# values; "variable" gives it a weight axis from 100 to 900. Environment: FONT_CHARS (the characters it covers,
# default "A"), FONT_WEIGHT (usWeightClass), FONT_ITALIC=1 (an italic face), FONT_ITAL_AXIS=1 (an italic axis).
font() {
  python3 - "$@" <<'EOF'
import sys
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
path, family = sys.argv[1], sys.argv[2]
fstype = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 0
desc = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
url = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
variable = len(sys.argv) > 6 and sys.argv[6] == "variable"
import os
chars = os.environ.get("FONT_CHARS", "A")
gname = {c: "g%04X" % ord(c) for c in chars}
fb = FontBuilder(1000, isTTF=True)
fb.setupGlyphOrder([".notdef", *gname.values()])
fb.setupCharacterMap({ord(c): n for c, n in gname.items()})
pen = TTGlyphPen(None)
pen.moveTo((0, 0)); pen.lineTo((500, 700)); pen.lineTo((1000, 0)); pen.closePath()
glyph = pen.glyph()
fb.setupGlyf({".notdef": glyph, **{n: glyph for n in gname.values()}})
fb.setupHorizontalMetrics({".notdef": (1000, 0), **{n: (1000, 0) for n in gname.values()}})
fb.setupHorizontalHeader(ascent=800, descent=-200)
names = {"familyName": family, "styleName": "Regular"}
if desc:
    names["licenseDescription"] = desc
if url:
    names["licenseInfoURL"] = url
fb.setupNameTable(names)
italic = os.environ.get("FONT_ITALIC") == "1"
fb.setupOS2(fsType=fstype, usWeightClass=int(os.environ.get("FONT_WEIGHT", "400")), fsSelection=1 if italic else 0x40)
fb.setupPost()
if italic:
    fb.font["head"].macStyle = 2
if variable:
    axes = [("wght", 100, 400, 900, "Weight")]
    if os.environ.get("FONT_ITAL_AXIS") == "1":
        axes.append(("ital", 0, 0, 1, "Italic"))
    fb.setupFvar(axes=axes, instances=[])
fb.save(path)
EOF
}
OFL='Copyright 2026 The Test Project Authors.
This Font Software is licensed under the SIL Open Font License, Version 1.1.
SIL OPEN FONT LICENSE Version 1.1 - 26 February 2007'
APACHE='                                 Apache License
                           Version 2.0, January 2004
                        http://www.apache.org/licenses/'
UFL='UBUNTU FONT LICENCE Version 1.0'
# role ROLE FAMILY FILES LICENCE [REVIEW_BY]: set one font role in tokens.json (FILES and LICENCE may be null).
role() {
  python3 - "$TOKENS" "$@" <<'EOF'
import json, sys
path, role, family, files, licence = sys.argv[1:6]
by = sys.argv[6] if len(sys.argv) > 6 else None
t = json.load(open(path))
f = t["type"]["fonts"][role]
f.update({"family": family, "fallback": "serif", "weights": [400],
          "files": None if files == "null" else files, "licence": None if licence == "null" else licence,
          "source": "https://example.org/fonts"})
if by:
    f["licence_review"] = {"by": by, "date": "2026-10-27"}
json.dump(t, open(path, "w"), indent=2)
EOF
}
# fresh: the template's tokens and no font folder.
fresh() { cp "$T/tokens.template.json" "$TOKENS"; rm -rf "$ID/fonts"; }
# ofl_font FAMILY [FSTYPE] [DESCRIPTION]: fonts/test/ with OFL.txt and one font of that family.
ofl_font() { mkdir -p "$ID/fonts/test"; printf '%s\n' "$OFL" >"$ID/fonts/test/OFL.txt"; font "$ID/fonts/test/Test-Regular.ttf" "$@"; }
# shellcheck disable=SC2329
words_only_in_closing() { ! grep -v "It is not legal advice" "$1" | grep -qiE "legal|allowed|permitted"; }

fresh; brand fonts
check "fonts: no font chosen yet passes" code 0
check "and every report ends with the closing sentence (5.2.7)" \
  says "$T/out" "This check compares licence files and font data. It is not legal advice."

fresh; ofl_font "Test Serif"; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "an OFL font with its licence file passes as a known open licence (5.2.1)" code 0
check "and is reported so" says "$T/out" "heading (Test Serif): known open licence OFL-1.1"
sum_before="$(sha256sum "$ID/fonts/test/Test-Regular.ttf")"
check "the check does not change the font file (5.2.9)" [ "$(sha256sum "$ID/fonts/test/Test-Regular.ttf")" = "$sum_before" ]

fresh; mkdir -p "$ID/fonts/test"; printf '%s\n' "$APACHE" >"$ID/fonts/test/LICENSE.txt"
font "$ID/fonts/test/Test-Regular.ttf" "Test Sans"; role body "Test Sans" fonts/test Apache-2.0; brand fonts
check "an Apache-2.0 font passes" code 0
fresh; mkdir -p "$ID/fonts/test"; printf '%s\n' "$UFL" >"$ID/fonts/test/UFL.txt"
font "$ID/fonts/test/Test-Regular.ttf" "Test Mono"; role ui "Test Mono" fonts/test UFL-1.0; brand fonts
check "a UFL-1.0 font passes" code 0

fresh; role ui "Test System" null null; brand fonts
check "a font the products do not ship needs no evidence" code 0
check "and is reported as not shipped" says "$T/out" "ui (Test System): not shipped"

fresh; mkdir -p "$ID/fonts/test"; printf 'Commercial font licence. One desktop seat.\n' >"$ID/fonts/test/LICENSE.txt"
font "$ID/fonts/test/Test-Regular.ttf" "Test Display"; role heading "Test Display" fonts/test LicenseRef-Commercial
brand fonts
check "a licence file the check does not know needs a person, and fails (5.2.3)" code 1
check "the failure names the role, the family and why" says "$T/out" "tokens.json: heading (Test Display): needs a person: the licence file is not one the check knows"
check "words like legal, allowed or permitted appear only in the closing sentence (5.2.8)" words_only_in_closing "$T/out"

fresh; ofl_font "Test Serif" 2; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "restricted embedding (fsType 2) needs a person" code 1
check "and the report suggests a qualified person (5.2.5)" says "$T/out" "qualified person"
fresh; ofl_font "Test Serif" 4; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "preview-and-print embedding (fsType 4) needs a person" code 1
fresh; ofl_font "Test Serif" 512; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "bitmap-only embedding (fsType bit 9) needs a person" code 1
fresh; ofl_font "Test Serif" 0 "Free for personal use only."; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "a font whose own licence text says personal use needs a person" code 1
check "and names the limit" says "$T/out" "personal use"
fresh; ofl_font "Test Serif" 0 "Licensed under the Example Font EULA." "https://example.org/eula"
role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "a font whose own licence text names another licence needs a person" code 1
fresh; ofl_font "Test Serif" 0 "This Font Software is licensed under the SIL Open Font License, Version 1.1." \
  "https://openfontlicense.org"
role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "a font whose own licence text names its OFL passes" code 0

fresh; ofl_font "Test Serif" 0 "Free for personal use only."; role heading "Test Serif" fonts/test OFL-1.1 "A. Founder"
brand fonts
check "a flagged font with a recorded reading passes (5.2.3)" code 0
check "and is reported as that person's reading, with the date (5.2.4)" \
  says "$T/out" "heading (Test Serif): read by A. Founder on 2026-10-27: this is their reading"
check "and not as a known open licence (5.2.6)" quiet_about "$T/out" "known open licence"

fresh; role heading "Test Serif" fonts/missing OFL-1.1; brand fonts
check "a font folder that does not exist is missing evidence, and fails (5.2.2)" code 1
check "and says so" says "$T/out" "heading (Test Serif): missing evidence"
fresh; mkdir -p "$ID/fonts/test"; printf '%s\n' "$OFL" >"$ID/fonts/test/OFL.txt"; role heading "Test Serif" fonts/test OFL-1.1
brand fonts
check "a folder with no font file is missing evidence" code 1
fresh; mkdir -p "$ID/fonts/test"; font "$ID/fonts/test/Test-Regular.ttf" "Test Serif"; role heading "Test Serif" fonts/test OFL-1.1
brand fonts
check "a folder with no licence file is missing evidence" code 1
fresh; ofl_font "Test Serif"; printf '%s\n' "$APACHE" >"$ID/fonts/test/LICENSE.txt"; role heading "Test Serif" fonts/test OFL-1.1
brand fonts
check "a folder with two licence files is missing evidence" code 1
fresh; ofl_font "Test Serif"; role heading "Test Serif" fonts/test Apache-2.0; brand fonts
check "a licence in tokens.json that differs from the licence file is missing evidence" code 1
fresh; ofl_font "Other Family"; role heading "Test Serif" fonts/test OFL-1.1; brand fonts
check "a font file of another family is missing evidence" code 1
check "and names both families" says_all "$T/out" "Other Family" "Test Serif"

fresh; ofl_font "Test Serif" 2; role heading "Test Serif" fonts/test OFL-1.1; brand check
check "check runs the font licence check too" code 1
fresh

# The generated files (spec §4.3) and the board's freshness (5.4.7, 5.4.8).
fresh; brand tokens
check "tokens: a fresh scaffold's generated files are up to date" code 0
palette "${GOOD[@]}"; brand tokens
check "a palette change makes tokens.css stale, and the check fails" code 1
check "and names the file" says "$T/out" "tokens.css: out of date with tokens.json"
brand tokens --write
check "--write writes the generated files" code 0
brand tokens
check "after --write they are up to date" code 0
CSS="$ID/tokens.css"
check "tokens.css holds the light values in :root" says "$CSS" "--color-bg: #FFFFFF;"
check "the dark values under prefers-color-scheme: dark" says "$CSS" "prefers-color-scheme: dark"
check "and under :root[data-theme=\"dark\"]" says "$CSS" ':root\[data-theme="dark"\]'
check "it says it is generated and must not be edited" says "$CSS" "Generated from tokens.json"
ofl_font "Test Serif"; role heading "Test Serif" fonts/test OFL-1.1; brand tokens --write
check "each role gets a font stack" says "$CSS" '--font-heading: "Test Serif", serif;'
check "and its two weights, lowered to the one weight shipped when the tokens set none" \
  says_all "$CSS" "--weight-heading: 400;" "--weight-heading-strong: 400;"
check "fonts.css has one @font-face for the shipped file, served as WOFF2" says "$ID/fonts.css" 'src: url("fonts/test/web/Test-Regular.woff2") format("woff2");'
check "with font-display: swap" says "$ID/fonts.css" "font-display: swap;"
sum1="$(sha256sum "$CSS" "$ID/fonts.css")"; brand tokens --write
check "a second --write gives byte-identical files" [ "$(sha256sum "$CSS" "$ID/fonts.css")" = "$sum1" ]
check "the pages build strictly with fonts.css" builds "$T/a"

# The foundations (design system tasks DS-T03; spec §5.5): the template holds every key, and tokens.css every variable.
fresh; brand tokens --write
check "the foundations: a fresh scaffold's generated files are up to date" code 0
# shellcheck disable=SC2329 # runs through check
has_keys() {
  python3 - "$TOKENS" <<'PY'
import json, sys
t = json.load(open(sys.argv[1]))
need = ["space", "radius", "elevation", "motion", "focus", "target", "breakpoints", "components", "accepted", "languages"]
missing = [k for k in need if k not in t]
roles = t["type"]["fonts"]
missing += [f"type.fonts.{r}" for r in ("wordmark", "display", "heading", "body", "ui") if r not in roles]
missing += [f"type.scale.{k}" for k in ("base", "ratio", "minimum", "sizes", "lineHeight") if k not in t["type"]["scale"]]
sys.exit(1 if missing else 0)
PY
}
check "the template's tokens.json holds every key of the token contract" has_keys
check "tokens.css carries the spacing, radius and shadow variables" says_all "$CSS" \
  "--space-1: 8px;" "--space-7: 64px;" "--radius-sm:" "--radius-md:" "--radius-lg:" "--radius-button:" "--shadow-card:" "--shadow-overlay:"
check "the motion, focus, target and breakpoint variables" says_all "$CSS" \
  "--motion-distance: 16px;" "--motion-duration: 240ms;" "--motion-easing: cubic-bezier" \
  "--focus-color: var(--color-accent);" "--focus-width: 2px;" "--focus-offset: 2px;" "--target: 44px;" "--bp-1: 640px;" "--bp-3: 1280px;"
check "the type scale variables" says_all "$CSS" "--text-body: 16px;" "--text-small:" "--text-display:" "--leading-body: 1.5;" "--leading-heading:"
check "reduced motion removes the distance and the duration" says_all "$CSS" "prefers-reduced-motion: reduce" "--motion-duration: 0ms;"
python3 - "$TOKENS" <<'PY'
import json, sys
t = json.load(open(sys.argv[1])); t["space"] = [4, 8]; t["radius"]["lg"] = 12; json.dump(t, open(sys.argv[1], "w"), indent=2)
PY
brand tokens
check "a foundation change makes tokens.css stale" code 1
brand tokens --write
check "and --write brings only the changed values: two spacing steps, the new radius" says_all "$CSS" "--space-2: 8px;" "--radius-lg: 12px;"
check "a spacing step that is gone is not left behind" quiet_about "$CSS" "--space-3:"
for r in wordmark display heading body ui; do
  fresh; ofl_font "Test Serif"; role "$r" "Test Serif" fonts/test OFL-1.1; brand tokens --write
  check "the $r role gets a font stack" says "$CSS" "--font-$r: \"Test Serif\", serif;"
done
check "the identity page has the foundations, components, accepted exceptions and applications sections" \
  says_all "$T/a/docs/7-branding/identity/README.md" "^## Foundations" "^## Components" "^## Accepted exceptions" "^## Applications"
fresh
fresh; mkdir -p "$ID/fonts/test"; printf '%s\n' "$OFL" >"$ID/fonts/test/OFL.txt"
font "$ID/fonts/test/Test-Variable.ttf" "Test Serif" 0 "" "" variable; role heading "Test Serif" fonts/test OFL-1.1
brand tokens --write
check "a variable font gets its weight range in fonts.css" says "$ID/fonts.css" "font-weight: 100 900;"
fresh; ofl_font "Test Serif"; role heading "Test Serif" fonts/test OFL-1.1
(cd "$T/a" && python3 -S .ouroboric/checks/brand.py fonts) >"$T/out" 2>&1; echo $? >"$T/code"
check "without fontTools the font check stops with code 2" code 2
check "and says what it needs" says "$T/out" "needs fontTools"

fresh; git -C "$T/a" checkout -q -- docs/7-branding/identity 2>/dev/null; cp "$T/tokens.css.template" "$CSS"
cp "$T/fonts.css.template" "$ID/fonts.css"; brand board-fresh
check "board-fresh passes on the template's placeholder board (5.4.8)" code 0
python3 - "$T/a" <<'EOF'
import sys, os
sys.path.insert(0, os.path.join(sys.argv[1], ".ouroboric/checks"))
os.chdir(sys.argv[1])
import brand
open("docs/7-branding/identity/board.md", "a").write(f"\n<!-- inputs: {brand.board_inputs_hash()} -->\n")
EOF
brand board-fresh
check "a board whose recorded inputs match passes" code 0
palette "${GOOD[@]}"; brand board-fresh
check "a board fails when an input changed after it was made (5.4.7)" code 1
check "and says the board is stale" says "$T/out" "board.md: out of date with its inputs"
brand check
check "check runs the generated files and board checks too" says_all "$T/out" "tokens.css" "board.md"
cp "$T/board.md.template" "$ID/board.md"; cp "$T/tokens.css.template" "$CSS"; cp "$T/fonts.css.template" "$ID/fonts.css"
fresh

palette "${GOOD[@]}"; brand tokens --write; brand check
check "check runs the contrast check" says_all "$T/out" "^light" "^dark"
check "and passes on a good palette" code 0
cp "$T/tokens.template.json" "$TOKENS"
check "run.sh runs the brand checks as one step (5.5.1)" grep -q 'brand.py" check' "$T/a/.ouroboric/checks/run.sh"
check "the output names no tool" quiet_about "$T/out" "brand.py"

# The design system's checks (design system tasks DS-T04; spec §3.1).
ASCII="$(python3 -c 'print("".join(chr(c) for c in range(0x20, 0x7f)))')"
TYPO="$(python3 -c 'print("\u2019\u201c\u201d\u2013\u2014\u2026\u20ac", end="")')"
PT="áàâãçéêíóôõúüÁÀÂÃÇÉÊÍÓÔÕÚÜ"
# tweak PYTHON: edit tokens.json (t is the parsed file) with a Python statement.
tweak() {
  python3 - "$TOKENS" "$1" <<'PY'
import json, sys
t = json.load(open(sys.argv[1]))
exec(sys.argv[2])
json.dump(t, open(sys.argv[1], "w"), indent=2)
PY
}

# Foundations: presence, minimum body size, line height, focus indicator, touch target.
fresh; brand foundations
check "foundations: the template's starting set passes" code 0
for k in space radius elevation motion focus target breakpoints; do
  fresh; tweak "del t['$k']"; brand foundations
  check "a missing $k fails" code 1
  check "and names it" says "$T/out" "tokens.json: $k is missing"
done
fresh; tweak "del t['type']['scale']['sizes']"; brand foundations
check "a missing type scale part fails and is named" says "$T/out" "tokens.json: type.scale.sizes is missing"
fresh; tweak "t['type']['scale']['sizes']['body'] = 15"; brand foundations
check "a body size under 16 px fails" code 1
check "and says so" says "$T/out" "tokens.json: the body text is 15 px, under the minimum 16 px"
fresh; tweak "t['type']['scale']['minimum'] = 14"; brand foundations
check "a scale minimum under 16 px fails" code 1
fresh; tweak "t['type']['scale']['lineHeight']['body'] = 1.4"; brand foundations
check "a body line height under 1.5 fails" code 1
check "and says so" says "$T/out" "tokens.json: the body line height is 1.4, under the minimum 1.5"
fresh; tweak "t['focus']['width'] = 1"; brand foundations
check "a focus indicator under 2 px fails" code 1
check "and says so" says "$T/out" "tokens.json: the focus indicator is 1 px thick, under the minimum 2 px"
fresh; tweak "t['target'] = 20"; brand foundations
check "a touch target under 24 px fails" code 1
check "and says so" says "$T/out" "tokens.json: the touch target is 20 px, under the minimum 24 px"
palette "${GOOD[@]}"; brand foundations
check "the focus colour at 3:1 against bg and surface in both modes passes" code 0
palette "${GOOD[@]}" light.accent=#E8E8E8; brand foundations
check "a focus colour under 3:1 fails" code 1
check "and names the mode, the colour and the surface" says "$T/out" "tokens.json: light: the focus colour accent on bg is 1.2.:1, under the minimum 3:1"
palette "${GOOD[@]}" light.accent=#E8E8E8; tweak "t['focus']['role'] = 'text'"; brand foundations
check "the focus colour follows the role the tokens name" code 0

# Accepted exceptions: a kept failure is accepted, until its value changes.
fresh; tweak "t['target'] = 20; t['accepted'] = [{'check': 'target', 'value': '20', 'reason': 'Small icons on the dense toolbar.', 'by': 'Alex', 'date': '2026-10-28'}]"; brand foundations
check "an accepted exception turns the failure into accepted: exit 0" code 0
check "and reports it with her reason" says_all "$T/out" "target" "accepted" "Small icons on the dense toolbar."
tweak "t['target'] = 16"; brand foundations
check "when the value changes the exception is stale and the check fails again" code 1
check "and says stale" says "$T/out" "stale"
fresh; tweak "t['accepted'] = [{'check': 'target', 'value': '20', 'by': 'Alex', 'date': '2026-10-28'}]"; brand accepted
check "an exception without a reason fails" code 1
check "and names the entry and the field" says "$T/out" "tokens.json: accepted\[0\]: reason is missing"
fresh; tweak "t['accepted'] = [{'check': 'target', 'value': '20', 'reason': 'Kept.', 'by': 'Alex', 'date': '2026-10-28'}]"; brand check
check "an exception for a check that now passes is reported as no longer needed, not as a failure" says "$T/out" "no longer needed"
fresh; palette "${GOOD[@]}" light.muted=#999999
tweak "t['accepted'] = [{'check': 'contrast:light:muted/' + b, 'value': '#999999/' + v, 'reason': 'Decorative captions only.', 'by': 'Alex', 'date': '2026-10-28'} for b, v in (('bg', '#FFFFFF'), ('surface', '#F5F5F5'))]"; brand contrast
check "a contrast failure can be accepted too" code 0
check "and is reported as accepted" says "$T/out" "light: muted on bg is 2.84:1.*accepted"

# The type checks read the font files: glyph coverage, the weights, the body face's italic.
fresh; brand type
check "type: no font chosen passes" code 0
fresh; tweak "t['languages'] = ['pt']"; ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; brand type
check "a font that lacks the clients' glyphs fails" code 1
check "and names the role, the language and some of the missing characters" \
  says "$T/out" "tokens.json: body (Test Sans): lacks 1[0-9][0-9] characters of pt, such as"
FONT_CHARS="$ASCII$TYPO$PT" ofl_font "Test Sans"; brand type
check "a font that covers them passes the glyph check" quiet_about "$T/out" "lacks"
fresh; tweak "t['languages'] = ['xx']"; FONT_CHARS="$ASCII" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; brand type
check "a language the check has no characters for fails and is named" says "$T/out" "tokens.json: the language xx has no list of characters"
fresh; tweak "t['languages'] = ['pt']"; ofl_font "Test Sans"; role heading "Test Sans" fonts/test OFL-1.1
tweak "t['accepted'] = [{'check': 'type:heading:glyphs', 'value': 'Test Sans', 'reason': 'Portuguese is added later.', 'by': 'Alex', 'date': '2026-10-28'}]"; brand type
check "a glyph failure can be accepted by the family" code 0
check "and is reported as accepted with her reason" says_all "$T/out" "heading (Test Sans): lacks" "accepted: Portuguese is added later."

LATIN="$ASCII$TYPO$PT"
fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; tweak "t['languages'] = ['pt']; t['type']['fonts']['body']['weights'] = [400, 700]"; brand type
check "a weight the files do not have fails" code 1
check "and says which, and what the files have" says "$T/out" "tokens.json: body (Test Sans): weight 700 is not in the font files (they have 400)"
FONT_CHARS="$LATIN" ofl_font "Test Sans"; FONT_CHARS="$LATIN" font "$ID/fonts/test/Test-Variable.ttf" "Test Sans" 0 "" "" variable
tweak "t['type']['fonts']['body']['weights'] = [400, 700]"; brand type
check "a weight inside a variable font's axis passes the weight check" quiet_about "$T/out" "weight 700"
tweak "t['type']['fonts']['body']['weights'] = [950]"; brand type
check "a weight outside the axis fails" says "$T/out" "weight 950 is not in the font files (they have 100 to 900)"

fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1
tweak "t['languages'] = ['pt']; t['type']['fonts']['body']['weight'] = 500; t['type']['fonts']['body']['strong'] = 700"; brand type
check "a regular weight the files do not have fails" says "$T/out" "tokens.json: body (Test Sans): the regular weight 500 is not in the font files (they have 400)"
check "and so does a strong weight" says "$T/out" "tokens.json: body (Test Sans): the strong weight 700 is not in the font files (they have 400)"
tweak "t['languages'] = ['pt']; t['type']['fonts']['body']['weight'] = 400; t['type']['fonts']['body']['strong'] = 400"; brand type
check "a face with one weight passes when both weights are that one" quiet_about "$T/out" "the regular weight"
fresh; ofl_font "Test Serif"; role heading "Test Serif" fonts/test OFL-1.1
tweak "t['type']['fonts']['heading']['weights'] = [400, 700]"; brand tokens --write
check "unset weights read as 400 and 600, lowered to the nearest weight shipped" \
  says_all "$CSS" "--weight-heading: 400;" "--weight-heading-strong: 700;"
tweak "t['type']['fonts']['heading']['weights'] = [400, 500, 700]; t['type']['fonts']['heading']['weight'] = 500; t['type']['fonts']['heading']['strong'] = 700"; brand tokens --write
check "set weights are written as they are" says_all "$CSS" "--weight-heading: 500;" "--weight-heading-strong: 700;"

fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; tweak "t['languages'] = ['pt']"; brand type
check "a body face without an italic fails" code 1
check "and says so" says "$T/out" "tokens.json: body (Test Sans) has no italic"
FONT_CHARS="$LATIN" FONT_ITALIC=1 font "$ID/fonts/test/Test-Italic.ttf" "Test Sans"; brand type
check "an italic file beside it passes the italic check" quiet_about "$T/out" "no italic"
fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; tweak "t['languages'] = ['pt']"
FONT_CHARS="$LATIN" FONT_ITAL_AXIS=1 font "$ID/fonts/test/Test-Regular.ttf" "Test Sans" 0 "" "" variable; brand type
check "an italic axis passes the italic check" quiet_about "$T/out" "no italic"
fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1; tweak "t['languages'] = ['pt']"
tweak "t['type']['fonts']['body']['italic'] = True"; brand type
check "tokens.json claiming an italic does not make one" says "$T/out" "has no italic"
tweak "t['accepted'] = [{'check': 'type:body:italic', 'value': 'Test Sans', 'reason': 'No italics; emphasis in bold.', 'by': 'Alex', 'date': '2026-10-28'}]"; brand type
check "the founder may keep a body face without an italic" code 0
check "and it is reported as accepted with her reason" says_all "$T/out" "body (Test Sans) has no italic" "accepted" "emphasis in bold"
tweak "t['type']['fonts']['body']['family'] = 'Test Sans'; t['accepted'][0]['value'] = 'Other Sans'"; brand type
check "an exception for another family does not cover it: stale" says "$T/out" "stale"
fresh; FONT_CHARS="$LATIN" ofl_font "Test Sans"; role heading "Test Sans" fonts/test OFL-1.1; tweak "t['languages'] = ['pt']"; brand type
check "only the body face needs an italic" code 0
brand check
check "check runs the foundations and the type checks too" says_all "$T/out" "foundations" "Test Sans"
fresh

# Web fonts (design system tasks DS-T08; spec §4.3): WOFF2, subset to the clients' languages; the original stays.
# woff_has FILE CHARS... : every character is in the font file's cmap.
# shellcheck disable=SC2329 # runs through check and lacks
woff_has() {
  python3 - "$@" <<'PY'
import sys
from fontTools.ttLib import TTFont
cmap = TTFont(sys.argv[1]).getBestCmap()
sys.exit(0 if all(ord(c) in cmap for c in "".join(sys.argv[2:])) else 1)
PY
}
# shellcheck disable=SC2329
lacks() { ! woff_has "$@"; }
# shellcheck disable=SC2329
is_woff2() { [ "$(head -c 4 "$1")" = "wOF2" ]; }
CYR="$(python3 -c 'print("Жд", end="")')"
fresh; tweak "t['languages'] = ['pt']"; FONT_CHARS="$ASCII$TYPO$PT$CYR" ofl_font "Test Sans"; role body "Test Sans" fonts/test OFL-1.1
sum_ttf="$(sha256sum "$ID/fonts/test/Test-Regular.ttf")"; brand tokens --write
WEBF="$ID/fonts/test/web/Test-Regular.woff2"
check "tokens --write converts the shipped font to a WOFF2 file" is_woff2 "$WEBF"
check "the WOFF2 holds every glyph of the clients' language" woff_has "$WEBF" "$ASCII" "$TYPO" "$PT"
check "and is subset to those languages: a Cyrillic glyph is left out" lacks "$WEBF" "$CYR"
check "the original font file stays, unchanged, as the licence's evidence" [ "$(sha256sum "$ID/fonts/test/Test-Regular.ttf")" = "$sum_ttf" ]
check "the subset keeps the font's name table, with its licence text" \
  python3 -c "import sys; from fontTools.ttLib import TTFont; n = TTFont(sys.argv[1])['name']; sys.exit(0 if n.getDebugName(1) == 'Test Sans' else 1)" "$WEBF"
brand tokens
check "after --write the generated files, WOFF2 included, are up to date" code 0
printf 'not a font' >"$WEBF"; brand tokens
check "a WOFF2 that does not hold the font's subset makes the check fail" code 1
check "and names the file" says "$T/out" "Test-Regular.woff2: out of date with the font and tokens.json"
brand tokens --write; brand tokens
check "--write makes it again" code 0
check "the fonts and type checks read the original, not the WOFF2" quiet_about "$T/out" "woff2"
brand fonts
check "the font licence check ignores the web folder" code 0
tweak "t['languages'] = ['pt', 'xx']"; brand tokens --write
check "a language with no list of characters keeps every glyph: the font is converted, not subset" woff_has "$WEBF" "$CYR"
FONT_CHARS="$ASCII" font "$ID/fonts/test/Test-Variable.ttf" "Test Sans" 0 "" "" variable; tweak "t['languages'] = ['en']"; brand tokens --write
check "a variable font keeps its weight axis in the WOFF2" \
  python3 -c "import sys; from fontTools.ttLib import TTFont; f = TTFont(sys.argv[1]); sys.exit(0 if 'fvar' in f else 1)" "$ID/fonts/test/web/Test-Variable.woff2"
check "and fonts.css gives its range" says "$ID/fonts.css" 'font-weight: 100 900;'
fresh

# The component recipes' rules (design system tasks DS-T11): what a variant needs from the palette.
fresh; palette "${GOOD[@]}"; brand components
check "components: the template's variants on a good palette pass" code 0
fresh; palette "${GOOD[@]}"; tweak "t['components']['button'] = 'soft'"; brand components
check "a soft button whose accent text reads on its tint passes" code 0
palette "${GOOD[@]}" light.accent-text=#6FA0E8; tweak "t['components']['button'] = 'soft'"; brand components
check "a soft button whose accent text does not read on its tint fails" code 1
check "and says so, with the mode and the ratio" says "$T/out" "tokens.json: light: the soft button's accent text on its tint is [0-9.]*:1, under the minimum 4.5:1"
palette "${GOOD[@]}" light.accent-text=#6FA0E8; tweak "t['components']['button'] = 'outlined'"; brand components
check "an outlined button's accent text must read on the background" says "$T/out" "light: the outlined button's accent text on the background is"
palette "${GOOD[@]}" light.accent-text=#6FA0E8; brand components
check "a filled button asks nothing more: its pair is already in the palette check" code 0
palette "${GOOD[@]}" light.accent-text=#1B2A4A; tweak "t['components']['link'] = 'colour'"; brand components
check "a link with no underline must differ from the text by 3:1 (WCAG 1.4.1)" says "$T/out" "light: a link without an underline differs from the text by"
tweak "t['components']['link'] = 'underlined'"; brand components
check "an underlined link needs no such difference" code 0
palette "${GOOD[@]}" light.crit=#E05050; tweak "t['components']['message'] = 'tint'"; brand components
check "a tinted message's colour must read on its tint" says "$T/out" "light: the crit message on its tint is"
tweak "t['components']['message'] = 'bar'"; brand components
check "a message with a side bar has no tint to check" code 0
palette "${GOOD[@]}" light.accent-text=#1B2A4A; tweak "t['components']['link'] = 'colour'; t['accepted'] = [{'check': 'components:link:light', 'value': '#1B2A4A/#1A1A1A', 'reason': 'Underline added by hand.', 'by': 'Alex', 'date': '2026-10-28'}, {'check': 'components:link:dark', 'value': '#6EA8FE/#EDEDED', 'reason': 'Underline added by hand.', 'by': 'Alex', 'date': '2026-10-28'}]"; brand components
check "a failing component rule can be accepted, with her reason" code 0
check "and is reported as accepted" says "$T/out" "accepted: Underline added by hand."
fresh; brand components
check "with no palette set there is nothing to check" code 0
fresh; palette "${GOOD[@]}"; brand check
check "check runs the component rules too" says "$T/out" "components"
fresh

exit "$fail"
