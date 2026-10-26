#!/usr/bin/env bash
# Tests for company-site.sh: it renders a company umbrella's docs as pages, on this machine only.
#   scripts/tests/company-site.test.sh   (needs mkdocs with the Material theme, and curl)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
SITE="$HERE/../company-site.sh"
T="$(mktemp -d)"
pid=""
trap '[ -z "$pid" ] || kill "$pid" 2>/dev/null; rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
hidden() { [ -f "$1" ] && ! sed "s/<!--.*-->//g" "$1" | grep -q "$2"; }
# shellcheck disable=SC2329
homes() { local d; for d in 1-company 4-ways-of-working 5-research 6-journal 7-branding; do
  [ -f "$1/$d/index.html" ] || return 1; done; }
# shellcheck disable=SC2329
tracked() { ! git -C "$1" check-ignore -q "$2"; }
# shellcheck disable=SC2329
local_only() { ! ss -ltnH "sport = :$1" | grep -vq "127.0.0.1:$1"; }

"$NEW" --name "tali.photo" --date 2026-10-26 "$T/a" >/dev/null 2>&1
"$NEW" --name "Two Hands" --date 2026-10-26 --no-yggdrasil --open-source --founders 2 "$T/b" >/dev/null 2>&1
check "the scaffold carries the site's settings in .ouroboric/" [ -f "$T/a/.ouroboric/mkdocs.yml" ]
check "and nothing for the site at the root" [ ! -e "$T/a/mkdocs.yml" ]

# Build: strict, so a broken link or a page left out fails it.
"$SITE" build "$T/a" >"$T/a.out" 2>&1
check "the default scaffold builds with no warnings" [ $? -eq 0 ]
out="$T/a/.ouroboric/site"
check "the docs map is the home page" grep -q "The map" "$out/index.html"
check "the charter is a page" [ -f "$out/1-company/charter/index.html" ]
check "the page carries the company's name" grep -q "tali.photo charter" "$out/1-company/charter/index.html"
check "the guidance comments are not shown" hidden "$out/1-company/charter/index.html" "To write at step 3"
"$SITE" build "$T/b" >/dev/null 2>&1
check "every add-on builds with no warnings" [ $? -eq 0 ]
check "every folder in the map has a home page" homes "$T/b/.ouroboric/site"

# A link the pages can't follow fails the build.
cp -R "$T/a" "$T/broken"
echo "See [the missing page](1-company/missing.md)." >>"$T/broken/docs/6-journal/README.md"
"$SITE" build "$T/broken" >/dev/null 2>&1
check "a link to a missing page fails the build" [ $? -ne 0 ]
cp -R "$T/a" "$T/folder"
echo "See [the company folder](../1-company/)." >>"$T/folder/docs/6-journal/README.md"
"$SITE" build "$T/folder" >/dev/null 2>&1
check "a link to a bare folder fails the build" [ $? -ne 0 ]

# The built pages stay out of the company's history.
git -C "$T/a" init -q
check "the built pages are ignored by git" git -C "$T/a" check-ignore -q .ouroboric/site/index.html
check "the settings are not ignored" tracked "$T/a" .ouroboric/mkdocs.yml

# Serve: on this machine only.
port="$(python3 -c 'import socket; s=socket.socket(); s.bind(("127.0.0.1",0)); print(s.getsockname()[1])')"
"$SITE" serve --port "$port" "$T/a" >"$T/serve.out" 2>&1 &
pid=$!
up=1
for _ in $(seq 1 50); do curl -fsS "http://127.0.0.1:$port/" >/dev/null 2>&1 && { up=0; break; }; sleep 0.2; done
check "it serves the pages on 127.0.0.1" [ "$up" -eq 0 ]
check "and only there" local_only "$port"
kill "$pid" 2>/dev/null; wait "$pid" 2>/dev/null; pid=""

# Refusals.
mkdir -p "$T/c"
"$SITE" build "$T/c" >/dev/null 2>&1
check "it refuses a folder with no site settings" [ $? -ne 0 ]
"$SITE" publish "$T/a" >/dev/null 2>&1
check "it refuses anything but build and serve" [ $? -ne 0 ]
"$SITE" serve --port 80x "$T/a" >/dev/null 2>&1
check "it refuses a port that is not a number" [ $? -ne 0 ]

exit "$fail"
