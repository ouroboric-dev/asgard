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
TLIBDIR="$T/typelib"; export TLIBDIR
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
brand_check_passes() { (cd "$1" && python3 .ouroboric/checks/brand.py check >"$1.bc.out" 2>&1); }
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
check "and the card of one role is shown at a time" fx browse "$PG" 'Array.from(document.querySelectorAll("[data-card]")).filter(c => getComputedStyle(c).display !== "none").length === 1'
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

# The typography pages (design system tasks DS-T15): width first (a direction at a time), then depth in the directions she
# likes, then the roles. Each page is built from what the one before saved.
use typage; CH="$C/$ID_REL/choices"; TLIB="$T/typelib"; TDL="$T/typedl"
ALL="$(python3 -c 'print(",".join("%x" % c for c in range(0x20, 0x7f)))')"
fx face "$TLIB/plainface" "Plain Face" "PlainFace-Regular.ttf" "$ALL" 400 0 - ofl
fx face "$TLIB/slantface" "Slant Face" "SlantFace[wght].ttf" "$ALL" 400 0 wght ofl
fx face "$TLIB/slantface" "Slant Face" "SlantFace-Italic[wght].ttf" "$ALL" 400 1 wght ofl
fx face "$TLIB/boldface" "Bold Face" "BoldFace-Regular.ttf" "$ALL" 700 0 - ofl ring
fx face "$TLIB/penface" "Pen Face" "PenFace-Regular.ttf" "$ALL" 400 0 - ofl tall
fx face "$TLIB/softface" "Soft Face" "SoftFace-Regular.ttf" "$ALL" 400 0 - ofl narrow
fx face "$TLIB/roundface" "Round Face" "RoundFace-Regular.ttf" "$ALL" 500 0 - ofl ring
fx face "$TLIB/inkface" "Ink Face" "InkFace-Regular.ttf" "$ALL" 400 0 - ofl narrow
python3 - "$T/faces.json" "$TLIB" <<'PY'
import hashlib, json, os, sys
out, lib = sys.argv[1:]
def face(i, fam, kind, direction, tier, suits, files):
    return {"id": i, "family": fam, "dir": i + "face", "kind": kind, "direction": direction, "tier": tier, "voices": ["calm"], "suits": suits,
            "note": f"{fam} for the test.", "licence": "OFL-1.1",
            "files": [{"name": n, "sha256": hashlib.sha256(open(os.path.join(lib, i + "face", n), "rb").read()).hexdigest()} for n in files]}
SANS, SERIF, SCRIPT = ["body", "heading", "ui"], ["body", "heading", "display"], ["wordmark", "display"]
json.dump({"library": "test", "ref": "0" * 40,
  "directions": [{"id": "clean", "name": "Clean sans", "text": "Plain and neutral.", "voices": ["calm"], "suits": SANS},
                 {"id": "book", "name": "Book serif", "text": "Warm and classic.", "voices": ["warm"], "suits": SERIF},
                 {"id": "pen", "name": "Pen script", "text": "Written by hand.", "voices": ["personal"], "suits": SCRIPT}],
  "faces": [face("plain", "Plain Face", "sans", "clean", "start", SANS, ["PlainFace-Regular.ttf"]),
            face("round", "Round Face", "sans", "clean", "start", SANS, ["RoundFace-Regular.ttf"]),
            face("slant", "Slant Face", "serif", "book", "start", SERIF + ["ui"], ["SlantFace[wght].ttf", "SlantFace-Italic[wght].ttf"]),
            face("bold", "Bold Face", "serif", "book", "start", SERIF, ["BoldFace-Regular.ttf"]),
            face("soft", "Soft Face", "serif", "book", "deeper", SERIF, ["SoftFace-Regular.ttf"]),
            face("pen", "Pen Face", "script", "pen", "start", SCRIPT, ["PenFace-Regular.ttf"]),
            face("ink", "Ink Face", "script", "pen", "start", SCRIPT, ["InkFace-Regular.ttf"])]}, open(out, "w"))
PY
python3 - "$T/type-cands.json" <<'PY'
import json, sys
json.dump({"languages": ["en"], "sample": {"name": "Example Studio", "tagline": "Portraits that feel like you", "about": "We photograph families the way they are, laughing and a little messy."}}, open(sys.argv[1], "w"))
PY
typage() { ASGARD_FACES="$T/faces.json" ASGARD_FONTS_BASE="file://$TLIB" ASGARD_FONTS_DIR="$TDL" "$BRAND" type-page "$@" >"$C.tp.out" 2>&1; echo $? >"$C.tp.code"; }
# shellcheck disable=SC2329
tpcode() { [ "$(cat "$C.tp.code")" = "$1" ]; }
typage "$C"
check "type-page without a candidates file is refused" tpcode 2
typage "$C" "$T/type-cands.json"
check "with nothing saved, type-page builds the first page: the taste page" tpcode 0
TASTE="$CH/type-taste.html"
check "which is written in the choices folder, ignored by git" test -f "$TASTE"
check "and says which page it is" says "$C.tp.out" "taste"
check "the taste page passes the page check: every face loads, every option changes it" check_page "$TASTE"
check "every direction has its own card, with its name and what it feels like" \
  fx page "$TASTE" 'all(x in html for x in ("Clean sans", "Plain and neutral.", "Book serif", "Warm and classic.", "Pen script", "Written by hand."))'
