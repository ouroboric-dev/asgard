#!/usr/bin/env bash
# Render a company umbrella's docs as pages, for review on this machine only (Asgard v0 design §6.2).
#   company-site.sh build DIR               build DIR/.ouroboric/site, strict: a broken link or a stray page fails
#   company-site.sh serve [--port N] DIR    serve on http://127.0.0.1:N (default 8000), rebuilt on every save
# The settings are DIR/.ouroboric/mkdocs.yml, written by new-company.sh; the built pages are ignored by git. It
# publishes nothing: the pages never leave this machine. Needs mkdocs with the Material theme.
# Operator- or agent-run.
set -euo pipefail
die() { echo "company-site: $*" >&2; exit 2; }

cmd="${1:-}"; [ $# -gt 0 ] && shift
case "$cmd" in build|serve) ;; *) die "usage: company-site.sh build|serve [--port N] DIR" ;; esac
port=8000 dir=""
while [ $# -gt 0 ]; do
  case "$1" in
    --port) [ "$cmd" = serve ] || die "--port is for serve"; port="${2:-}"; shift 2 ;;
    -*) die "unknown option $1" ;;
    *) [ -z "$dir" ] || die "one folder only"; dir="$1"; shift ;;
  esac
done
[ -n "$dir" ] || die "the company folder is required"
[[ "$port" =~ ^[1-9][0-9]{0,4}$ ]] && [ "$port" -le 65535 ] || die "--port must be a number from 1 to 65535"
cfg="$dir/.ouroboric/mkdocs.yml"
[ -f "$cfg" ] || die "no site settings at $cfg (new-company.sh writes them)"
command -v mkdocs >/dev/null || die "mkdocs is not installed (pip install mkdocs-material)"

case "$cmd" in
  build) exec mkdocs build --strict --clean --config-file "$cfg" ;;
  serve) exec mkdocs serve --strict --config-file "$cfg" --dev-addr "127.0.0.1:$port" ;;
esac
