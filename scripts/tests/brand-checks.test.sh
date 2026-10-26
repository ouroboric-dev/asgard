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
# font FILE FAMILY [FSTYPE] [DESCRIPTION] [URL]: a minimal TrueType font with those name and OS/2 values.
font() {
  python3 - "$@" <<'EOF'
import sys
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen
path, family = sys.argv[1], sys.argv[2]
fstype = int(sys.argv[3]) if len(sys.argv) > 3 and sys.argv[3] else 0
desc = sys.argv[4] if len(sys.argv) > 4 and sys.argv[4] else None
url = sys.argv[5] if len(sys.argv) > 5 and sys.argv[5] else None
fb = FontBuilder(1000, isTTF=True)
fb.setupGlyphOrder([".notdef", "A"])
fb.setupCharacterMap({ord("A"): "A"})
pen = TTGlyphPen(None)
pen.moveTo((0, 0)); pen.lineTo((500, 700)); pen.lineTo((1000, 0)); pen.closePath()
glyph = pen.glyph()
fb.setupGlyf({".notdef": glyph, "A": glyph})
fb.setupHorizontalMetrics({".notdef": (1000, 0), "A": (1000, 0)})
fb.setupHorizontalHeader(ascent=800, descent=-200)
names = {"familyName": family, "styleName": "Regular"}
if desc:
    names["licenseDescription"] = desc
if url:
    names["licenseInfoURL"] = url
fb.setupNameTable(names)
fb.setupOS2(fsType=fstype)
fb.setupPost()
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
check "fonts.css has one @font-face for the shipped file" says "$ID/fonts.css" 'src: url("fonts/test/Test-Regular.ttf") format("truetype");'
check "with font-display: swap" says "$ID/fonts.css" "font-display: swap;"
sum1="$(sha256sum "$CSS" "$ID/fonts.css")"; brand tokens --write
check "a second --write gives byte-identical files" [ "$(sha256sum "$CSS" "$ID/fonts.css")" = "$sum1" ]
check "the pages build strictly with fonts.css" builds "$T/a"

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

exit "$fail"
