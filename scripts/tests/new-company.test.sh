#!/usr/bin/env bash
# Tests for new-company.sh: it scaffolds a company umbrella from templates/company.   scripts/tests/new-company.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
T="$(mktemp -d)"
trap 'rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # has and none run through check
has() { [ -f "$1/$2" ]; }
# shellcheck disable=SC2329
none() { ! grep -rq -- "$2" "$1"; }

# The default: core and the Yggdrasil add-on, one founder.
"$NEW" --name "tali.photo" --date 2026-10-26 "$T/a" >"$T/a.out" 2>&1
check "the default scaffold succeeds" [ $? -eq 0 ]
check "it writes the core: charter" has "$T/a" docs/1-company/charter.md
check "it writes the core: customers and offer" has "$T/a" docs/1-company/customers-and-offer.md
check "it writes the core: accounts inventory" has "$T/a" docs/1-company/accounts.md
check "it writes the core: voice guide" has "$T/a" docs/7-branding/voice/README.md
check "it writes the core: design tokens" has "$T/a" docs/7-branding/identity/tokens.json
check "it writes the core: AGENTS.md" has "$T/a" AGENTS.md
check "the Yggdrasil add-on is on by default" has "$T/a" .ouroboric/standards.yaml
check "the open-source add-on is off by default" [ ! -e "$T/a/docs/1-company/legal/licences.md" ]
check "one founder gets no founders' agreement" [ ! -e "$T/a/docs/1-company/founders-agreement.md" ]
check "every placeholder is filled" none "$T/a" "{{"
check "the name is filled in" grep -q "tali.photo" "$T/a/docs/1-company/charter.md"
check "the date is filled in" grep -q "^date: 2026-10-26$" "$T/a/docs/1-company/charter.md"
check "the template's version is recorded" grep -q "^template: " "$T/a/.ouroboric/company.yaml"
check "the add-ons are recorded" grep -q "^addons: \[yggdrasil\]$" "$T/a/.ouroboric/company.yaml"
check "no configuration file at the root" [ ! -e "$T/a/asgard.yaml" ]
# The founder's files never name the factory or its parts; what the factory needs stays in .ouroboric/.
leaks() { grep -rIliE --exclude-dir=.ouroboric "(^|[^.])\b(asgard|yggdrasil|ouroboric|ygg|odin|gungnir|gleipnir|jormungandr|havamal|voluspa|niflheim|helheim|midgard|realm)\b" "$1"; }
check "no file outside .ouroboric/ names the factory (default)" [ -z "$(leaks "$T/a")" ]
check "the tokens are valid JSON" python3 -c "import json,sys; json.load(open(sys.argv[1]))" "$T/a/docs/7-branding/identity/tokens.json"

# Add-ons on and off.
"$NEW" --name "Two Hands" --date 2026-10-26 --no-yggdrasil --open-source --founders 2 "$T/b" >/dev/null 2>&1
check "no Yggdrasil add-on when turned off" [ ! -e "$T/b/.ouroboric/standards.yaml" ]
check "core keeps a ways-of-working page without it" has "$T/b" docs/4-ways-of-working/README.md
check "the open-source add-on when turned on" has "$T/b" docs/1-company/legal/licences.md
check "two founders get a founders' agreement" has "$T/b" docs/1-company/founders-agreement.md
check "the add-ons are recorded in order" grep -q "^addons: \[open-source, founders\]$" "$T/b/.ouroboric/company.yaml"
check "no file outside .ouroboric/ names the factory (every add-on)" [ -z "$(leaks "$T/b")" ]

# Refusals.
mkdir -p "$T/c" && echo x >"$T/c/keep"
"$NEW" --name "x" --date 2026-10-26 "$T/c" >/dev/null 2>&1
check "it refuses a folder that is not empty" [ $? -ne 0 ]
check "and leaves it as it was" [ "$(ls "$T/c")" = keep ]
"$NEW" --date 2026-10-26 "$T/d" >/dev/null 2>&1
check "it refuses a missing name" [ $? -ne 0 ]
"$NEW" --name "x" --date 26-10-2026 "$T/e" >/dev/null 2>&1
check "it refuses a date that is not YYYY-MM-DD" [ $? -ne 0 ]
"$NEW" --name 'a|b' --date 2026-10-26 "$T/f" >/dev/null 2>&1
check "it refuses a name with characters it can't place safely" [ $? -ne 0 ]
"$NEW" --name "x" --date 2026-10-26 --founders 0 "$T/g" >/dev/null 2>&1
check "it refuses zero founders" [ $? -ne 0 ]

exit "$fail"
