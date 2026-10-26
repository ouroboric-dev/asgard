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

exit "$fail"
