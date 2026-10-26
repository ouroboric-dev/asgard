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

key="$(cat "$LIB/requirements.txt" "$LIB/resvg.lock" | sha256sum | cut -c1-16)"
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
  local work p url sum
  rm -rf "$ENV"
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
  python3 -m venv "$work/venv"
  "$work/venv/bin/pip" install --quiet --disable-pip-version-check --require-hashes --only-binary :all: \
    -r "$LIB/requirements.txt" || die "pip could not install the pinned packages"
  rm -rf "$work/download"
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
    exec "$ENV/venv/bin/python" -I "$LIB/logo.py" --resvg "$ENV/bin/resvg" "$1" ;;
  board)
    need_env
    check=""; [ "${1:-}" = "--check" ] && { check="--check"; shift; }
    [ $# -eq 1 ] || die "usage: brand.sh board [--check] DIR"
    exec "$ENV/venv/bin/python" -I "$LIB/board.py" --resvg "$ENV/bin/resvg" $check "$1" ;;
  *) die "usage: brand.sh setup | logo DIR | board [--check] DIR" ;;
esac