check "only the faces to start with are on it: width before depth" \
  fx page "$TASTE" 'sorted(f["id"] for f in d["faces"]) == ["bold", "ink", "pen", "plain", "round", "slant"]'
check "one card is shown at a time" fx browse "$TASTE" 'Array.from(document.querySelectorAll("[data-card]")).filter(c => getComputedStyle(c).display !== "none").length === 1'
check "a face is shown in her own words, in its own font" fx page "$TASTE" '"Portraits that feel like you" in html and html.count("data:font/woff2;base64") >= 6'
check "the faces are subset to the words shown, so the page stays small" fx page "$TASTE" 'len(html) < 400000'
check "so the page fetches nothing" fx page "$TASTE" '"src=\"http" not in html and "url(http" not in html'
check "a face's facts are read from its file: the face with no italic is shown without one" \
  fx page "$TASTE" 'all(f["italic"] is False for f in d["faces"] if f["id"] == "plain") and all(f["italic"] is True for f in d["faces"] if f["id"] == "slant")'
check "what she likes is gathered as she chooses" \
  fx browse "$TASTE" '(() => { document.querySelector("input[name=like-clean][value=plain]").click(); document.querySelector("input[name=like-book][value=both]").click(); const r = window.__choiceResult(); return r.likes.join() === "plain,slant,bold" && r.directions.join() === "clean,book"; })()'
check "and shown in a strip that is always on the page" \
  fx browse "$TASTE" '(() => { document.querySelector("input[name=like-pen][value=ink]").click(); return document.getElementById("favs").textContent.includes("Ink Face"); })()'
check "nothing liked gives an empty result" fx browse "$TASTE" 'window.__choiceResult().likes.length === 0'
typage "$C" "$T/type-cands.json" --stage depth
check "the depth page needs the taste saved first" tpcode 2
check "and says what to do" says "$C.tp.out" "taste"
printf '{"step": "type-taste", "choice": {"like-clean": "plain", "like-book": "both", "like-pen": "neither"}, "reason": "Calm and warm", "result": {"likes": ["plain", "slant", "bold"], "directions": ["clean", "book"]}}' >"$CH/type-taste.json"
typage "$C" "$T/type-cands.json"
DEPTH="$CH/type-depth.html"
check "with the taste saved, type-page builds the depth page" tpcode 0
check "which says so" says "$C.tp.out" "depth"
check "the depth page passes the page check" check_page "$DEPTH"
check "it opens only the directions she liked" fx page "$DEPTH" 'sorted(x["id"] for x in d["directions"]) == ["book", "clean"]'
check "and offers the faces held back there: the held-back face of the liked direction" \
  fx page "$DEPTH" '[f["id"] for f in d["faces"] if f["tier"] == "deeper"] == ["soft"]'
check "but none of the direction she did not like" fx page "$DEPTH" 'not any(f["id"] in ("pen", "ink") for f in d["faces"])'
check "her favourites so far are kept: the faces she liked are on the page" \
  fx page "$DEPTH" 'all(i in [f["id"] for f in d["faces"]] for i in ("plain", "slant", "bold"))'
check "a face chosen in depth joins her favourites" \
  fx browse "$DEPTH" '(() => { document.querySelector("input[name=more-book][value=soft]").click(); return window.__choiceResult().favourites.join() === "plain,slant,bold,soft"; })()'
printf '{"step": "type-depth", "choice": {"more-book": "soft"}, "reason": "Softer", "result": {"favourites": ["plain", "slant", "bold", "soft"]}}' >"$CH/type-depth.json"
typage "$C" "$T/type-cands.json"
ROLES="$CH/type.html"
check "with the depth saved, type-page builds the roles page" tpcode 0
check "which says so" says "$C.tp.out" "roles"
check "the roles page passes the page check" check_page "$ROLES"
check "every role has its own card, with its job, where it appears and how often it is seen" \
  fx page "$ROLES" 'all(x in html for x in ("name in the logo", "The few big words", "Section titles", "Everything people read", "Buttons, labels"))'
check "a role is offered her favourites that suit it: the script face she did not like is not offered" \
  fx page "$ROLES" 'sorted(f["id"] for f in d["roleFaces"]["wordmark"]) == sorted(set(f["id"] for f in d["roleFaces"]["wordmark"]))'
