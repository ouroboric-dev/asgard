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
board_sums() { (cd "$C/$ID_REL" && sha256sum board.md board/*); }
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

exit "$fail"
