#!/usr/bin/env bash
# Tests for brand.sh: setup, logo processing and the brand board.   scripts/tests/brand.test.sh
# (needs python3 3.10 or later, curl, the network for the first setup; mkdocs with the Material theme)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
BRAND="$HERE/../brand.sh"
T="$(mktemp -d)"
trap 'rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
says() { grep -q -- "$2" "$1"; }
# shellcheck disable=SC2329
lacks_text() { ! grep -q -- "$2" "$1"; }

"$NEW" --name "Example Studio" --date 2026-10-27 "$T/a" >/dev/null 2>&1
git -C "$T/a" init -q -b main
git -C "$T/a" -c user.name=t -c user.email=t@example.com add -A
git -C "$T/a" -c user.name=t -c user.email=t@example.com commit -q -m scaffold

# Setup (spec §3.2). The shared cache keeps the first run's download for the next runs.
"$BRAND" setup >"$T/setup.out" 2>&1
check "setup builds the tools' environment" [ $? -eq 0 ]
"$BRAND" setup >"$T/setup2.out" 2>&1
check "a second setup with the same pins does nothing" says "$T/setup2.out" "up to date"
XDG_CACHE_HOME="$T/empty" "$BRAND" logo "$T/a" >"$T/nosetup.out" 2>&1
check "logo refuses to run without the environment, with code 2" [ $? -eq 2 ]
check "and names setup" says "$T/nosetup.out" "brand.sh setup"
XDG_CACHE_HOME="$T/empty" "$BRAND" board "$T/a" >/dev/null 2>&1
check "board refuses to run without the environment" [ $? -eq 2 ]

# A resvg binary whose SHA-256 differs from resvg.lock is refused.
mkdir -p "$T/copy/brand"
cp "$BRAND" "$T/copy/"
cp "$HERE/../brand/"* "$T/copy/brand/"
sed -i 's/^\(linux-x86_64 [^ ]*\) [0-9a-f]*$/\1 0000000000000000000000000000000000000000000000000000000000000000/' \
  "$T/copy/brand/resvg.lock"
XDG_CACHE_HOME="$T/bad" "$T/copy/brand.sh" setup >"$T/bad.out" 2>&1
check "setup refuses a resvg binary whose SHA-256 differs" [ $? -ne 0 ]
check "and says why" says "$T/bad.out" "SHA-256"
check "and leaves no environment behind" [ -z "$(find "$T/bad" -name .complete 2>/dev/null)" ]

"$BRAND" nonsense >/dev/null 2>&1
check "it refuses an unknown command" [ $? -eq 2 ]

# Logo processing (spec §5.3, with the change of 2026-10-27: the detail limit counts shapes and holes).
# Each case works in its own fresh copy of the scaffold; nothing is reset between cases.
PY="$(sed -n 's/.*(\(.*\))$/\1/p' "$T/setup2.out")/venv/bin/python"
FX="$HERE/brand_fixtures.py"
PLAYWRIGHT_BROWSERS_PATH="$(dirname "$(dirname "$(dirname "$PY")")")/browsers"; export PLAYWRIGHT_BROWSERS_PATH
fx() { "$PY" -I "$FX" "$@"; }
# use NAME: a fresh copy of the scaffold at $T/NAME; sets C, L (its logo folder) and SRC (her PNGs).
use() { C="$T/$1"; cp -R "$T/a" "$C"; L="$C/docs/7-branding/identity/logo"; SRC="$L/source"; mkdir -p "$SRC"; }
logo() { "$BRAND" logo "$C" >"$C.out" 2>&1; echo $? >"$C.code"; }
# shellcheck disable=SC2329 # these run through check
lcode() { [ "$(cat "$C.code")" = "$1" ]; }
# shellcheck disable=SC2329
trace() { fx trace "$L/trace.json" "$1"; }
# shellcheck disable=SC2329
svg_clean() { local f; for f in "$@"; do
  grep -q 'viewBox=' "$f" || return 1
  ! grep -q '<!--' "$f" || return 1
  ! grep -o '<[a-zA-Z][a-zA-Z]*' "$f" | sort -u | grep -qvxE '<(svg|path|style)' || return 1
done; }
# shellcheck disable=SC2329
only_logo_changed() { ! git -C "$1" status --porcelain | grep -qv 'docs/7-branding/identity/logo/'; }
# shellcheck disable=SC2329
only_choices_changed() { ! git -C "$1" status --porcelain | grep -qv 'identity/choices/'; }
# shellcheck disable=SC2329
names_pass() { (cd "$1" && .ouroboric/checks/names-check.sh); }
logo_sums() { (cd "$L" && find . -type f ! -path './source/*' -exec sha256sum {} + | sort); }

# Refusals (5.3.1).
use none; logo
check "logo refuses a company with no logo PNG, with code 2" lcode 2
check "and says where to put it" says "$C.out" "logo/source/logo.png"
use notpng; printf 'not a png' >"$SRC/logo.png"; logo
check "it refuses a file that is not a PNG, by its first bytes" lcode 2
use small; fx draw small "$SRC/logo.png"; logo
check "it refuses a PNG under 512 pixels on its short side" lcode 2
use huge; fx draw huge "$SRC/logo.png"; logo
check "it refuses a PNG over 8192 pixels on a side" lcode 2
use opaque; fx draw opaque "$SRC/logo.png"; logo
check "it refuses a PNG with no transparent background" lcode 2
check "and says what to bring" says "$C.out" "transparent background"
use notsquare; fx draw mark "$SRC/logo.png"; fx draw not-square "$SRC/mark.png"; logo
check "it refuses a mark that is not roughly square" lcode 2

# The trace and its faithfulness (5.3.2 to 5.3.5).
use faithful; fx palette "$C/docs/7-branding/identity/tokens.json"
git -C "$C" -c user.name=t -c user.email=t@example.com commit -qam palette
fx draw mark "$SRC/logo.png"; logo
check "a two-colour mark is processed" lcode 0
check "trace.json says it is faithful" trace 't["faithful"] is True and t["gaps"] == []'
check "it records the tracer, its version and its fixed settings (5.3.2)" \
  trace 't["tracer"]["name"] == "vtracer" and t["tracer"]["version"] == "0.6.15" and t["tracer"]["params"]["hierarchical"] == "stacked"'
check "it records the shape, detail and colour results (5.3.3)" \
  trace '{"mismatch", "shapes", "holes", "colour_delta"} <= t["modes"]["light"].keys()'
check "the SVGs hold only svg and path, a viewBox and no comment (5.3.11, 5.3.12)" svg_clean "$L/logo.svg" "$L/logo-dark.svg"
check "a traced colour maps to the nearest token" trace 'any(c["token"] == "text" for c in t["modes"]["light"]["colours"])'
check "with one PNG, the dark version is derived (5.3.6)" trace 't["modes"]["dark"]["from"] == "derived"'
check "the dark version uses the tokens' dark values" grep -qi 'fill="#EDEDED"' "$L/logo-dark.svg"
check "a colour no token holds is proposed as a brand token (5.3.9)" \
  trace 'len(t["proposed_brand_tokens"]) == 1 and t["proposed_brand_tokens"][0]["light"].upper() == "#C2185B"'