check "the body is offered the faces that suit it" fx page "$ROLES" '"plain" in [f["id"] for f in d["roleFaces"]["body"]] and "pen" not in [f["id"] for f in d["roleFaces"]["body"]]'
check "a role none of her favourites suit says so, and offers faces that do" \
  fx page "$ROLES" '"of your favourites suit this role" in html and len(d["roleFaces"]["wordmark"]) >= 1'
check "a face without the italic the body needs says so, in words" \
  fx browse "$ROLES" '(() => { document.querySelector("input[name=type-body][value=plain]").click(); return document.getElementById("warnings").textContent.includes("Plain Face has no italic"); })()'
check "and the face that has it does not" \
  fx browse "$ROLES" '(() => { document.querySelector("input[name=type-body][value=slant]").click(); return !document.getElementById("warnings").textContent.includes("no italic"); })()'
check "the final choice names each role's family, licence and files" \
  fx browse "$ROLES" '(() => { document.querySelector("input[name=type-body][value=slant]").click(); const b = window.__choiceResult().fonts.body; return b.family === "Slant Face" && b.licence === "OFL-1.1" && b.files.length === 2; })()'
check "the pages build strictly with the docs and the names check passes" builds "$C"
check "and the names check" names_pass "$C"
python3 - "$T/faces.json" "$T/faces-bad.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["faces"][0]["files"][0]["sha256"] = "0" * 64; json.dump(d, open(sys.argv[2], "w"))
PY
ASGARD_FACES="$T/faces-bad.json" ASGARD_FONTS_BASE="file://$TLIB" ASGARD_FONTS_DIR="$T/typedl2" "$BRAND" type-page "$C" "$T/type-cands.json" --stage taste >"$C.tp.out" 2>&1; echo $? >"$C.tp.code"
check "a face whose file does not match its pinned hash is refused" tpcode 2
check "and named" says "$C.tp.out" "Plain Face"
use typage2; CH="$C/$ID_REL/choices"; mkdir -p "$CH"
printf '{"step": "type", "choice": {"type-body": "slant"}, "reason": "Warm", "result": {"fonts": {}}}' >"$CH/type.json"; typage "$C" "$T/type-cands.json" --stage roles
check "a saved final choice is restored on the roles page" check_page "$CH/type.html"
check "and says so" says "$C.cp.out" "reopens on the saved choice"

# The pin script (design system tasks DS-T15): the curated list is made from a source list by fetching and hashing the files.
python3 - "$T/pin-source.json" "$T/pin-listing.json" "$TLIB" <<'PY'
import json, os, sys
src, listing, lib = sys.argv[1:]
json.dump({"directions": [{"id": "clean", "name": "Clean", "text": "Plain.", "voices": ["calm"], "suits": ["body"],
                           "start": [["plainface", "Plain Face", "A plain face."]],
                           "deeper": [["slantface", "Slant Face", "Two files."], ["ghostface", "Ghost Face", "Not in the library."]]}]}, open(src, "w"))
json.dump({d: [[n, os.path.getsize(os.path.join(lib, d, n))] for n in sorted(os.listdir(os.path.join(lib, d))) if n.endswith(".ttf")]
           for d in os.listdir(lib)}, open(listing, "w"))
PY
pin() { ASGARD_FONTS_BASE="file://$TLIB" "$PY" -I "$HERE/../brand/pin_faces.py" --ref 0000000000000000000000000000000000000000 --listing "$T/pin-listing.json" "$@" >"$T/pin.out" 2>&1; echo $? >"$T/pin.code"; }
# shellcheck disable=SC2329
pincode() { [ "$(cat "$T/pin.code")" = "$1" ]; }
pin "$T/pin-source.json" "$T/pin-out.json"
check "the pin script writes the list from the source" pincode 0
check "with the directions and each face's tier" fx json "$T/pin-out.json" 'd["directions"][0]["id"] == "clean" and [(f["id"], f["tier"]) for f in d["faces"]] == [("plainface", "start"), ("slantface", "deeper")]'
check "and the hash of each file as the library has it" \
  fx json "$T/pin-out.json" '__import__("hashlib").sha256(open(__import__("os").environ["TLIBDIR"] + "/plainface/PlainFace-Regular.ttf", "rb").read()).hexdigest() == d["faces"][0]["files"][0]["sha256"]'
check "a face that is not in the library is left out, and said so" says "$T/pin.out" "Ghost Face: not in the library"
pin --max-files 1 "$T/pin-source.json" "$T/pin-out2.json"
check "a face with more files than allowed is left out, and said so" says "$T/pin.out" "Slant Face: 2 files"
check "the review table shows the weights, the italic and the glyphs a language lacks (the fixture lacks the typographic ones)" says_all "$T/pin.out" "| clean | start | Plain Face | 1 |" "| 400 | no |" "en:-"
check "a face with no italic is shown so in the review table" says "$T/pin.out" "| 1 | .* | 400 | no |"

