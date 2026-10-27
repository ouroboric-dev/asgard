#!/usr/bin/env bash
# The brand tools of step 6 of the company kickstart (brand tools spec §3.2).
#   brand.sh setup                 install the pinned tools into the cache; the only command that uses the network
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
  *) die "usage: brand.sh setup | logo DIR | board [--check] DIR" ;;
esac
