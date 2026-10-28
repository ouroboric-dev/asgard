#!/usr/bin/env bash
# Tests for the kickstart guide: docs/3-using/kickstart-guide.md (design system tasks DS-T01). The guide describes the tools as built,
# so every command it names must exist, every command must be named, and it names no company.   scripts/tests/guide.test.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT="$HERE/../.."
GUIDE="$ROOT/docs/3-using/kickstart-guide.md"
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
says() { grep -q -- "$1" "$GUIDE"; }
# shellcheck disable=SC2329
quiet() { ! grep -qiE -- "$1" "$GUIDE"; }
# the commands of brand.sh, from its case list; the checks of brand.py, from its usage text
# shellcheck disable=SC2329 # these run through check
sh_commands() { grep -oE '^  [a-z-]+\)' "$ROOT/scripts/brand.sh" | tr -d ' )' | grep -vE '^(\*)$'; }
# shellcheck disable=SC2329
py_commands() { grep -oE 'brand\.py ([a-z-]+)' "$ROOT/templates/company/core/.ouroboric/checks/brand.py" | awk '{print $2}' | sort -u; }
# shellcheck disable=SC2329
every_sh_command_is_named() {
  local missing=0 c
  while read -r c; do
    grep -q "brand\.sh $c" "$GUIDE" || { echo "not named: brand.sh $c"; missing=1; }
  done < <(sh_commands)
  return "$missing"
}
# shellcheck disable=SC2329
every_named_sh_command_exists() {
  local bad=0 c
  while read -r c; do
    sh_commands | grep -qx "$c" || { echo "no such command: brand.sh $c"; bad=1; }
  done < <(grep -oE 'brand\.sh [a-z-]+' "$GUIDE" | awk '{print $2}' | sort -u)
  return "$bad"
}
# shellcheck disable=SC2329
every_named_py_command_exists() {
  local bad=0 c
  while read -r c; do
    py_commands | grep -qx "$c" || { echo "no such check: brand.py $c"; bad=1; }
  done < <(grep -oE 'brand\.py [a-z-]+' "$GUIDE" | awk '{print $2}' | sort -u)
  return "$bad"
}

check "the guide exists" test -f "$GUIDE"
check "with the front matter of a guide" head -8 "$GUIDE" | grep -q "^style: guide"
for n in 1 2 3 4 5 6 7 8 9; do check "it has a section for step $n" says "^## Step $n\b"; done
for s in a b c d e f g; do check "step 6 has its sub-step 6$s" says "^### 6$s\b"; done
# shellcheck disable=SC2329
names_the_stops() { local tick; tick="$(printf '\140')"; grep -q "${tick}charter${tick}" "$GUIDE" && grep -q "${tick}brand${tick}" "$GUIDE" && grep -qi 'readiness' "$GUIDE"; }
check "it names the three stops: charter, brand and readiness" names_the_stops
check "every brand.sh command of the tools is named in the guide" every_sh_command_is_named
check "every brand.sh command the guide names exists" every_named_sh_command_exists
check "every brand.py check the guide names exists" every_named_py_command_exists
# shellcheck disable=SC2329
each_step_has_its_parts() {
  python3 - "$GUIDE" <<'PY'
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
parts = re.split(r"^## ", text, flags=re.M)[1:]
steps = {m.group(1): body for body in parts if (m := re.match(r"Step (\d)\b", body))}
need = ("**Ask**", "**Write**", "**Run**", "**Approve**")
bad = [(n, w) for n in "123456789" for w in need if n not in steps or w not in steps[n]]
for n, w in bad: print(f"step {n} lacks {w}")
sys.exit(1 if bad else 0)
PY
}
check "for each step it says what to ask, what to write, what to run and what the founder approves" each_step_has_its_parts
check "it says how a choice is saved: where, and by which command" says "brand.sh serve"
check "it says the founder never needs a terminal" grep -qi "terminal" "$GUIDE"
# The names of the companies Asgard has served are private: they are never in this repository. When the operator keeps a list of them
# (one per line) and points ASGARD_PRIVATE_NAMES at it, the guide is checked against it; without one, only the generic checks run.
# shellcheck disable=SC2329
names_no_company() { [ -z "${ASGARD_PRIVATE_NAMES:-}" ] || [ ! -f "$ASGARD_PRIVATE_NAMES" ] || ! grep -qiFf "$ASGARD_PRIVATE_NAMES" "$GUIDE"; }
check "it names no company or person from the operator's private list (when there is one)" names_no_company
check "it names no private path" quiet '/home/|~/|\.claude'
check "it says nothing is final until the founder approves" says "approve"
exit "$fail"
