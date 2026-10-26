#!/usr/bin/env bash
# Scaffold a company umbrella from templates/company: step 1 of the company kickstart (Asgard v0 design §6, §7).
#   new-company.sh --name NAME [--date YYYY-MM-DD] [--no-yggdrasil] [--open-source] [--founders N] DIR
# It copies templates/company/core, then each add-on that is on, into DIR, which must not exist or be empty:
#   yggdrasil    on by default (--no-yggdrasil turns it off): the standards page and the factory's budget section
#   open-source  off by default (--open-source turns it on): licences, contributions, trademarks
#   founders     on when --founders is 2 or more (default 1): the founders' agreement
# In every file it replaces {{COMPANY}} with NAME, {{DATE}} with the date (default: today, UTC) and {{TEMPLATE}} with
# the version of Asgard it came from. NAME is the company's name, or a neutral placeholder before step 4 (Name).
# It writes .ouroboric/company.yaml: the template version, the date, the add-ons. Nothing outside .ouroboric/ names
# Asgard, Yggdrasil, Ouroboric or any of their parts: the company's files are the founder's own. It makes no
# repository and pushes nothing: the agent or the operator does that, in the founder's own organisation.
# Agent-run.
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TPL="$HERE/../templates/company"

name="" date="" ygg=1 oss=0 founders=1 dir=""
die() { echo "new-company: $*" >&2; exit 2; }
while [ $# -gt 0 ]; do
  case "$1" in
    --name) name="${2:-}"; shift 2 ;;
    --date) date="${2:-}"; shift 2 ;;
    --no-yggdrasil) ygg=0; shift ;;
    --open-source) oss=1; shift ;;
    --founders) founders="${2:-}"; shift 2 ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$dir" ] || die "one folder only"; dir="$1"; shift ;;
  esac
done
[ -n "$name" ] || die "--name is required (the company's name, or a placeholder before step 4)"
[ -n "$dir" ] || die "the folder to scaffold into is required"
# The name goes into Markdown, YAML and JSON through sed: letters, digits, spaces, dots, hyphens, apostrophes and
# ampersands only.
[[ "$name" =~ ^[[:alnum:]][[:alnum:]\ .\'\&-]*$ ]] || die "the name may hold only letters, digits, spaces and . - ' &"
[ -n "$date" ] || date="$(date -u +%Y-%m-%d)"
[[ "$date" =~ ^[0-9]{4}-[0-9]{2}-[0-9]{2}$ ]] || die "--date must be YYYY-MM-DD"
[[ "$founders" =~ ^[1-9][0-9]*$ ]] || die "--founders must be 1 or more"
if [ -e "$dir" ] && [ -n "$(ls -A "$dir")" ]; then die "$dir is not empty"; fi
[ -d "$TPL/core" ] || die "no template at $TPL/core"

version="$(git -C "$HERE/.." describe --always --dirty --abbrev=12 2>/dev/null || echo unknown)"
addons=()
[ "$ygg" -eq 1 ] && addons+=(yggdrasil)
[ "$oss" -eq 1 ] && addons+=(open-source)
[ "$founders" -ge 2 ] && addons+=(founders)

mkdir -p "$dir"
cp -R "$TPL/core/." "$dir/"
for a in "${addons[@]}"; do cp -R "$TPL/$a/." "$dir/"; done

# A sed replacement must escape &, the delimiter | and backslashes; the name check above keeps | and \ out.
esc_name="${name//&/\\&}"
while IFS= read -r -d '' f; do
  sed -i -e "s|{{COMPANY}}|$esc_name|g" -e "s|{{DATE}}|$date|g" -e "s|{{TEMPLATE}}|$version|g" "$f"
done < <(find "$dir" -type f -print0)

joined="$(IFS=,; echo "${addons[*]}")"
mkdir -p "$dir/.ouroboric"
cat >"$dir/.ouroboric/company.yaml" <<EOF
# Where this company umbrella came from: written when the company was set up.
template: $version
date: $date
addons: [${joined//,/, }]
founders: $founders
EOF
echo "new-company: scaffolded $name in $dir (template $version, add-ons: ${joined:-none})"