check "the proposal's dark value reaches 3:1 on the dark background" fx dark3 "$L/trace.json"
check "logo writes nothing outside logo/, tokens.json included (5.3.10, 5.3.16)" only_logo_changed "$C"
check "the company passes the names check after logo (5.4.6)" names_pass "$C"
sum1="$(logo_sums)"; logo
check "a second run writes byte-identical files (5.3.15)" [ "$(logo_sums)" = "$sum1" ]
fx accept "$C/docs/7-branding/identity/tokens.json" "$L/trace.json"; logo
check "once the brand token is in the palette, the colour maps to it" \
  trace 't["proposed_brand_tokens"] == [] and any(c["token"] == "brand-1" for c in t["modes"]["light"]["colours"])'

use details; fx draw small-details "$SRC/logo.png"; logo
check "a 2 by 2 dot and a 2 by 2 hole stay faithful" trace 't["faithful"] is True'
use ring; fx draw ring "$SRC/logo.png"; logo
check "a thin ring that the trace breaks apart is a gap (5.3.4)" trace 't["faithful"] is False and len(t["gaps"]) > 0'
check "and still exits 0: a gap is not a failure" lcode 0
check "the gap image shows where the trace differs" [ -f "$L/trace-light.png" ]
check "the gap is printed for the agent" says "$C.out" "gap"
use gradient; fx draw gradient "$SRC/logo.png"; logo
check "a PNG with many colours is a gap (gradients or a photo)" trace 'any("colours" in g["what"] for g in t["gaps"])'
use two; fx palette "$C/docs/7-branding/identity/tokens.json"; fx draw mark "$SRC/logo.png"
fx draw mark-dark "$SRC/logo-dark.png"; logo
check "with two PNGs, no mode is derived (5.3.7)" trace 't["modes"]["dark"]["from"] == "given"'

# Exports (5.3.8, 5.3.13, 5.3.14).
use wide; fx palette "$C/docs/7-branding/identity/tokens.json"; fx draw wide "$SRC/logo.png"; logo
check "a wide logo with no mark gives a favicon gap" trace 'any("favicon" in g["what"] for g in t["gaps"])'
use withmark; fx palette "$C/docs/7-branding/identity/tokens.json"; fx draw wide "$SRC/logo.png"
fx draw square "$SRC/mark.png"; logo
check "with a mark, the favicon comes from it and the gap goes (5.3.8)" trace 'not any("favicon" in g["what"] for g in t["gaps"])'
check "the mark is traced for both modes" test -f "$L/mark-dark.svg"
check "favicon.svg switches to the dark colours" says "$L/favicon.svg" "prefers-color-scheme: dark"
check "favicon.svg holds only svg, path and style" svg_clean "$L/favicon.svg"
check "favicon.ico holds 16, 32 and 48 pixels (5.3.13)" fx ico "$L/favicon.ico"
check "the icons are opaque, with the mark inside the safe-zone circle (5.3.14)" fx icons "$L"