# The foundations page (design system tasks DS-T16): step 6e, one foundation at a time, each shown and not described.
use found; CH="$C/$ID_REL/choices"; mkdir -p "$CH"; FP="$CH/foundations.html"
foundpage() { "$BRAND" foundations-page "$@" >"$C.fp.out" 2>&1; echo $? >"$C.fp.code"; }
# shellcheck disable=SC2329
fpcode() { [ "$(cat "$C.fp.code")" = "$1" ]; }
foundpage "$C"
check "foundations-page builds the page with its own default candidates" fpcode 0
check "in the choices folder, ignored by git" test -f "$FP"
check "the page passes the page check: every candidate of every foundation changes it, light and dark" check_page "$FP"
check "each foundation has its own card, with why it matters in plain words" \
  fx page "$FP" 'all(x in html for x in ("Body size", "Type scale", "Line height", "Spacing", "Corners", "Depth", "Motion", "Focus", "Touch size", "Breakpoints"))'
check "and the cards are shown one at a time" fx browse "$FP" 'Array.from(document.querySelectorAll("[data-card]")).filter(c => getComputedStyle(c).display !== "none").length === 1'
check "every candidate is shown on the page at once, not described: the body size changes the text" \
  fx browse "$FP" '(() => { const s = () => getComputedStyle(document.querySelector("#sample-body")).fontSize; const a = s(); document.querySelector("input[name=f-base][value=\"18\"]").click(); return a !== s(); })()'
check "the corners change the card and the button" \
  fx browse "$FP" '(() => { const r = () => getComputedStyle(document.querySelector("#sample-card")).borderTopLeftRadius; const a = r(); document.querySelector("input[name=f-radius][value=round]").click(); return a !== r(); })()'
check "motion is played, and the page says what it does in numbers" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-motion][value=lively]").click(); return document.getElementById("motion-words").textContent.includes("320 ms") && document.querySelector("#motion-ball").getAnimations().length > 0; })()'
check "where the device asks for reduced motion, it is still" fx page "$FP" '"prefers-reduced-motion: reduce" in html'
check "the breakpoints are a ruler with the usual devices marked and a width slider" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-breakpoints][value=photo]").click(); return document.getElementById("ruler").textContent.includes("1440") && document.getElementById("width-slider").type === "range"; })()'
check "a look sets every foundation at once" \
  fx browse "$FP" '(() => { document.querySelector("input[name=look][value=playful]").click(); return document.querySelector("input[name=f-radius][value=round]").checked && document.querySelector("input[name=f-motion][value=lively]").checked; })()'
check "the final choice has the keys of the token contract" \
  fx browse "$FP" '(() => { const r = window.__choiceResult(); return Array.isArray(r.space) && r.radius.button !== undefined && r.elevation.card !== undefined && r.motion.duration > 0 && r.focus.width >= 2 && r.target >= 24 && Array.isArray(r.breakpoints) && r.type.scale.sizes.body >= 16 && r.type.scale.lineHeight.body >= 1.5; })()'
check "the type scale sizes follow the base and the ratio" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-base][value=\"16\"]").click(); document.querySelector("input[name=f-ratio][value=\"1.25\"]").click(); const s = window.__choiceResult().type.scale.sizes; return s.body === 16 && s.h3 === 20 && s.h2 === 25; })()'
printf '{"foundations": {"base": [{"id": "15", "name": "15 px", "note": "Too small.", "v": 15}, {"id": "16", "name": "16 px", "note": "The usual.", "v": 16}]}}' >"$T/found-cands.json"; foundpage "$C" "$T/found-cands.json"
check "candidates of the agent replace the defaults of a foundation" fpcode 0
check "a body size under the minimum is warned about, in words" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-base][value=\"15\"]").click(); return document.getElementById("warnings").textContent.includes("body text is 15 px, under the minimum 16"); })()'
check "and she may keep it: the result says what she kept" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-base][value=\"15\"]").click(); document.querySelector("#warnings input[type=checkbox]").click(); return window.__choiceResult().kept.includes("type:body:size"); })()'
printf '{"step": "palette", "choice": {}, "reason": "", "result": {"light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "text": "#1A1A1A", "muted": "#555555", "accent": "#E8E8E8", "on-accent": "#111111"}, "dark": {"bg": "#121212", "surface": "#1E1E1E", "text": "#EDEDED", "muted": "#B0B0B0", "accent": "#6EA8FE", "on-accent": "#121212"}}}' >"$CH/palette.json"; foundpage "$C"
check "the saved palette is used: a focus ring too faint against it is warned about" \
  fx browse "$FP" '(() => { document.querySelector("input[name=f-focus][value=accent]").click(); return document.getElementById("warnings").textContent.includes("light: the focus colour accent on bg"); })()'
