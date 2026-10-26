#!/usr/bin/env bash
# Tests for the company template's checks: .ouroboric/checks/run.sh, which the CI runs on every pull request.
#   scripts/tests/company-checks.test.sh   (needs pre-commit, or uvx to fetch it; mkdocs with the Material theme;
#   the network on the first run, for the hooks)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
T="$(mktemp -d)"
trap 'rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
passes() { (cd "$1" && .ouroboric/checks/run.sh) >"$1.out" 2>&1; }
# shellcheck disable=SC2329
fails() { ! passes "$1"; }
# shellcheck disable=SC2329
says() { grep -q -- "$2" "$1.out"; }

# Use pre-commit from PATH, or fetch the pinned one with uvx.
if ! command -v pre-commit >/dev/null; then
  mkdir -p "$T/bin"
  printf '#!/bin/sh\nexec uvx pre-commit==4.6.2 "$@"\n' >"$T/bin/pre-commit"
  chmod +x "$T/bin/pre-commit"
  export PATH="$T/bin:$PATH"
fi

# A company repo: scaffolded, committed. Each case below changes a copy of it.
"$NEW" --name "tali.photo" --date 2026-10-26 "$T/a" >/dev/null 2>&1
git -C "$T/a" init -q -b main
git -C "$T/a" -c user.name=t -c user.email=t@example.com add -A
git -C "$T/a" -c user.name=t -c user.email=t@example.com commit -q -m scaffold
# shellcheck disable=SC2329
case_of() { rm -rf "${T:?}/$1"; cp -R "$T/a" "$T/$1"; }
# shellcheck disable=SC2329
commit() { git -C "$1" -c user.name=t -c user.email=t@example.com add -A &&
  git -C "$1" -c user.name=t -c user.email=t@example.com commit -q -m change; }

check "the scaffold has the CI workflow" [ -f "$T/a/.github/workflows/checks.yml" ]
check "the checks live in .ouroboric/" [ -x "$T/a/.ouroboric/checks/run.sh" ]
check "no lint settings at the root" [ -z "$(find "$T/a" -maxdepth 1 -name '.pre-commit*' -o -maxdepth 1 -name '.markdownlint*' -o -maxdepth 1 -name '.yamllint*')" ]
check "the workflow runs the same checks" grep -q "\.ouroboric/checks/run\.sh" "$T/a/.github/workflows/checks.yml"
check "a fresh scaffold passes every check" passes "$T/a"
"$NEW" --name "Two Hands" --date 2026-10-26 --no-yggdrasil --open-source --founders 2 "$T/b" >/dev/null 2>&1
git -C "$T/b" init -q -b main
commit "$T/b"
check "every add-on passes too" passes "$T/b"

# Front matter.
case_of fm-missing
sed -i '/^status: /d' "$T/fm-missing/docs/1-company/charter.md"; commit "$T/fm-missing"
check "a doc without a status fails" fails "$T/fm-missing"
check "and the failure names the doc and the key" says "$T/fm-missing" "docs/1-company/charter.md: .*status"
case_of fm-status
sed -i 's/^status: draft$/status: done/' "$T/fm-status/docs/1-company/charter.md"; commit "$T/fm-status"
check "a status outside the standard's list fails" fails "$T/fm-status"
case_of fm-date
sed -i 's/^date: 2026-10-26$/date: 2026-13-40/' "$T/fm-date/docs/1-company/roadmap.md"; commit "$T/fm-date"
check "a date that is not a real date fails" fails "$T/fm-date"
case_of fm-style
sed -i 's/^style: direction$/style: poetry/' "$T/fm-style/docs/1-company/charter.md"; commit "$T/fm-style"
check "a style outside the writing styles fails" fails "$T/fm-style"
case_of fm-related
sed -i 's/^related: \[roadmap.md, customers-and-offer.md\]$/related: [roadmap.md, gone.md]/' \
  "$T/fm-related/docs/1-company/charter.md"; commit "$T/fm-related"
check "a related doc that does not exist fails" fails "$T/fm-related"
check "and the failure names it" says "$T/fm-related" "gone.md"
case_of fm-none
printf '# A note\n\nNo front matter.\n' >"$T/fm-none/docs/5-research/2026-10-26-note.md"; commit "$T/fm-none"
check "a doc with no front matter fails" fails "$T/fm-none"

# File names.
case_of undated
printf -- '---\ntitle: Competitors\nstatus: draft\ndate: 2026-10-26\nrelated: []\nstyle: research\n---\n\n# Competitors\n' \
  >"$T/undated/docs/5-research/competitors.md"; commit "$T/undated"
check "an undated research note fails" fails "$T/undated"
case_of dated
printf -- '---\ntitle: Competitors\nstatus: draft\ndate: 2026-10-26\nrelated: []\nstyle: research\n---\n\n# Competitors\n' \
  >"$T/dated/docs/5-research/2026-10-26-competitors.md"; commit "$T/dated"
check "a dated research note passes" passes "$T/dated"

# Links.
case_of link
echo "See [the plan](docs/1-company/plan.md)." >>"$T/link/README.md"; commit "$T/link"
check "a broken link outside docs/ fails" fails "$T/link"
check "and the failure names the file and the link" says "$T/link" "README.md: .*docs/1-company/plan.md"
case_of folder
echo "See [the journal](../6-journal/)." >>"$T/folder/docs/5-research/README.md"; commit "$T/folder"
check "a link to a bare folder in docs/ fails (the pages can't follow it)" fails "$T/folder"

# Names of the tools.
case_of names
echo "Built with Yggdrasil." >>"$T/names/docs/6-journal/README.md"; commit "$T/names"
check "a tool's name outside .ouroboric/ fails" fails "$T/names"
check "and the failure names the file" says "$T/names" "docs/6-journal/README.md"

# Lint.
case_of lint
printf '\n\n\n# Two blank lines above\n' >>"$T/lint/docs/7-branding/README.md"; commit "$T/lint"
check "a Markdown lint error fails" fails "$T/lint"

exit "$fail"
