#!/usr/bin/env bash
# The company's files are the founder's own: no file outside .ouroboric/ names the tools that set the company up
# or build its products. Prints each file that does, and fails.
#   .ouroboric/checks/names-check.sh
set -euo pipefail
cd "$(git rev-parse --show-toplevel)"
names='(^|[^.])\b(asgard|yggdrasil|ouroboric|ygg|odin|gungnir|gleipnir|jormungandr|havamal|voluspa|niflheim|helheim|midgard|realm)\b'
found=0
while IFS= read -r -d '' f; do
  case "$f" in .ouroboric/*) continue ;; esac
  [ -f "$f" ] || continue
  if grep -IqiE "$names" "$f"; then echo "$f: names a tool; move the setting into .ouroboric/ or reword it"; found=1; fi
done < <(git ls-files -z --cached --others --exclude-standard)
exit "$found"