check "the pages build strictly and the names check passes" builds "$C"
check "and the names check" names_pass "$C"
printf '{"step": "foundations", "choice": {"f-radius": "round", "f-motion": "lively"}, "reason": "Playful"}' >"$CH/foundations.json"; foundpage "$C"
check "a saved choice is restored" check_page "$FP"
check "and says so" says "$C.cp.out" "reopens on the saved choice"

# The playground (design system tasks DS-T11): the last look at everything together, then the export that brand.py validates.
play() { ASGARD_FACES="$T/faces.json" ASGARD_FONTS_BASE="file://$TLIB" ASGARD_FONTS_DIR="$TDL" "$BRAND" playground "$@" >"$C.pl.out" 2>&1; echo $? >"$C.pl.code"; }
# shellcheck disable=SC2329
plcode() { [ "$(cat "$C.pl.code")" = "$1" ]; }
use playbare; play "$C"
check "the playground without a saved palette or a palette in the tokens is refused" plcode 2
check "and says what to do first" says "$C.pl.out" "palette"
use play; CH="$C/$ID_REL/choices"; TK="$C/$ID_REL/tokens.json"; PGP="$CH/playground.html"; mkdir -p "$CH"; fx draw mark "$SRC/logo.png"
python3 - "$CH" <<'PY'
import json, sys
ch = sys.argv[1]
good = {"light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "border": "#DDDDDD", "text": "#1A1A1A", "muted": "#555555", "accent": "#0B5FCC", "accent-text": "#0B5FCC", "on-accent": "#FFFFFF", "ok": "#1B6E20", "warn": "#8A5A00", "crit": "#B00020"},
        "dark": {"bg": "#121212", "surface": "#1E1E1E", "border": "#333333", "text": "#EDEDED", "muted": "#B0B0B0", "accent": "#6EA8FE", "accent-text": "#6EA8FE", "on-accent": "#121212", "ok": "#81C784", "warn": "#FFB74D", "crit": "#EF9A9A"}}
json.dump({"step": "palette", "choice": {"preset": "calm"}, "reason": "Calm", "result": {"preset": "calm", **good, "kept": []}}, open(ch + "/palette.json", "w"))
fonts = {r: {"id": i} for r, i in (("wordmark", "pen"), ("display", "slant"), ("heading", "slant"), ("body", "slant"), ("ui", "plain"))}
json.dump({"step": "type-depth", "choice": {}, "reason": "", "result": {"favourites": ["plain", "slant", "bold", "pen"]}}, open(ch + "/type-depth.json", "w"))
json.dump({"step": "type", "choice": {}, "reason": "", "result": {"fonts": fonts, "kept": []}}, open(ch + "/type.json", "w"))
PY
play "$C"
check "with the choices saved, the playground is built" plcode 0
check "in the choices folder, ignored by git" test -f "$PGP"
check "the page passes the page check: every option of every tab changes it, in both modes" check_page "$PGP"
check "it has a tab for the palette, the type, the foundations, the components and the checks" \
  fx page "$PGP" 'all(x in html for x in ("data-tab=\"palette\"", "data-tab=\"type\"", "data-tab=\"foundations\"", "data-tab=\"components\"", "data-tab=\"checks\""))'
check "the sample site has a navigation, a hero, a grid of images, an about block, service cards, a contact block and a footer" \
  fx page "$PGP" 'all(("id=\"site-" + s + "\"") in html for s in ("nav", "hero", "grid", "about", "cards", "contact", "footer"))'
check "it is painted only from tokens: no colour is written in the sample" \
  fx browse "$PGP" '!/#[0-9a-fA-F]{6}/.test(document.getElementById("site").outerHTML.replace(/<svg[\s\S]*?<\/svg>/g, ""))'
check "the faces are embedded and no address is loaded" fx page "$PGP" 'html.count("data:font/woff2;base64") >= 4 and "src=\"http" not in html and "url(http" not in html'
check "it opens on her saved choices: the palette is the saved one" \
  fx browse "$PGP" 'window.__choiceResult().tokens.light.accent === "#0B5FCC" && window.__choiceResult().tokens.dark.bg === "#121212"'
check "and the saved typefaces: the body is the one she chose" \
  fx browse "$PGP" 'window.__choiceResult().tokens.type.fonts.body.family === "Slant Face" && window.__choiceResult().tokens.type.fonts.wordmark.family === "Pen Face"'
check "and the foundations of the tokens" fx browse "$PGP" 'window.__choiceResult().tokens.target === 44 && window.__choiceResult().tokens.space.length === 7'
check "the page's rules give brand.py's ratio and result for every contrast pair of the palette" \
  fx browse "$PGP" 'window.__rules && window.__data().expected.every(r => { const x = window.__rules.rows(window.__data().palette.light, window.__data().palette.dark).find(y => y.mode === r.mode && y.fg === r.fg && y.bg === r.bg); return x && x.result === r.result && Math.abs(x.ratio - r.ratio) < 0.001; })'