# The brand board (spec §5.4, with the founder's answers of 2026-10-27: plain Markdown and generated images).
ID_REL=docs/7-branding/identity
board() { "$BRAND" board "$C" >"$C.board.out" 2>&1; echo $? >"$C.board.code"; }
# shellcheck disable=SC2329 # these run through check
bcode() { [ "$(cat "$C.board.code")" = "$1" ]; }
# shellcheck disable=SC2329
board_fresh() { "$BRAND" board --check "$C" >/dev/null 2>&1; }
# shellcheck disable=SC2329
company_fresh() { (cd "$C" && python3 .ouroboric/checks/brand.py board-fresh >/dev/null); }
# shellcheck disable=SC2329
board_stale() { ! board_fresh; }
# shellcheck disable=SC2329
company_stale() { ! company_fresh; }
# shellcheck disable=SC2329
says_all() { local f="$1" p; shift; for p in "$@"; do grep -q -- "$p" "$f" || return 1; done; }
# shellcheck disable=SC2329
in_order() { local f="$1" last=0 n; shift; for h in "$@"; do
  n="$(grep -n -m1 -- "^## $h" "$f" | cut -d: -f1)"; [ -n "$n" ] && [ "$n" -gt "$last" ] || return 1; last="$n"; done; }
# shellcheck disable=SC2329
no_html() { ! grep -vE '^<!--.*-->$' "$1" | grep -qE '<[a-zA-Z/]'; }
# shellcheck disable=SC2329
local_only() { ! grep -qE 'https?://|\]\(/|<script' "$1"; }
# shellcheck disable=SC2329
board_images_clean() { local f; for f in "$1"/*; do
  case "$f" in
    *.png) ;;
    *.svg) ! grep -o '<[a-zA-Z][a-zA-Z]*' "$f" | sort -u | grep -qvxE '<(svg|path|rect|g|text)' || return 1 ;;
    *) return 1 ;;
  esac; done; }
# shellcheck disable=SC2329
builds() { (cd "$1" && mkdocs build --strict --quiet --config-file .ouroboric/mkdocs.yml); }
# shellcheck disable=SC2329
docs_pass() { (cd "$1" && python3 .ouroboric/checks/docs-check.py); }
board_sums() { (cd "$C/$ID_REL" && sha256sum board.md board/* applications/*); }
# shellcheck disable=SC2329
no_pycache() { [ -z "$(find "$1" -name __pycache__)" ]; }
# shellcheck disable=SC2329
no_message_swatch() { ! grep -qE '>(ok|warn|crit)</text>' "$1"; }
# shellcheck disable=SC2329
no_message_pairs() { ! grep -qE '^\| (ok|warn|crit) on ' "$1"; }
# shellcheck disable=SC2329
one_row_per_token() {   # the logo's colour table: one row for each mode and token
  [ -z "$(grep -E '^\| (light|dark) \|' "$1" | awk -F'|' '{gsub(/ /, "", $2); gsub(/ /, "", $4); print $2 "/" $4}' | sort | uniq -d)" ]; }

use bempty; board
check "board runs on a company with nothing chosen yet" bcode 0
check "and writes the board with its five parts in order (5.4.1)" \
  in_order "$C/$ID_REL/board.md" Palette Type Logo "Sample images" "Open items"
check "board --check passes right after board" board_fresh

use bfull; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx font "$TK" "$C/$ID_REL/fonts/test" "Test Serif" ttf
fx draw mark "$SRC/logo.png"; fx draw square "$SRC/mark.png"
mkdir -p "$C/docs/7-branding/imagery"
fx photo "$C/docs/7-branding/imagery/portrait.png" 1200; fx photo "$C/docs/7-branding/imagery/detail.png" 800
fx record "$C/docs/7-branding/imagery.md" portrait.png yes "confirmed by the founder, 2026-10-27"
(cd "$C" && "$PY" -I .ouroboric/checks/brand.py tokens --write >/dev/null)
logo; board
B="$C/$ID_REL/board.md"
check "a full board is written" bcode 0
check "its five parts are in order (5.4.1)" in_order "$B" Palette Type Logo "Sample images" "Open items"
check "it shows the light and the dark palette at the same time (5.4.2)" \
  says_all "$B" "board/palette-light.svg" "board/palette-dark.svg"
check "each contrast result is in words (5.4.3)" says "$B" "passes"
check "the board holds no HTML element (5.4.9)" no_html "$B"
check "no script, no external URL and no absolute link (5.4.4)" local_only "$B"
check "its images are SVGs of the allowed elements, or PNGs (5.4.10)" board_images_clean "$C/$ID_REL/board"
check "the heading font has a type specimen, with the text drawn" fx ink "$C/$ID_REL/board/type-heading.png"
check "the logo is shown on each background" test -f "$C/$ID_REL/board/logo-on-dark.svg"
check "a sample image with no record is an open item" says "$B" "detail.png"
check "a proposed brand token is an open item" says "$B" "#C2185B"
check "the pages build strictly after board (5.4.5)" builds "$C"
check "the docs check passes after board" docs_pass "$C"
check "the names check passes after board (5.4.6)" names_pass "$C"
sums="$(board_sums)"; board
check "a second board writes byte-identical files" [ "$(board_sums)" = "$sums" ]
check "board --check passes while nothing changed" board_fresh
fx record "$C/docs/7-branding/imagery.md" detail.png no ""
check "board --check fails when an input changed (5.4.7)" board_stale
check "and so does the company's freshness check" company_stale
check "the board leaves no Python cache in the company" no_pycache "$C"
check "the palette panels show the brand colours, not the message colours" no_message_swatch "$C/$ID_REL/board/palette-light.svg"
check "the contrast tables leave the message colours out" no_message_pairs "$B"
check "and the board says where the message colours are" says "$B" "message colours"

use bshades; fx palette "$C/$ID_REL/tokens.json"; fx trace-shades "$L/trace.json"; board
check "a logo whose soft edges trace as several shades of one token gets one row per mode and token" \
  one_row_per_token "$C/$ID_REL/board.md"

use bwoff; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx font "$TK" "$C/$ID_REL/fonts/test" "Test Serif" woff2
board
check "a WOFF2 font is converted for its specimen (the change of 2026-10-27)" fx ink "$C/$ID_REL/board/type-heading.png"

use bbare; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx font "$TK" "$C/$ID_REL/fonts/test" "Test Serif" bare
board
check "a font the renderer cannot load gets no blank specimen" test ! -f "$C/$ID_REL/board/type-heading.png"
check "it is shown in words and listed as an open item" says "$C/$ID_REL/board.md" "could not be drawn"

use bmany; mkdir -p "$C/docs/7-branding/imagery"
for i in 1 2 3 4 5 6 7; do fx photo "$C/docs/7-branding/imagery/p$i.png" 600; done; board
check "board refuses more than six sample images (5.4.11)" bcode 2
use bbig; mkdir -p "$C/docs/7-branding/imagery"; fx photo "$C/docs/7-branding/imagery/big.png" 2000; board
check "board refuses a sample image over 1600 pixels (5.4.11)" bcode 2

# The design system on the board (design system tasks DS-T09; spec §5.4).
use bsystem; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx font "$TK" "$C/$ID_REL/fonts/test" "Test Serif" ttf
fx message-colour "$TK" "#FF00FF"
fx accepted "$TK" "type:body:italic" "Test Serif" "No italics; emphasis in bold."
fx accepted "$TK" "target" "20" "Small icons on the dense toolbar."
fx draw mark "$SRC/logo.png"; fx draw square "$SRC/mark.png"
(cd "$C" && "$PY" -I .ouroboric/checks/brand.py tokens --write >/dev/null)
logo; board
B="$C/$ID_REL/board.md"; BD="$C/$ID_REL/board"; AP="$C/$ID_REL/applications"
check "the board with the design system is written" bcode 0
check "its parts stay in order, the new ones before the open items" \
  in_order "$B" Palette Type Logo "Sample images" Foundations Components Applications "Accepted exceptions" "Open items"
for r in wordmark display heading body ui; do
  check "the $r role has a specimen drawn from its font" fx ink "$BD/type-$r.png"
done
check "each role is shown at its scale size" says_all "$B" "Set at 39 px" "Set at 25 px" "Set at 16 px" "Set at 14 px"
check "the foundations are listed with their values" \
  says_all "$B" "Spacing" "8 px" "64 px" "Corner radius" "Elevation" "Motion" "240 ms" "Focus" "Touch target" "44 px" "Breakpoints" "640 px"
check "with pictures of the spacing, the corners and the depth" \
  test -f "$BD/foundations-space.svg" -a -f "$BD/foundations-radius.svg" -a -f "$BD/foundations-elevation.png"
for c in button link field card message navigation image icon; do
  check "the component sheet lists the $c and its recipe" says "$B" "^| $c | "
done
check "the chosen variants are named" says_all "$B" "| button | filled |" "| card | bordered |" "| message | tint |" "| navigation | left |"
check "the component sheet is drawn in light" fx ink "$BD/components-light.png"
check "and in dark" fx ink "$BD/components-dark.png"
check "and leaves the message colours out" fx lacks-colour "$BD/components-light.png" "#FF00FF"
check "also in dark" fx lacks-colour "$BD/components-dark.png" "#FF00FF"
check "logo usage: the clear space is stated" says_all "$B" "Clear space" "width of the mark"
check "and drawn" test -f "$BD/logo-clear-space.svg"
check "the minimum sizes are stated" says "$B" "Minimum size"
check "and drawn for the logo and the mark" test -f "$BD/logo-minimum-light.png"
for m in stretched rotated recoloured low-contrast; do
  check "the misuse '$m' has its own tile" test -f "$BD/misuse-$m.svg"
done
check "the misuses are listed in words" says_all "$B" "Do not stretch" "Do not rotate" "Do not recolour" "Do not place"
check "the board images stay SVGs of the allowed elements, or PNGs" board_images_clean "$BD"
check "the kept exceptions are listed with their reasons" says_all "$B" "No italics; emphasis in bold." "Small icons on the dense toolbar." "type:body:italic"
check "the profile picture is square, 1080 pixels" fx size "$AP/profile-picture.png" 1080x1080
check "the link preview is 1200 by 630" fx size "$AP/link-preview.png" 1200x630
check "the email signature has a double-resolution logo" test -f "$AP/email-signature.html" -a -f "$AP/signature-logo@2x.png"
check "and the HTML shows it at half its width" fx half-width "$AP/email-signature.html" "$AP/signature-logo@2x.png"
check "the board shows the applications" says_all "$B" "applications/profile-picture.png" "applications/link-preview.png" "email-signature.html"
check "the board still holds no HTML" no_html "$B"
check "the pages build strictly with the applications" builds "$C"
check "the docs check passes" docs_pass "$C"
check "the names check passes" names_pass "$C"
sums="$(board_sums)"; board
check "a second board writes byte-identical files, applications included" [ "$(board_sums)" = "$sums" ]

use bnone; board
check "a board with no logo and no exceptions says so, and still writes" bcode 0
check "no exception is stated" says "$C/$ID_REL/board.md" "No exception is kept"

# The typography tool (design system tasks DS-T05): candidate faces fetched from the library, their facts read from the
# files. The library is a folder here, reached through file://; nothing is fetched from the network.
use fonts1
LIB="$T/library"; DL="$T/downloads"; FACTS="$C/docs/7-branding/identity/choices/fonts-facts.json"
PTX="e1,e0,e2,e3,e7,e9,ea,ed,f3,f4,f5,fa,fc,c1,c0,c2,c3,c7,c9,ca,cd,d3,d4,d5,da,dc"
fx face "$LIB/plainsans" "Plain Sans" "PlainSans-Regular.ttf" "-" 400 0 - ofl
fx face "$LIB/slantserif" "Slant Serif" "SlantSerif-Regular.ttf" "-" 400 0 - ofl
fx face "$LIB/slantserif" "Slant Serif" "SlantSerif-Italic.ttf" "-" 400 1 - ofl
fx face "$LIB/flexsans" "Flex Sans" "FlexSans[wght].ttf" "$PTX" 400 0 wght ofl
fx face "$LIB/closedsans" "Closed Sans" "ClosedSans-Regular.ttf" "-" 400 0 - unknown
python3 - "$T/candidates.json" <<'PY'
import json, sys
json.dump({"languages": ["pt"], "candidates": [
    {"id": "plain", "family": "Plain Sans", "dir": "plainsans", "files": ["PlainSans-Regular.ttf"], "italic": True, "group": "serious"},
    {"id": "slant", "family": "Slant Serif", "dir": "slantserif", "files": ["SlantSerif-Regular.ttf", "SlantSerif-Italic.ttf"], "italic": False},
    {"id": "flex", "family": "Flex Sans", "dir": "flexsans", "files": ["FlexSans[wght].ttf"]},
    {"id": "closed", "family": "Closed Sans", "dir": "closedsans", "files": ["ClosedSans-Regular.ttf"]}]},
    open(sys.argv[1], "w"))
PY
fontsrun() { ASGARD_FONTS_BASE="file://$LIB" ASGARD_FONTS_DIR="$DL" "$BRAND" fonts "$C" "$T/candidates.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"; }
# shellcheck disable=SC2329
fcode() { [ "$(cat "$C.fonts.code")" = "$1" ]; }
XDG_CACHE_HOME="$T/empty" "$BRAND" fonts "$C" "$T/candidates.json" >/dev/null 2>&1
check "fonts refuses to run without the environment" [ $? -eq 2 ]
fontsrun
check "fonts fetches the candidates and writes their facts" fcode 0
check "the facts are in the company's choices folder" test -f "$FACTS"
check "each candidate's files and licence are downloaded, unchanged" test -f "$DL/plainsans/PlainSans-Regular.ttf" -a -f "$DL/plainsans/OFL.txt"
# shellcheck disable=SC2329
hash_matches() {
  [ "$(fx json-get "$FACTS" 'd["candidates"][0]["files"][0]["sha256"]')" = "$(sha256sum "$DL/plainsans/PlainSans-Regular.ttf" | cut -d' ' -f1)" ]
}
check "the file's hash is recorded and matches the download" hash_matches
check "a face with no italic file is reported without italic, whatever the candidates file says" \
  fx json "$FACTS" 'd["candidates"][0]["italic"] is False'
check "and the disagreement is noted" fx json "$FACTS" 'any("italic" in x for x in d["candidates"][0]["notes"])'
check "a face with an italic file is reported with it, and the file is named" \
  fx json "$FACTS" 'd["candidates"][1]["italic"] is True and d["candidates"][1]["italic_from"] == "SlantSerif-Italic.ttf"'
check "even when the candidates file says it has none" fx json "$FACTS" 'any("italic" in x for x in d["candidates"][1]["notes"])'
check "a variable font's weights come from its axis" \
  fx json "$FACTS" 'd["candidates"][2]["weights"] == [{"min": 300, "max": 700}]'
check "a static font's weight comes from the file" \
  fx json "$FACTS" 'd["candidates"][0]["weights"] == [{"min": 400, "max": 400}]'
check "the glyphs of each language are counted from the font" \
  fx json "$FACTS" 'd["candidates"][0]["glyphs"]["pt"]["covers"] is False and d["candidates"][0]["glyphs"]["pt"]["missing"] > 50'
check "a font that covers the language is reported as covering it" \
  fx json "$FACTS" 'd["candidates"][2]["glyphs"]["pt"]["missing"] < d["candidates"][0]["glyphs"]["pt"]["missing"]'
check "the family name is read from the file" fx json "$FACTS" 'd["candidates"][0]["family_in_file"] == "Plain Sans"'
check "a known open licence is named by its SPDX id" fx json "$FACTS" 'd["candidates"][0]["licence"]["spdx"] == "OFL-1.1"'
check "a licence the tool does not know has no id, and is flagged for a person" \
  fx json "$FACTS" 'd["candidates"][3]["licence"]["spdx"] is None and any("licence" in x for x in d["candidates"][3]["notes"])'
check "the candidates file's own fields travel with the facts" fx json "$FACTS" 'd["candidates"][0]["group"] == "serious"'
check "the library folder to copy from is named" fx json "$FACTS" 'd["candidates"][0]["dir"] == "plainsans"'
check "the facts hold no path of this machine" lacks_text "$FACTS" "$DL"
check "fonts writes nothing else in the company" only_choices_changed "$C"
check "the names check passes after fonts" names_pass "$C"
sum1="$(sha256sum "$FACTS")"; fontsrun
check "a second run writes the same facts" [ "$(sha256sum "$FACTS")" = "$sum1" ]
ASGARD_FONTS_BASE="file://$T/nowhere" ASGARD_FONTS_DIR="$DL" "$BRAND" fonts "$C" "$T/candidates.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"
check "a second run needs no library: the downloads are kept" fcode 0

use fonts2; FACTS="$C/docs/7-branding/identity/choices/fonts-facts.json"
python3 - "$T/candidates-bad.json" <<'PY'
import json, sys
json.dump({"candidates": [{"id": "a", "family": "Plain Sans", "dir": "plainsans", "files": ["PlainSans-Regular.ttf"]},
                          {"id": "b", "family": "Gone", "dir": "gone", "files": ["Gone-Regular.ttf"]}]}, open(sys.argv[1], "w"))
PY
DL2="$T/downloads2"
ASGARD_FONTS_BASE="file://$LIB" ASGARD_FONTS_DIR="$DL2" "$BRAND" fonts "$C" "$T/candidates-bad.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"
check "a file the library does not have refuses the run, with code 2" fcode 2
check "and names the file" says "$C.fonts.out" "Gone-Regular.ttf"
check "and writes no facts" test ! -f "$FACTS"
python3 - "$T/candidates-evil.json" <<'PY'
import json, sys
json.dump({"candidates": [{"id": "a", "family": "X", "dir": "../x", "files": ["a.ttf"]}]}, open(sys.argv[1], "w"))
PY
ASGARD_FONTS_BASE="file://$LIB" ASGARD_FONTS_DIR="$DL2" "$BRAND" fonts "$C" "$T/candidates-evil.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"
check "a folder name that leaves the library is refused" fcode 2
python3 - "$T/candidates-evil2.json" <<'PY'
import json, sys
json.dump({"candidates": [{"id": "a", "family": "X", "dir": "plainsans", "files": ["../../secret.ttf"]}]}, open(sys.argv[1], "w"))
PY
ASGARD_FONTS_BASE="file://$LIB" ASGARD_FONTS_DIR="$DL2" "$BRAND" fonts "$C" "$T/candidates-evil2.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"
check "a file name that leaves the folder is refused" fcode 2
ASGARD_FONTS_BASE="http://example.org/ofl" ASGARD_FONTS_DIR="$DL2" "$BRAND" fonts "$C" "$T/candidates.json" >"$C.fonts.out" 2>&1; echo $? >"$C.fonts.code"
check "a library address that is not https or a local folder is refused" fcode 2
check "fonts without a candidates file is refused" [ "$("$BRAND" fonts "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]
# Palette rounds (design system tasks DS-T06): every preset is checked with the company's contrast rules before it is shown.
use rounds; RF="$C/docs/7-branding/identity/choices/palette-round-1.json"; ROUND="$T/round.json"
paletteround() { "$BRAND" palette "$C" "$ROUND" >"$C.round.out" 2>&1; echo $? >"$C.round.code"; }
# shellcheck disable=SC2329
rcode() { [ "$(cat "$C.round.code")" = "$1" ]; }
# shellcheck disable=SC2329
blames_only_pale() { ! grep -q "calm\|bold" "$C.round.out"; }
fx round "$ROUND" light-fail; paletteround
check "a round with one failing preset is refused, with code 2" rcode 2
check "the failing preset is named" says "$C.round.out" "pale"
check "with the mode, the pair, the ratio and the minimum" says "$C.round.out" "light: muted on bg is 2.84:1, under the minimum 4.5:1"
check "the passing presets are not blamed" blames_only_pale
check "nothing is written for a refused round" test ! -f "$RF"
fx round "$ROUND" dark-fail; paletteround
check "a preset that fails only in dark mode is refused too" rcode 2
check "and says dark" says "$C.round.out" "dark: muted on bg"
fx round "$ROUND" ok; paletteround
check "a round whose presets all pass is accepted" rcode 0
check "and writes the round where the pages read it" test -f "$RF"
check "each preset carries its contrast rows" fx json "$RF" 'len(d["presets"]) == 3 and all(len(p["contrast"]) > 10 for p in d["presets"])'
check "and its result in words" fx json "$RF" 'all(p["result"] == "passes" for p in d["presets"])'
check "the round number and the presets' names are kept" fx json "$RF" 'd["round"] == 1 and d["presets"][1]["name"] == "Bold plum"'
check "the message colours are checked with the rest" fx json "$RF" 'any(r["fg"] == "crit" for r in d["presets"][0]["contrast"])'
check "the run says each preset passes" says "$C.round.out" "calm: passes"
check "the round writes nothing else in the company" only_choices_changed "$C"
check "the names check passes after the round" names_pass "$C"
sum1="$(sha256sum "$RF")"; paletteround
check "a second run writes the same file" [ "$(sha256sum "$RF")" = "$sum1" ]
fx round "$ROUND" brand-ok; paletteround
check "a brand token with a light and a dark value is accepted" rcode 0
for kind in five missing-key bad-hex dup brand-half round4; do
  fx round "$ROUND" "$kind"; paletteround
  check "a round with a bad shape ($kind) is refused with code 2" rcode 2
done
fx round "$ROUND" missing-key; paletteround
check "a missing colour is named with its preset and mode" says "$C.round.out" "calm: light: border is not set"
fx round "$ROUND" bad-hex; paletteround
check "a value that is not #RRGGBB is named" says "$C.round.out" "bold: dark: text is 'white', not #RRGGBB"
fx round "$ROUND" brand-half; paletteround
check "a brand token without its other mode is named" says "$C.round.out" "calm: brand-1 has no dark value"
fx round "$ROUND" five; paletteround
check "more than four presets are refused" says "$C.round.out" "four presets"
fx round "$ROUND" round4; paletteround
check "a fourth round is refused: the agent asks what is missing" says "$C.round.out" "three rounds"
check "palette without a round file is refused" [ "$("$BRAND" palette "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]

# Logo preparation (design system tasks DS-T07): cut out, flatten, enlarge.
use prep; PREP="$C/docs/7-branding/identity/choices/logo-prep"
prep() { local flag=(); if [ "$1" = "--mark" ]; then flag=(--mark); shift; fi
  "$BRAND" logo-prep ${flag[@]+"${flag[@]}"} "$C" "$1" >"$C.prep.out" 2>&1; echo $? >"$C.prep.code"; }
# shellcheck disable=SC2329
pcode() { [ "$(cat "$C.prep.code")" = "$1" ]; }
fx draw opaque "$T/opaque.png"; prep "$T/opaque.png"
check "logo-prep takes an image on an opaque flat background and writes a prepared PNG" pcode 0
check "in the choices folder, named after the image" test -f "$PREP/opaque.png"
check "the background is cut out: the corners are transparent" fx clear-corners "$PREP/opaque.png"
check "the short side is at least 1000 pixels" fx short "$PREP/opaque.png" 1000
fx arcs "$T/arcs.png"; prep "$T/arcs.png"
check "an anti-aliased image is flattened to its flat colours, with a binary alpha" fx colours "$PREP/arcs.png" 2
check "its facts are written beside it, with the colours found" fx json "$PREP/arcs.json" 'len(d["colours"]) == 2 and d["background"]["from"] == "removed"'
check "and the scale used" fx json "$PREP/arcs.json" 'd["scale"] >= 1 and d["output"]["short_side"] >= 1000'
sum1="$(sha256sum "$PREP/arcs.png")"; prep "$T/arcs.png"
check "a second run writes the same image" [ "$(sha256sum "$PREP/arcs.png")" = "$sum1" ]
fx draw mark "$T/transparent.png"; prep "$T/transparent.png"
check "an image that is already transparent keeps its transparency" fx clear-corners "$PREP/transparent.png"
check "and says its background was given" fx json "$PREP/transparent.json" 'd["background"]["from"] == "given"'
fx jpeg "$T/photo.jpg"; prep "$T/photo.jpg"
check "a JPEG is accepted, by its first bytes" pcode 0
check "and its compression noise is flattened away" fx colours "$PREP/photo.png" 2
fx photo "$T/small.png" 200; prep "$T/small.png"
check "an image under 256 pixels is refused, with code 2" pcode 2
fx noisy "$T/noisy.png"; prep "$T/noisy.png"
check "a background that is not one flat colour is refused" pcode 2
check "and says so" says "$C.prep.out" "flat colour"
fx blank "$T/blank.png"; prep "$T/blank.png"
check "an image with nothing but a background is refused" pcode 2
printf 'not an image' >"$T/text.png"; prep "$T/text.png"
check "a file that is not an image is refused" pcode 2
fx draw huge "$T/huge.png"; prep "$T/huge.png"
check "an image over 8192 pixels is refused" pcode 2
check "logo-prep without an image is refused" [ "$("$BRAND" logo-prep "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]
check "logo-prep writes nothing outside the choices folder" only_choices_changed "$C"
# a mark of long arcs: at 1400 pixels the trace cuts them short; prepared at 2400 or more, it is faithful
use arcs1400; fx arcs "$SRC/logo.png" flat; logo
check "a mark of long arcs at 1400 pixels is not traced faithfully" trace 't["modes"]["light"]["mismatch"] > 0.01'
use arcsprep; PREP="$C/docs/7-branding/identity/choices/logo-prep"; fx arcs "$T/arcs-mark.png"; prep --mark "$T/arcs-mark.png"
check "a mark is enlarged to at least 2400 pixels on its short side" fx short "$PREP/arcs-mark.png" 2400
cp "$PREP/arcs-mark.png" "$SRC/logo.png"; logo
check "the same mark, prepared, traces faithfully" trace 't["modes"]["light"]["mismatch"] <= 0.01'

# Logo proposals (design system tasks DS-T07): the review page, and the chosen design as source PNGs.
use props; PD="$C/docs/7-branding/identity/choices"; PAGE="$PD/logo-proposals.html"; FACTSF="$PD/fonts-facts.json"
PLIB="$T/proplib"; PDL="$T/propdl"
LET="$(python3 -c 'print(",".join("%x" % c for c in list(range(0x41, 0x5b)) + list(range(0x61, 0x7b)) + [0x20]))')"
fx face "$PLIB/plainface" "Plain Face" "PlainFace-Regular.ttf" "$LET" 400 0 - ofl
fx face "$PLIB/ringface" "Ring Face" "RingFace-Regular.ttf" "$LET" 400 0 - ofl ring
fx face "$PLIB/narrowface" "Narrow Face" "NarrowFace-Regular.ttf" "$LET" 400 0 - ofl narrow
fx face "$PLIB/scriptface" "Script Face" "ScriptFace-Regular.ttf" "$LET" 400 0 - ofl tall
fx face "$PLIB/partface" "Part Face" "PartFace-Regular.ttf" "41,42,43" 400 0 - ofl
python3 - "$T/prop-fonts.json" <<'PY'
import json, sys
def c(i, name, group, **kw):
    return {"id": i, "family": name, "dir": i + "face", "files": [name.replace(" ", "") + "-Regular.ttf"], "group": group, **kw}
json.dump({"languages": ["en"], "candidates": [c("plain", "Plain Face", "serious"), c("ring", "Ring Face", "serious"),
    c("narrow", "Narrow Face", "serious"), c("script", "Script Face", "stylised", joined=True),
    c("part", "Part Face", "stylised")]}, open(sys.argv[1], "w"))
PY
ASGARD_FONTS_BASE="file://$PLIB" ASGARD_FONTS_DIR="$PDL" "$BRAND" fonts "$C" "$T/prop-fonts.json" >/dev/null 2>&1
mkdir -p "$PD/concept"; fx draw mark "$PD/concept/mark.png"; fx draw wide "$PD/concept/wide.png"
python3 - "$T/prop.json" <<'PY'
import json, sys
json.dump({"name": "Example Studio", "faces": ["plain", "ring", "narrow", "script", "part"], "alternatives": [
    {"id": "drawn", "name": "As drawn", "strength": "Keeps the concept exactly", "risk": "The lettering is not a real typeface",
     "fails_at": 24, "image": "docs/7-branding/identity/choices/concept/wide.png", "mark": "docs/7-branding/identity/choices/concept/mark.png", "lettering": False},
    {"id": "named", "name": "Mark beside the name", "strength": "The mark works alone as the favicon",
     "risk": "The name is long at small sizes", "fails_at": 32, "mark": "docs/7-branding/identity/choices/concept/mark.png",
     "lettering": True, "layout": "beside", "symbol_in": "o"},
    {"id": "swap", "name": "Mark above the name", "strength": "Compact", "risk": "A letter is replaced by the mark",
     "mark": "docs/7-branding/identity/choices/concept/mark.png", "lettering": True, "layout": "above", "replaces_letter": "i",
     "poor_fit": {"ring": "The agent's own note about this pairing"}}]}, open(sys.argv[1], "w"))
PY
# shellcheck disable=SC2329
check_page() { "$BRAND" check-page "$C" "$1" >"$C.cp.out" 2>&1; }
proposals() { ASGARD_FONTS_DIR="$PDL" "$BRAND" logo-proposals "$@" >"$C.prop.out" 2>&1; echo $? >"$C.prop.code"; }
# shellcheck disable=SC2329
ppcode() { [ "$(cat "$C.prop.code")" = "$1" ]; }
proposals "$C" "$T/prop.json"
check "logo-proposals writes the review page" ppcode 0
check "in the choices folder" test -f "$PAGE"
check "with a panel for each alternative, with its name, strength and risk" \
  fx page "$PAGE" 'all(a["id"] in html and a["name"] in html and a["strength"] in html and a["risk"] in html for a in d["alternatives"])'
check "the page says where each alternative fails, when it does" fx page "$PAGE" '"24" in html and "fails" in html'
check "it has a lettering picker with a serious and a stylised group" \
  fx page "$PAGE" '"Serious" in html and "Stylised" in html and len(d["faces"]) == 5'
check "each face shows its licence" fx page "$PAGE" 'all(f["licence"] == "OFL-1.1" for f in d["faces"])'
check "each alternative has the logo in a light and a dark row at four sizes" \
  fx page "$PAGE" 'all(len(d["images"][a["id"]][f["id"]]["light"]) > 100 and len(d["images"][a["id"]][f["id"]]["dark"]) > 100 for a in d["alternatives"] for f in d["faces"])'
check "and the mark at its sizes, with the enlarged 16" fx page "$PAGE" 'all(len(d["marks"][a["id"]]["light"]) > 100 for a in d["alternatives"])'
check "the page needs no network: no address in it" fx page "$PAGE" '"http" not in html'
check "a pairing the face cannot set carries a note: the characters it lacks" \
  fx page "$PAGE" 'any("lacks" in n for n in d["notes"]["named"]["part"])'
check "a symbol in the counter of a narrow o carries a note" \
  fx page "$PAGE" 'any("counter" in n for n in d["notes"]["named"]["narrow"])'
check "and a wide counter does not" fx page "$PAGE" 'not any("counter" in n for n in d["notes"]["named"]["ring"])'
check "a letter replaced in a joined face carries a note" \
  fx page "$PAGE" 'any("joined" in n for n in d["notes"]["swap"]["script"])'
check "the agent's own note for a pairing is shown" fx page "$PAGE" 'any("own note" in n for n in d["notes"]["swap"]["ring"])'
check "an alternative with no lettering has no pairing notes" fx page "$PAGE" 'all(d["notes"]["drawn"][f["id"]] == [] for f in d["faces"])'
check "a pairing with a note is not hidden: the picker still offers the face" fx page "$PAGE" 'any(f["id"] == "part" for f in d["faces"])'
check "the page passes the page check: every option changes it, every image decodes" check_page "$PAGE"
check "each face's facts are read from its file when the page is built" \
  fx page "$PAGE" 'all("weights" in f and f["italic"] is False for f in d["faces"])'
check "the page is written only in the choices folder" only_choices_changed "$C"
check "the names check passes" names_pass "$C"
check "the generated page is not committed: the company's ignore file holds it back" git -C "$C" check-ignore -q "$PAGE"
check "the pages build strictly with the choices in the docs" builds "$C"
check "and the docs check passes" docs_pass "$C"
sum1="$(sha256sum "$PAGE")"; proposals "$C" "$T/prop.json"
check "a second run writes the same page" [ "$(sha256sum "$PAGE")" = "$sum1" ]
cp "$T/prop.json" "$T/prop-bad.json"; sed -i 's/"ring", "narrow"/"ring", "ghost"/' "$T/prop-bad.json"; proposals "$C" "$T/prop-bad.json"
check "a face that is not in the fonts' facts is refused" ppcode 2
check "and named, with the command that makes the facts" says "$C.prop.out" "ghost"
python3 - "$FACTSF" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["candidates"][0]["italic"] = True; d["candidates"][0]["weights"] = [{"min": 900, "max": 900}]
json.dump(d, open(sys.argv[1], "w"))
PY
proposals "$C" "$T/prop.json"
check "facts typed by hand do not reach the page: it shows what the file says" \
  fx page "$PAGE" 'd["faces"][0]["italic"] is False and d["faces"][0]["weights"] == [{"min": 400, "max": 400}]'
printf 'x' >>"$PDL/plainface/PlainFace-Regular.ttf"; proposals "$C" "$T/prop.json"
check "a font file that changed since its facts were read is refused" ppcode 2
check "and the run to repeat is named" says "$C.prop.out" "brand.sh fonts"
ASGARD_FONTS_BASE="file://$PLIB" ASGARD_FONTS_DIR="$PDL" "$BRAND" fonts "$C" "$T/prop-fonts.json" >/dev/null 2>&1
sed 's#docs/7-branding/identity/choices/concept/mark.png#../../../etc/passwd#' "$T/prop.json" >"$T/prop-evil.json"; proposals "$C" "$T/prop-evil.json"
check "an image outside the company folder is refused" ppcode 2
python3 - "$T/prop.json" "$T/prop-noname.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); del d["alternatives"][0]["strength"]; json.dump(d, open(sys.argv[2], "w"))
PY
proposals "$C" "$T/prop-noname.json"
check "an alternative without its strength is refused" ppcode 2
check "logo-proposals without a candidates file is refused" [ "$("$BRAND" logo-proposals "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]

# The chosen design becomes the logo's source PNGs, in the palette's text and accent colours.
use props2; PD="$C/docs/7-branding/identity/choices"; PAGE="$PD/logo-proposals.html"; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"
mkdir -p "$PD/concept"; fx draw mark "$PD/concept/mark.png"; fx draw wide "$PD/concept/wide.png"
ASGARD_FONTS_BASE="file://$PLIB" ASGARD_FONTS_DIR="$PDL" "$BRAND" fonts "$C" "$T/prop-fonts.json" >/dev/null 2>&1
proposals "$C" "$T/prop.json" --choose named:ring
check "--choose writes the chosen design as source PNGs" ppcode 0
check "the logo for light backgrounds" test -f "$SRC/logo.png"
check "and for dark backgrounds" test -f "$SRC/logo-dark.png"
check "and the mark" test -f "$SRC/mark.png"
check "each reaches 1000 pixels on its short side" fx short "$SRC/logo.png" 1000
check "the light logo is drawn in the palette's text colour" fx has-colour "$SRC/logo.png" "#1A1A1A"
check "and its accent colour" fx has-colour "$SRC/logo.png" "#0B5FCC"
check "the dark logo is drawn in the dark palette's text colour" fx has-colour "$SRC/logo-dark.png" "#EDEDED"
check "the choice is recorded, with the typeface for the wordmark role" \
  fx json "$PD/logo.json" 'd["alternative"] == "named" and d["face"] == "ring" and d["wordmark"]["family"] == "Ring Face" and d["wordmark"]["licence"] == "OFL-1.1"'
logo
check "brand.sh logo takes the chosen design" lcode 0
proposals "$C" "$T/prop.json" --choose drawn
check "an alternative with no lettering is chosen without a face" ppcode 0
proposals "$C" "$T/prop.json" --choose named
check "a lettered alternative needs a face" ppcode 2
proposals "$C" "$T/prop.json" --choose ghost:ring
check "an alternative that does not exist is refused" ppcode 2
proposals "$C" "$T/prop.json" --choose named:ghost
check "and so is a face that does not" ppcode 2
proposals "$C" "$T/prop.json" --choose saved
check "--choose saved with nothing saved is refused" ppcode 2
check "and says what is missing" says "$C.prop.out" "no choice saved"
python3 - "$PD/logo.json" <<'PY'
import json, sys
json.dump({"step": "logo", "choice": {"alternative": "swap", "face": "ring"}, "reason": "Calm and compact", "date": "2026-10-28"}, open(sys.argv[1], "w"))
PY
proposals "$C" "$T/prop.json"
check "a saved choice is embedded in the page it builds" fx page "$PAGE" '"Calm and compact" in html'
check_page "$PAGE"
# shellcheck disable=SC2329
says_saved() { says "$C.cp.out" "reopens on the saved choice"; }
check "and the page reopens on it, proved in the browser" says_saved
proposals "$C" "$T/prop.json" --choose saved
check "--choose saved applies the saved choice" ppcode 0
check "and records the chosen proposal beside her reason" \
  fx json "$PD/logo.json" 'd["alternative"] == "swap" and d["face"] == "ring" and d["reason"] == "Calm and compact" and d["choice"]["face"] == "ring"'

# The choice pages (design system tasks DS-T12): the four rules of spec §5.7, and the local server that saves a choice.
use pages; CH="$C/$ID_REL/choices"; mkdir -p "$CH"
FONTURI="$(fx fontdata)"
pagecheck() { "$BRAND" check-page "$C" "$1" >"$C.page.out" 2>&1; echo $? >"$C.page.code"; }
# shellcheck disable=SC2329
pgcode() { [ "$(cat "$C.page.code")" = "$1" ]; }
fx optionpage "$CH/good.html" good; pagecheck "$CH/good.html"
check "a page whose every option changes it passes the page check" pgcode 0
check "and says what it proved" says_all "$C.page.out" "tone" "light" "dark" "390" "820" "1280"
fx optionpage "$CH/dead.html" dead; pagecheck "$CH/dead.html"
check "an option that changes nothing makes the check fail (rule 4)" pgcode 1
check "and names the group and the two options" says "$C.page.out" "tone: the options a and c do not change what the page shows"
fx optionpage "$CH/dark.html" dark-only; pagecheck "$CH/dark.html"
check "an option that differs from another only in dark mode is a visible change: it passes" pgcode 0
fx optionpage "$CH/face.html" face-ok "$FONTURI"; pagecheck "$CH/face.html"
check "a page whose face loads passes the font check (rule 3)" pgcode 0
check "and lists the face as loaded" says "$C.page.out" "Probe Face: loaded"
fx optionpage "$CH/broken.html" face-broken; pagecheck "$CH/broken.html"
check "a face that does not load makes the check fail" pgcode 1
check "and names the family" says "$C.page.out" "Probe Face: did not load"
fx optionpage "$CH/image.html" broken-image; pagecheck "$CH/image.html"
check "an image that does not decode makes the check fail" pgcode 1
fx optionpage "$CH/quote.html" double-quoted; pagecheck "$CH/quote.html"
check "a font name in double quotes inside a style attribute is refused (the attribute would break)" pgcode 1
check "and says so" says "$C.page.out" "single-quoted"
fx optionpage "$CH/saved.html" saved; pagecheck "$CH/saved.html"
check "a page reopens on the saved choice (rule 1)" pgcode 0
check "and says it did" says "$C.page.out" "reopens on the saved choice"
fx optionpage "$CH/unrestored.html" unrestored; pagecheck "$CH/unrestored.html"
check "a page that does not restore the saved choice fails" pgcode 1
check "and says what differs" says "$C.page.out" "tone: saved b, the page shows a"
pagecheck "$CH/nothere.html"
check "check-page of a file that is not there is refused, with code 2" pgcode 2
check "check-page without a page is refused" [ "$("$BRAND" check-page "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]
mkdir -p "$C/.ouroboric"; printf '{"executable": "/nonexistent/browser"}\n' >"$C/.ouroboric/browser.json"; pagecheck "$CH/good.html"
check "a browser set in the company's own settings is used" pgcode 2
check "and a missing one is named" says "$C.page.out" "/nonexistent/browser"

# The local server (design system tasks DS-T12): serves the pages on 127.0.0.1 and saves a choice into the company's files.
use served; CH="$C/$ID_REL/choices"; mkdir -p "$CH"; fx optionpage "$CH/playground.html" good
PORT="$(fx freeport)"; BASEURL="http://127.0.0.1:$PORT"
"$BRAND" serve "$C" --port "$PORT" >"$C.serve.out" 2>&1 &
SERVER=$!
for _ in $(seq 1 50); do grep -q "127.0.0.1" "$C.serve.out" 2>/dev/null && break; sleep 0.2; done
# shellcheck disable=SC2329
status_is() { [ "$(fx http "${@:2}" | head -1)" = "$1" ]; }
# shellcheck disable=SC2329
body_has() { fx http GET "$1" | grep -q -- "$2"; }
# shellcheck disable=SC2329
stopped() { ! kill -0 "$SERVER" 2>/dev/null; }
check "serve says where it listens, on 127.0.0.1 only" says "$C.serve.out" "http://127.0.0.1:$PORT/"
check "the index lists the pages" body_has "$BASEURL/" playground
check "a page is served" status_is 200 GET "$BASEURL/page/playground"
check "with the token filled in" [ "$(fx token "$BASEURL/page/playground" | wc -c)" -gt 20 ]
TOKEN="$(fx token "$BASEURL/page/playground")"
BODY='{"choice": {"tone": "b"}, "reason": "I like the blue"}'
check "a choice with the token is saved" status_is 200 POST "$BASEURL/save/playground" "$BODY" application/json "$TOKEN"
SAVEDF="$CH/playground.json"
check "in the design system's choices folder" test -f "$SAVEDF"
check "with the choice, the reason and the date" \
  fx json "$SAVEDF" 'd["choice"] == {"tone": "b"} and d["reason"] == "I like the blue" and d["step"] == "playground" and len(d["date"]) == 10'
check "and the saved choice is read back" status_is 200 GET "$BASEURL/choices/playground.json"
check "the served page reopens on it" body_has "$BASEURL/page/playground" "I like the blue"
sumsaved="$(sha256sum "$SAVEDF")"
check "no token is refused" status_is 403 POST "$BASEURL/save/playground" "$BODY" application/json ""
check "a wrong token is refused" status_is 403 POST "$BASEURL/save/playground" "$BODY" application/json "nope"
check "a body that is not JSON by its type is refused" status_is 415 POST "$BASEURL/save/playground" "$BODY" text/plain "$TOKEN"
check "a step that is not one of the design's steps is refused" status_is 404 POST "$BASEURL/save/nothing" "$BODY" application/json "$TOKEN"
check "a step that leaves the folder is refused" status_is 404 POST "$BASEURL/save/..%2Fsecret" "$BODY" application/json "$TOKEN"
check "a choice that is not an object is refused" status_is 400 POST "$BASEURL/save/playground" '{"choice": "b", "reason": ""}' application/json "$TOKEN"
check "a reason that is not text is refused" status_is 400 POST "$BASEURL/save/playground" '{"choice": {"tone": "a"}, "reason": 5}' application/json "$TOKEN"
check "a body over 64 KB is refused" status_is 413 POST "$BASEURL/save/playground" "@big" application/json "$TOKEN"
check "a request for another host name is refused (DNS rebinding)" status_is 421 GET "$BASEURL/page/playground" "" "" "" "evil.example"
check "a page that is not there is a 404" status_is 404 GET "$BASEURL/page/nothing"
check "a file outside the pages is not served" status_is 404 GET "$BASEURL/page/..%2F..%2Ftokens"
check "refused requests changed nothing" [ "$(sha256sum "$SAVEDF")" = "$sumsaved" ]
kill "$SERVER" 2>/dev/null; wait "$SERVER" 2>/dev/null
check "serve stops when it is told to" stopped
check "serve wrote nothing but the choice" only_choices_changed "$C"
check "serve without a company folder is refused" [ "$("$BRAND" serve >/dev/null 2>&1; echo $?)" -eq 2 ]

# The palette page (design system tasks DS-T14): step 6b, one option at a time.
use palpage; CH="$C/$ID_REL/choices"; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx draw mark "$SRC/logo.png"
PG="$CH/palette.html"; ROUNDF="$T/pal-round.json"
palpage() { "$BRAND" palette-page "$C" >"$C.pp.out" 2>&1; echo $? >"$C.pp.code"; }
# shellcheck disable=SC2329
ppgcode() { [ "$(cat "$C.pp.code")" = "$1" ]; }
palpage
check "palette-page without a checked round is refused" ppgcode 2
check "and names the command that makes one" says "$C.pp.out" "brand.sh palette"
fx round "$ROUNDF" roles-fail; "$BRAND" palette "$C" "$ROUNDF" >/dev/null 2>&1; palpage
check "palette-page writes the page from the latest checked round" ppgcode 0
check "in the choices folder" test -f "$PG"
check "the page is not committed: it is ignored" git -C "$C" check-ignore -q "$PG"
check "the page passes the page check: every preset and every candidate colour changes it" check_page "$PG"
check "each preset is a card of its own, shown one at a time, with its mood" \
  fx page "$PG" 'len(d["presets"]) == 3 and all(p["mood"] in html for p in d["presets"]) and html.count("data-view=\"preset\"") == 3'
check "each colour role has its own card with an explanation in plain words" \
  fx page "$PG" 'all(r in html for r in ("The page background", "Text on a plain background", "The brand colour", "Text on a brand-colour fill"))'
check "and the card of one role is shown at a time" fx browse "$PG" 'document.querySelectorAll("[data-card]:not([hidden])").length === 1'
check "the contrast results are in words, with the ratio and the minimum" \
  fx page "$PG" '"passes" in html and "needs at least 4.5:1" in html'
check "the logo is shown recoloured by the palette, through masks of its own colours" \
  fx page "$PG" '"mask-image" in html and "--logo-0" in html and len(d["logo"]["layers"]) == 2'
check "the page's live rules give brand.py's ratio and result for every pair of every preset" \
  fx browse "$PG" 'window.__rules && __data().presets.every(p => { const r = window.__rules.rows(p.light, p.dark); return r.length === p.contrast.length && r.every((x, i) => x.result === p.contrast[i].result && Math.abs(x.ratio - p.contrast[i].ratio) < 0.001); })'
check "a candidate equal to the first preset's own value is left out, so it is not an option that changes nothing" \
  fx page "$PG" 'not any(c["id"] == "same" for c in d["roles"].get("accent", []))'
check "and the build says so" says "$C.pp.out" "same"
check "a candidate colour that breaks a rule shows a warning in words" \
  fx browse "$PG" '(() => { document.querySelector("input[name=role-muted][value=fainter]").click(); return document.getElementById("warnings").textContent.includes("muted on bg"); })()'
check "the final palette is what the agent reads: a result with both modes" \
  fx browse "$PG" 'window.__choiceResult && window.__choiceResult().light.bg && window.__choiceResult().dark.bg'
check "the page builds strictly with the choices in the docs" builds "$C"
check "the names check passes" names_pass "$C"
fx round "$ROUNDF" ok; "$BRAND" palette "$C" "$ROUNDF" >/dev/null 2>&1; palpage
check "a round without candidates still gives a page" ppgcode 0
printf '{"step": "palette", "choice": {"preset": "bold", "role-accent": "keep"}, "reason": "Plum feels like us"}' >"$CH/palette.json"; palpage
check "a saved choice is restored in the page" check_page "$PG"
check "and says so" says "$C.cp.out" "reopens on the saved choice"

exit "$fail"
