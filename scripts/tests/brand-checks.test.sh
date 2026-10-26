#!/usr/bin/env bash
# Tests for the company template's brand checks: .ouroboric/checks/brand.py (the contrast check, the font licence
# check, the generated files).   scripts/tests/brand-checks.test.sh   (needs python3)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
NEW="$HERE/../new-company.sh"
T="$(mktemp -d)"
trap 'rm -rf -- "$T"' EXIT
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
says() { grep -q -- "$2" "$1"; }
# shellcheck disable=SC2329
quiet_about() { ! grep -q -- "$2" "$1"; }
# shellcheck disable=SC2329
says_all() { local f="$1" p; shift; for p in "$@"; do grep -q -- "$p" "$f" || return 1; done; }

# A company to change: scaffolded, a git repository (the checks find its root through git).
"$NEW" --name "Example Studio" --date 2026-10-27 "$T/a" >/dev/null 2>&1
git -C "$T/a" init -q -b main
TOKENS="$T/a/docs/7-branding/identity/tokens.json"
cp "$TOKENS" "$T/tokens.template.json"

# brand MODE ... : run brand.py in the company; stdout and stderr to $T/out, the exit code to $T/code.
brand() { (cd "$T/a" && python3 .ouroboric/checks/brand.py "$@") >"$T/out" 2>&1; echo $? >"$T/code"; }
# shellcheck disable=SC2329 # code runs through check
code() { [ "$(cat "$T/code")" = "$1" ]; }
# palette KEY=VALUE ... : the template's tokens.json, then each light.KEY or dark.KEY set (null for null).
palette() {
  python3 - "$T/tokens.template.json" "$TOKENS" "$@" <<'EOF'
import json, sys
src, dst, *pairs = sys.argv[1:]
t = json.load(open(src))
for pair in pairs:
    key, value = pair.split("=", 1)
    mode, name = key.split(".", 1)
    t[mode][name] = None if value == "null" else value
json.dump(t, open(dst, "w"), indent=2)
EOF
}
GOOD=(light.bg=#FFFFFF light.surface=#F5F5F5 light.border=#DDDDDD light.text=#1A1A1A light.muted=#555555
  light.accent=#0B5FCC light.accent-text=#0B5FCC light.on-accent=#FFFFFF light.ok=#1B6E20 light.warn=#8A5A00
  light.crit=#B00020
  dark.bg=#121212 dark.surface=#1E1E1E dark.border=#333333 dark.text=#EDEDED dark.muted=#B0B0B0
  dark.accent=#6EA8FE dark.accent-text=#6EA8FE dark.on-accent=#121212 dark.ok=#81C784 dark.warn=#FFB74D
  dark.crit=#EF9A9A)

# The contrast check (spec §5.1).
brand contrast
check "the template's empty palette passes (5.1.8)" code 0
check "and says the palette is not set" says "$T/out" "not set"

palette "${GOOD[@]}"; brand contrast
check "a palette whose pairs all reach their minimum passes" code 0
check "it tests the light palette and the dark palette (5.1.1)" says_all "$T/out" "^light" "^dark"
check "it reports the enhanced level for text, for information" says "$T/out" "7:1"
check "it reports the border, which has no minimum" says "$T/out" "border"

palette "${GOOD[@]}" light.muted=#999999; brand contrast
check "a text pair below 4.5:1 fails (5.1.4)" code 1
check "the failure names the mode, the tokens, the ratio and the minimum (5.1.5)" \
  says "$T/out" "tokens.json: light: muted on bg is 2.84:1, under the minimum 4.5:1"

palette "${GOOD[@]}" dark.accent=#2A2A2A dark.on-accent=#FFFFFF; brand contrast
check "a shape below 3:1 fails" code 1
check "and names it as a shape" says "$T/out" "dark: accent on bg is .*minimum 3:1"

palette "${GOOD[@]}" light.border=#FEFEFE; brand contrast
check "a border with no contrast does not fail: it is decorative" code 0

palette "${GOOD[@]}" light.text=#767676 light.muted=#767676 light.surface=#FFFFFF; brand contrast
check "#767676 on #FFFFFF passes at 4.54:1 (5.1.10)" code 0
check "the ratio is shown rounded down to two decimals (5.1.6)" says "$T/out" "4.54:1"
palette "${GOOD[@]}" light.text=#777777 light.surface=#FFFFFF; brand contrast
check "#777777 on #FFFFFF fails at 4.47:1 (5.1.10)" code 1
check "and is not rounded up to pass (5.1.3)" says "$T/out" "text on bg is 4.47:1"

palette "${GOOD[@]}" light.text=red; brand contrast
check "a value that is not #RRGGBB fails (5.1.7)" code 1
check "and names the token" says "$T/out" "light: text is 'red', not #RRGGBB"

palette "${GOOD[@]}" light.warn=null dark.crit=null; brand contrast
check "a palette with some values missing fails (5.1.9)" code 1
check "and names each missing token" says_all "$T/out" "light: warn is not set" "dark: crit is not set"

palette "${GOOD[@]}" light.brand-1=#FFF5F5 dark.brand-1=#151515; brand contrast
check "a brand token never fails by its contrast (5.1.11)" code 0
check "but it is reported, for information" says "$T/out" "brand-1"
palette "${GOOD[@]}" light.brand-1=#C2185B; brand contrast
check "a brand token with a value in one mode only fails (5.1.11)" code 1
check "and says the other mode is missing" says "$T/out" "brand-1 has no dark value"

echo '{ not json' >"$TOKENS"; brand contrast
check "tokens.json that is not JSON stops the check with code 2" code 2

palette "${GOOD[@]}"; brand contrast --json
check "--json prints one object per pair" python3 -c '
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
keys = {"mode", "fg", "bg", "kind", "ratio", "minimum", "result"}
assert rows and all(keys <= r.keys() for r in rows), rows[:1]
' "$T/out"

palette "${GOOD[@]}"; brand check
check "check runs the contrast check" says_all "$T/out" "^light" "^dark"
check "and passes on a good palette" code 0
cp "$T/tokens.template.json" "$TOKENS"
check "run.sh runs the brand checks as one step (5.5.1)" grep -q 'brand.py" check' "$T/a/.ouroboric/checks/run.sh"
check "the output names no tool" quiet_about "$T/out" "brand.py"

exit "$fail"