check "the checks tab lists every check with its id" fx browse "$PGP" 'window.__checks().some(c => c.id === "contrast:light:text/bg") && window.__checks().some(c => c.id === "type:body:italic") && window.__checks().some(c => c.id === "focus:light:bg")'
check "a change that breaks a rule shows it open: a muted colour too faint" \
  fx browse "$PGP" '(() => { const f = document.querySelector("input[data-choice-field=custom-muted]"); f.value = "#BBBBBB | #666666"; f.dispatchEvent(new Event("input", {bubbles: true})); return window.__checks().some(c => c.id === "contrast:light:muted/bg" && !c.pass && !c.kept); })()'
check "and she may keep it, with a reason, which becomes an accepted exception" \
  fx browse "$PGP" '(() => { const f = document.querySelector("input[data-choice-field=custom-muted]"); f.value = "#BBBBBB | #666666"; f.dispatchEvent(new Event("input", {bubbles: true})); window.__keep("contrast:light:muted/bg", "Captions only."); const r = window.__choiceResult(); return r.kept.some(k => k.check === "contrast:light:muted/bg" && k.reason === "Captions only." && k.value === "#BBBBBB/#FFFFFF"); })()'
check "a face without the italic the body needs is an open check" \
  fx browse "$PGP" '(() => { document.querySelector("input[name=t-body][value=plain]").click(); return window.__checks().some(c => c.id === "type:body:italic" && !c.pass); })()'
check "a component variant that needs more of the palette is checked too" \
  fx browse "$PGP" '(() => { document.querySelector("input[name=c-link][value=colour]").click(); return window.__checks().some(c => c.id.startsWith("components:link:")); })()'
check "the export has the token file's keys" \
  fx browse "$PGP" '(() => { const t = window.__choiceResult().tokens; return t.light.bg && t.type.scale.sizes.body >= 16 && Array.isArray(t.breakpoints) && t.radius.button !== undefined && t.components.button && Array.isArray(t.accepted); })()'
check "the pages build strictly and the names check passes" builds "$C"
check "and the names check" names_pass "$C"
printf '{"step": "playground", "choice": {"c-button": "soft"}, "reason": "Soft", "result": {}}' >"$CH/playground.json"; play "$C"
check "a saved choice is restored" check_page "$PGP"
check "and says so" says "$C.cp.out" "reopens on the saved choice"
# Applying: brand.py validates the export before anything is written.
ALIB="$T/applib"; ALLT="$(python3 -c 'print(",".join("%x" % c for c in list(range(0x20, 0x7f)) + [0x2019, 0x201c, 0x201d, 0x2013, 0x2014, 0x2026, 0x20ac]))')"
fx face "$ALIB/plainface" "Plain Face" "PlainFace-Regular.ttf" "$ALLT" 400 0 - ofl
fx face "$ALIB/slantface" "Slant Face" "SlantFace[wght].ttf" "$ALLT" 400 0 wght ofl
fx face "$ALIB/slantface" "Slant Face" "SlantFace-Italic[wght].ttf" "$ALLT" 400 1 wght ofl
applyp() { ASGARD_FONTS_DIR="$ALIB" "$BRAND" playground-apply "$@" >"$C.ap.out" 2>&1; echo $? >"$C.ap.code"; }
# shellcheck disable=SC2329
apcode() { [ "$(cat "$C.ap.code")" = "$1" ]; }
use apply0; applyp "$C" --by "Alex"
check "playground-apply with nothing saved is refused" apcode 2
use apply1; CH="$C/$ID_REL/choices"; TK="$C/$ID_REL/tokens.json"; mkdir -p "$CH"; fx draw mark "$SRC/logo.png"
python3 - "$CH" "$TK" <<'PY'
import json, sys
ch, tk = sys.argv[1:]
t = json.load(open(tk))
good = {"light": {"bg": "#FFFFFF", "surface": "#F5F5F5", "border": "#DDDDDD", "text": "#1A1A1A", "muted": "#555555", "accent": "#0B5FCC", "accent-text": "#0B5FCC", "on-accent": "#FFFFFF", "ok": "#1B6E20", "warn": "#8A5A00", "crit": "#B00020"},
        "dark": {"bg": "#121212", "surface": "#1E1E1E", "border": "#333333", "text": "#EDEDED", "muted": "#B0B0B0", "accent": "#6EA8FE", "accent-text": "#6EA8FE", "on-accent": "#121212", "ok": "#81C784", "warn": "#FFB74D", "crit": "#EF9A9A"}}
