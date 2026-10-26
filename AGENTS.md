# AGENTS.md: Asgard

Asgard is the company factory. It runs on Odin and turns an idea into a company that is ready to
build. This umbrella holds docs and the templates Asgard copies into new companies. Start with
`docs/1-product/charter.md`.

## Invariants

These rules apply to every repo in this tree. They include the company invariants:
<https://github.com/ouroboric-dev/ouroboric/blob/main/AGENTS.md#invariants>
A child `AGENTS.md` may add rules; it must not loosen these.

1. Humans steer. Stop and ask when work would leave an approved charter, spec or plan.
2. Write the failing test first. A test that never failed proves nothing.
3. Never merge a pull request, and never push to `main`. Humans merge.
4. Never read, print or store secrets, tokens or keys.
5. Never weaken a guardrail: approval points, sandbox settings, policies, rulesets or security tests.
6. Direction is human. Draft and check charters; never approve them.
7. Readiness is evidence. Link every readiness item to its evidence, or mark it missing.
8. Asgard is not a lawyer. Scaffold legal material and flag what needs a qualified person; never
   present it as legal advice.

## Map

- Direction: `docs/1-product/charter.md`.
- Templates copied into new companies: `templates/` (MIT).
- The company template: `templates/company/` (`core/` and one folder per add-on); scaffold it with
  `scripts/new-company.sh`, tested by `scripts/tests/new-company.test.sh`. Its docs render as pages on
  this machine only with `scripts/company-site.sh build|serve DIR`, tested by `scripts/tests/company-site.test.sh`
  (needs mkdocs with the Material theme).
- Standards: <https://github.com/ouroboric-dev/ouroboric/tree/main/docs/4-ways-of-working>
