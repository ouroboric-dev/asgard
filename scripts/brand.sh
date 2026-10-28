#!/usr/bin/env bash
# The brand tools of step 6 of the company kickstart (brand tools spec §3.2).
#   brand.sh setup                 install the pinned tools into the cache; uses the network
#   brand.sh fonts DIR CANDIDATES  fetch candidate typefaces and their licences, write their facts (uses the network
#                                  for files not yet downloaded; the facts go to DIR/docs/7-branding/identity/choices/)
#   brand.sh palette DIR ROUND     check every preset of a palette round with the company's contrast rules
#   brand.sh serve DIR [--port N]   serve the choice pages on 127.0.0.1 and save the founder's choices into DIR
#   brand.sh check-page DIR PAGE     open a choice page in the headless browser: faces load, every option changes the page
#   brand.sh logo-prep [--mark] DIR IMAGE   cut out, flatten and enlarge the founder's concept
#   brand.sh logo-proposals DIR CANDIDATES [--choose ALT[:FACE]]   the logo review page; the chosen design as source PNGs
#   brand.sh logo DIR              trace, recolour, derive, export and check the logo of the company in DIR
#   brand.sh board [--check] DIR   write DIR/docs/7-branding/identity/board.md; --check fails when it is stale
# The environment lives in ${XDG_CACHE_HOME:-$HOME/.cache}/asgard/brand/<key>, where <key> is a hash of
# brand/requirements.txt and brand/resvg.lock: a pin change makes a new environment. Python packages install from
# wheels with their hashes; the resvg binary is refused when its SHA-256 differs from resvg.lock.
# Exit codes: 0 done, 1 a check failed (board --check), 2 refused (usage, missing setup, an input refused).
# Agent-run.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIB="$HERE/brand"
die() { echo "brand.sh: $*" >&2; exit 2; }

# VTracer 0.6.15 installs on Python 3.14 but crashes when it traces, so the tools use the newest of 3.13 to 3.10.
PY=""
for v in 3.13 3.12 3.11 3.10; do
  if command -v "python$v" >/dev/null; then PY="python$v"; break; fi
done
if [ -z "$PY" ] && command -v python3 >/dev/null &&
  python3 -c 'import sys; sys.exit(0 if (3, 10) <= sys.version_info[:2] <= (3, 13) else 1)'; then PY=python3; fi

key="$({ cat "$LIB/requirements.txt" "$LIB/resvg.lock"; [ -z "$PY" ] || "$PY" -V; } | sha256sum | cut -c1-16)"
ENV="${XDG_CACHE_HOME:-$HOME/.cache}/asgard/brand/$key"

platform() {
  case "$(uname -s)-$(uname -m)" in
    Linux-x86_64) echo linux-x86_64 ;;
    Darwin-arm64) echo macos-aarch64 ;;
    Darwin-x86_64) echo macos-x86_64 ;;
    *) die "no resvg binary for $(uname -s) $(uname -m)" ;;
  esac
}

setup() {
  if [ -f "$ENV/.complete" ]; then echo "brand.sh: the tools are up to date ($ENV)"; return 0; fi
  [ ! -e "$ENV" ] || die "an incomplete environment is in $ENV: remove that folder, then run setup again"
  [ -n "$PY" ] || die "the brand tools need Python 3.10 to 3.13 (VTracer crashes on 3.14); install one of them"
  local work p url sum
  mkdir -p "$(dirname "$ENV")"
  work="$(mktemp -d "$(dirname "$ENV")/.setup.XXXXXX")"
  trap 'rm -rf -- "$work"' RETURN
  p="$(platform)"
  read -r url sum < <(awk -v p="$p" '$1 == p { print $2, $3 }' "$LIB/resvg.lock")
  [ -n "${url:-}" ] || die "resvg.lock has no line for $p"
  mkdir -p "$work/download" "$work/bin"
  curl -fsSL --proto '=https' -o "$work/download/resvg.archive" "$url" || die "could not download $url"
  [ "$(sha256sum "$work/download/resvg.archive" | cut -d' ' -f1)" = "$sum" ] ||
    die "the resvg binary's SHA-256 differs from resvg.lock: refused"
  case "$url" in
    *.tar.gz) tar -xzf "$work/download/resvg.archive" -C "$work/bin" resvg ;;
    *.zip) python3 -c 'import sys, zipfile; zipfile.ZipFile(sys.argv[1]).extract("resvg", sys.argv[2])' \
      "$work/download/resvg.archive" "$work/bin" ;;
  esac
  chmod +x "$work/bin/resvg"
  "$PY" -m venv "$work/venv"
  "$work/venv/bin/pip" install --quiet --disable-pip-version-check --require-hashes --only-binary :all: \
    -r "$LIB/requirements.txt" || die "pip could not install the pinned packages"
  # A smoke trace: an environment that installs but cannot trace is refused here, not at step 6.
  "$work/venv/bin/python" -I -c '