fonts = {r: {"id": i, "family": f, "licence": "OFL-1.1", "source": "https://example.org/" + i, "files": files, "weights": [{"min": 400, "max": 400}], "dir": i + "face"}
         for r, i, f, files in (("wordmark", "plain", "Plain Face", ["PlainFace-Regular.ttf"]), ("display", "plain", "Plain Face", ["PlainFace-Regular.ttf"]),
                                ("heading", "plain", "Plain Face", ["PlainFace-Regular.ttf"]), ("body", "slant", "Slant Face", ["SlantFace[wght].ttf", "SlantFace-Italic[wght].ttf"]),
                                ("ui", "plain", "Plain Face", ["PlainFace-Regular.ttf"]))}
t.update({"light": good["light"], "dark": good["dark"]})
t["languages"] = ["en"]
tokens = {**t, "type": {"fonts": {r: {"family": v["family"], "fallback": "sans-serif", "weights": [400], "files": "fonts/" + v["dir"], "licence": v["licence"], "source": v["source"]} for r, v in fonts.items()}, "scale": t["type"]["scale"]}, "accepted": []}
copy = [{"dir": "plainface", "files": ["PlainFace-Regular.ttf"]}, {"dir": "slantface", "files": ["SlantFace[wght].ttf", "SlantFace-Italic[wght].ttf"]}]
json.dump({"step": "playground", "choice": {}, "reason": "Done", "result": {"tokens": tokens, "kept": [], "copy": copy}}, open(ch + "/playground.json", "w"))
PY
sumtk="$(sha256sum "$TK")"; applyp "$C" --by "Alex"
check "playground-apply writes the export into tokens.json when brand.py accepts it" apcode 0
check "tokens.json holds the new palette" fx json "$TK" 'd["light"]["accent"] == "#0B5FCC" and d["dark"]["bg"] == "#121212"'
check "and the typefaces, with their folders and licences" fx json "$TK" 'd["type"]["fonts"]["body"]["family"] == "Slant Face" and d["type"]["fonts"]["body"]["files"] == "fonts/slantface"'
check "the shipped font files are copied beside the identity, with their licence file" test -f "$C/$ID_REL/fonts/slantface/SlantFace[wght].ttf" -a -f "$C/$ID_REL/fonts/slantface/OFL.txt"
check "the generated CSS and web fonts are made again" says_all "$C.ap.out" "tokens.css" "web"
check "and the company's checks pass on the result" brand_check_passes "$C"
check "the apply says what it did" [ "$(sha256sum "$TK")" != "$sumtk" ]
python3 - "$CH" "$TK" <<'PY'
import json, sys
ch, tk = sys.argv[1:]
d = json.load(open(ch + "/playground.json")); d["result"]["tokens"]["light"]["muted"] = "#BBBBBB"; json.dump(d, open(ch + "/playground.json", "w"))
PY
sumbefore="$(sha256sum "$TK")"; applyp "$C" --by "Alex"
check "an export that fails a rule she did not keep is refused, with code 1" apcode 1
check "and names the failing pair" says "$C.ap.out" "muted on bg"
check "and tokens.json is left as it was" [ "$(sha256sum "$TK")" = "$sumbefore" ]
python3 - "$CH" <<'PY'
import json, sys
ch = sys.argv[1]
d = json.load(open(ch + "/playground.json")); d["result"]["kept"] = [{"check": "contrast:light:muted/bg", "value": "#BBBBBB/#FFFFFF", "reason": "Captions only."}, {"check": "contrast:light:muted/surface", "value": "#BBBBBB/#F5F5F5", "reason": "Captions only."}]
json.dump(d, open(ch + "/playground.json", "w"))
PY
applyp "$C" --by "Alex"
check "the same export with the failures kept, with her reason, is applied" apcode 0
check "they become accepted exceptions with who and when" \
  fx json "$TK" 'any(a["check"] == "contrast:light:muted/bg" and a["reason"] == "Captions only." and a["by"] == "Alex" and len(a["date"]) == 10 for a in d["accepted"])'
check "and the company's checks pass, the exceptions reported as accepted" brand_check_passes "$C"
applyp "$C"
check "playground-apply needs to know who accepts the exceptions" apcode 2

