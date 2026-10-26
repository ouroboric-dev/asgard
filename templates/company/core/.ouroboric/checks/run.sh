#!/usr/bin/env bash
# The company's checks: the CI runs this on every pull request (.github/workflows/checks.yml), and anyone can run
# it from the repository. It runs every check, then fails if any failed. The lint hooks and their settings are
# the repository's own, at its root (.pre-commit-config.yaml, .markdownlint.yaml, .yamllint.yaml).
#   .ouroboric/checks/run.sh   (needs pre-commit, python3 and mkdocs with the Material theme)
set -uo pipefail
cd "$(git rev-parse --show-toplevel)" || exit 2
C=.ouroboric/checks
fail=0
step() { local name="$1"; shift; echo "== $name"; if "$@"; then echo "ok   $name"; else echo "FAIL $name"; fail=1; fi; }

step "lint" pre-commit run --all-files --show-diff-on-failure
step "secrets in the whole history" pre-commit run --hook-stage manual gitleaks-history --all-files
step "docs: front matter, file names, links" python3 "$C/docs-check.py"
step "docs: the pages build" mkdocs build --strict --clean --quiet --config-file .ouroboric/mkdocs.yml
step "no tool names outside .ouroboric/" "$C/names-check.sh"
exit "$fail"