import sys, vtracer
from PIL import Image, ImageDraw
im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
ImageDraw.Draw(im).ellipse((8, 8, 56, 56), fill=(26, 26, 26, 255))
im.save(sys.argv[1] + "/smoke.png")
vtracer.convert_image_to_svg_py(sys.argv[1] + "/smoke.png", sys.argv[1] + "/smoke.svg", colormode="color")
sys.exit(0 if "<path" in open(sys.argv[1] + "/smoke.svg").read() else 1)' "$work" ||
    die "the tools installed but could not trace a test image with $("$PY" -V)"
  # The headless browser that proves the choice pages. Playwright downloads the Chromium build its release pins, from its
  # own CDN: that download cannot be checked against a hash here, unlike the packages and resvg.
  PLAYWRIGHT_BROWSERS_PATH="$work/browsers" "$work/venv/bin/python" -I -m playwright install --only-shell chromium \
    >/dev/null 2>&1 || die "Playwright could not download its Chromium"
  PLAYWRIGHT_BROWSERS_PATH="$work/browsers" "$work/venv/bin/python" -I -c '
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch()
    page = b.new_page()
    page.set_content("<p>ok</p>")
    assert page.inner_text("p") == "ok"
    b.close()' || die "the headless browser installed but could not open a page"
  mv "$work" "$ENV"
  # The venv's scripts name the folder it was made in; the tools run its python by path, so the move is safe.
  touch "$ENV/.complete"
  echo "brand.sh: the tools are set up ($ENV)"
}

need_env() { [ -f "$ENV/.complete" ] || die "the tools are not set up: run brand.sh setup first"; }

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in
  setup) [ $# -eq 0 ] || die "setup takes no argument"; setup ;;
  logo)
    need_env
    [ $# -eq 1 ] || die "usage: brand.sh logo DIR"
    exec "$ENV/venv/bin/python" -I -B "$LIB/logo.py" --resvg "$ENV/bin/resvg" "$1" ;;
  board)
    need_env
    check=""; [ "${1:-}" = "--check" ] && { check="--check"; shift; }
    [ $# -eq 1 ] || die "usage: brand.sh board [--check] DIR"
    exec "$ENV/venv/bin/python" -I -B "$LIB/board.py" --resvg "$ENV/bin/resvg" $check "$1" ;;
  logo-prep)
    need_env
    [ $# -ge 2 ] && [ $# -le 3 ] || die "usage: brand.sh logo-prep [--mark] DIR IMAGE"
    exec "$ENV/venv/bin/python" -I -B "$LIB/logoprep.py" "$@" ;;
  logo-proposals)
    need_env
    [ $# -eq 2 ] || { [ $# -eq 4 ] && [ "$3" = "--choose" ]; } || die "usage: brand.sh logo-proposals DIR CANDIDATES.json [--choose ALTERNATIVE[:FACE]]"
    exec "$ENV/venv/bin/python" -I -B "$LIB/proposals.py" --resvg "$ENV/bin/resvg" "$@" ;;
  palette-page)
    need_env
    [ $# -eq 1 ] || die "usage: brand.sh palette-page DIR"
    exec "$ENV/venv/bin/python" -I -B "$LIB/palettepage.py" "$@" ;;
  type-page)
    need_env
    [ $# -eq 2 ] || { [ $# -eq 4 ] && [ "$3" = "--stage" ]; } || die "usage: brand.sh type-page DIR CANDIDATES.json [--stage taste|depth|roles]"
    exec "$ENV/venv/bin/python" -I -B "$LIB/typepage.py" "$@" ;;
  foundations-page)
    need_env
    [ $# -ge 1 ] && [ $# -le 2 ] || die "usage: brand.sh foundations-page DIR [CANDIDATES.json]"
    exec "$ENV/venv/bin/python" -I -B "$LIB/foundationspage.py" "$@" ;;
  check-page)
    need_env
    [ $# -eq 2 ] || die "usage: brand.sh check-page DIR PAGE.html"
    exec env PLAYWRIGHT_BROWSERS_PATH="$ENV/browsers" "$ENV/venv/bin/python" -I -B "$LIB/pagecheck.py" "$@" ;;
  serve)
    need_env
    [ $# -ge 1 ] && [ $# -le 3 ] || die "usage: brand.sh serve DIR [--port N]"
    exec "$ENV/venv/bin/python" -I -B "$LIB/serve.py" "$@" ;;
  fonts)
    need_env
    [ $# -eq 2 ] || die "usage: brand.sh fonts DIR CANDIDATES.json"
    exec "$ENV/venv/bin/python" -I -B "$LIB/fonts.py" "$@" ;;
  palette)
    need_env
    [ $# -eq 2 ] || die "usage: brand.sh palette DIR ROUND.json"
    exec "$ENV/venv/bin/python" -I -B "$LIB/palette.py" "$@" ;;
  *) die "usage: brand.sh setup | fonts DIR CANDIDATES.json | palette DIR ROUND.json | palette-page DIR | type-page DIR CANDIDATES.json [--stage S] | foundations-page DIR [CANDIDATES.json] | serve DIR [--port N] | check-page DIR PAGE.html | logo-prep [--mark] DIR IMAGE | logo-proposals DIR CANDIDATES.json [--choose ALT[:FACE]] | logo DIR | board [--check] DIR" ;;
esac
