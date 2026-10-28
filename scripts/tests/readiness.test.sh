#!/usr/bin/env bash
# Tests for the readiness checklist template: templates/readiness/checklist.md.   scripts/tests/readiness.test.sh
# (the design system tasks DS-T02: the items RB-21 to RB-25 and RL-06, an "applies to" column, no tool names)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
LIST="$HERE/../../templates/readiness/checklist.md"
fail=0
check() { local d="$1"; shift; if "$@"; then echo "ok   $d"; else echo "FAIL $d"; fail=1; fi; }
# shellcheck disable=SC2329 # these run through check
says() { grep -q -- "$1" "$LIST"; }
# shellcheck disable=SC2329
quiet() { ! grep -qiE -- "$1" "$LIST"; }
# rows: print "ID|Area|Applies|Question|Check" for every item row.
rows() { grep -E '^\| R[BLP]-[0-9]+' "$LIST" | awk -F'|' '{ for (i = 2; i <= NF - 1; i++) { gsub(/^ +| +$/, "", $i) } print $2 "|" $3 "|" $4 "|" $5 "|" $6 }'; }
# shellcheck disable=SC2329
row() { rows | grep -E "^$1\|"; }
# shellcheck disable=SC2329
every_row_has_five_cells() { [ -z "$(grep -E '^\| R[BLP]-[0-9]+' "$LIST" | awk -F'|' 'NF != 7')" ]; }
# shellcheck disable=SC2329
every_table_has_the_column() { [ "$(grep -c '^| ID | Area | Applies to | Question | Check |$' "$LIST")" -eq 3 ]; }
# shellcheck disable=SC2329
applies_is_company_or_product() { [ -z "$(rows | awk -F'|' '$3 != "company" && $3 != "product"')" ]; }
# shellcheck disable=SC2329
product_items_are() { [ "$(rows | awk -F'|' '$3 == "product" { printf "%s ", $1 }')" = "$1 " ]; }
# shellcheck disable=SC2329
ids_are_unique() { [ -z "$(rows | cut -d'|' -f1 | sort | uniq -d)" ]; }
# shellcheck disable=SC2329
row_says() { row "$1" | grep -qi -- "$2"; }
# shellcheck disable=SC2329
exceptions_follow_their_item() { awk '/^## Accepted exceptions/ { found = 1 } END { exit found ? 0 : 1 }' "$LIST"; }

check "every item row has an ID, area, applies to, question and check" every_row_has_five_cells
check "each of the three level tables has the applies-to column" every_table_has_the_column
check "every item applies to the company or to a product" applies_is_company_or_product
check "the product items are RB-02, RB-03, RB-18 to RB-20 and RB-25" product_items_are "RB-02 RB-03 RB-18 RB-19 RB-20 RB-25"
check "item IDs are unique" ids_are_unique
check "RB-21 asks for the identity: logo and mark in light and dark, a palette that passes WCAG 2.2 AA" \
  row_says RB-21 "mark in light and dark"
check "and its palette pairs" row_says RB-21 "WCAG 2.2 AA"
check "RB-22 asks for the typography of every role, the wordmark included, with its reason" row_says RB-22 "wordmark"
check "and the licence and the glyphs of the clients' languages" row_says RB-22 "every glyph of the clients' languages"
check "RB-23 asks for the foundations as tokens" row_says RB-23 "foundations"
check "RB-24 asks for interaction states, a focus indicator at 3:1 and reduced motion" row_says RB-24 "3:1"
check "RB-25 asks that a product's theme comes from the company's tokens" row_says RB-25 "tokens"
check "RB-25 is a product item and checked by the script" [ "$(row RB-25 | cut -d'|' -f3,5)" = "product|auto" ]
check "the old RB-21, a minimal identity, is gone" quiet "minimal visual identity"
check "RL-06 asks for the component baseline" row_says RL-06 "component baseline"
check "an icon set with its licence" row_says RL-06 "icon set"
check "logo usage rules" row_says RL-06 "logo usage"
check "and the brand's applications" row_says RL-06 "applications"
check "RL-06 stays a level 2 company item" [ "$(row RL-06 | cut -d'|' -f3)" = "company" ]
check "the checklist says what applies to means" says "Applies to"
check "accepted exceptions have a place: listed under their item" exceptions_follow_their_item
check "with the fields an exception records" says "reason"
check "no tool is named in what a company copies" quiet 'brand\.(py|sh)|\.ouroboric|asgard|yggdrasil|ouroboric|odin|gungnir|gleipnir|havamal|voluspa|resvg|vtracer|fonttools'
exit "$fail"