# The reference (design system tasks DS-T13): the design system as products build it, generated from the tokens.
use ref; REFD="$C/$ID_REL/reference"; TK="$C/$ID_REL/tokens.json"; fx palette "$TK"; fx font "$TK" "$C/$ID_REL/fonts/test" "Test Serif" ttf; fx draw mark "$SRC/logo.png"
(cd "$C" && "$PY" -I .ouroboric/checks/brand.py tokens --write >/dev/null); logo
refp() { "$BRAND" reference "$C" >"$C.ref.out" 2>&1; echo $? >"$C.ref.code"; }
# shellcheck disable=SC2329
refcode() { [ "$(cat "$C.ref.code")" = "$1" ]; }
# shellcheck disable=SC2329
only_variables() { ! grep -vE '^\s*(/\*|\*)' "$1" | grep -qiE '#[0-9a-f]{3,8}\b|rgba?\(|hsla?\(|font-family: *[^v ]|font-family: *"'; }
# shellcheck disable=SC2329
sizes_are_recipe_constants() { ! grep -vE '^\s*(/\*|\*)' "$1" | grep -oE '[0-9]+(\.[0-9]+)?px' | grep -vxE '0px|1px|1\.5px|3px|22px' | grep -q .; }
# shellcheck disable=SC2329
vars_are_defined() { python3 - "$1" "$2" <<'PY'
import re, sys
css, tokens = (open(p, encoding="utf-8").read() for p in sys.argv[1:])
used = set(re.findall(r"var\((--[a-z0-9-]+)", css)); local = set(re.findall(r"(--[a-z0-9-]+)\s*:", css)); defined = set(re.findall(r"(--[a-z0-9-]+)\s*:", tokens))
missing = sorted(used - defined - local); print("missing:", missing) if missing else None; sys.exit(1 if missing else 0)
PY
}
refp
check "reference writes the component stylesheet, the page and the screenshots" refcode 0
check "components.css holds no literal colour and no font name: only variables of tokens.css" only_variables "$REFD/components.css"
check "and no size but the recipes' own constants (a 1 px border, a 3 px bar, a 22 px icon)" sizes_are_recipe_constants "$REFD/components.css"
check "every variable it uses is one that tokens.css defines" vars_are_defined "$REFD/components.css" "$C/$ID_REL/tokens.css"
for v in 'data-variant="filled"' 'data-variant="outlined"' 'data-variant="soft"' 'data-variant="underlined"' 'data-variant="colour"' 'data-variant="bordered"' 'data-variant="raised"' 'data-variant="tint"' 'data-variant="bar"' 'data-variant="centre"' 'data-variant="framed"' 'data-variant="rounded"'; do
  check "components.css has the variant $v" says "$REFD/components.css" "$v"
done
check "and each component's states: hover, active, focus-visible, disabled" says_all "$REFD/components.css" ":hover" ":active" ":focus-visible" '\[aria-disabled="true"\]'
check "the stylesheet says it is generated and must not be edited" says "$REFD/components.css" "Generated from tokens.json"
check "it loads nothing from the network" lacks_text "$REFD/playground.html" 'src="http'
check "it has no way to save: the choice is made, the page is for looking" lacks_text "$REFD/playground.html" "Save my choice"
check "it shows every variant of every component" fx browse "$REFD/playground.html" 'document.querySelectorAll("[data-variant]").length >= 20'
check "its fonts load" fx browse "$REFD/playground.html" 'document.fonts.ready.then(() => Array.from(document.fonts).every(f => f.status === "loaded"))'
for m in light dark; do for w in 390 820 1280; do
  check "the screenshot $m at $w pixels is there and has something drawn" fx ink "$REFD/screenshots/$m-$w.png"
done; done
check "the 1280 screenshot is 1280 pixels wide" fx size "$REFD/screenshots/light-1280.png" 1280x"$(python3 -c "from PIL import Image; print(Image.open('$REFD/screenshots/light-1280.png').size[1])")"
check "the generated files name no tool" names_pass "$C"
check "the pages build strictly with the reference in the docs" builds "$C"
brand_ref() { (cd "$C" && "$PY" -I .ouroboric/checks/brand.py reference-fresh >"$C.rf.out" 2>&1); echo $? >"$C.rf.code"; }
# shellcheck disable=SC2329
rfcode() { [ "$(cat "$C.rf.code")" = "$1" ]; }
brand_ref
check "brand.py finds the reference fresh right after it is made" rfcode 0
sums="$(cd "$REFD" && sha256sum components.css playground.html)"; refp
check "a second run writes byte-identical stylesheet and page" [ "$(cd "$REFD" && sha256sum components.css playground.html)" = "$sums" ]
python3 - "$TK" <<'PY'
import json, sys
t = json.load(open(sys.argv[1])); t["radius"]["lg"] = 12; json.dump(t, open(sys.argv[1], "w"), indent=2)
PY
(cd "$C" && "$PY" -I .ouroboric/checks/brand.py tokens --write >/dev/null); brand_ref
check "when a token changes, brand.py reports the reference stale" rfcode 1
check "and says to make it again" says "$C.rf.out" "reference: out of date with its inputs"
refp; brand_ref
check "making it again makes it fresh" rfcode 0
check "the company's own check runs the reference freshness too" says "$C.rf.out" "reference"
use refnone; (cd "$C" && python3 .ouroboric/checks/brand.py reference-fresh >"$C.rf.out" 2>&1); echo $? >"$C.rf.code"
check "a company with no reference yet passes: there is nothing to compare" rfcode 0
check "reference refuses a company with no palette, with code 2" [ "$("$BRAND" reference "$C" >/dev/null 2>&1; echo $?)" -eq 2 ]

echo "end of suite: every check ran"
exit "$fail"
