---
title: Readiness checklist
status: draft
date: 2026-10-11
style: procedure
---

# Readiness checklist

This is the Asgard checklist for companies and products.

1. Copy this checklist into `docs/1-company/readiness/YYYY-MM-DD-<level>.md`.
2. Fill one row for each item.
3. Give evidence (a link) for each item, or mark the item missing.

Check type **auto** means that the docs check can verify the item. The check verifies that the
artifact exists and has the correct status. Check type **human** means that a person must judge the item.

Use these status values: `met`, `partial`, `missing`, `n/a` (give a reason).

## Level 1: ready to build (before the first spec)

| ID | Area | Question | Check |
| --- | --- | --- | --- |
| RB-01 | direction | Is the company charter accepted? | auto |
| RB-02 | direction | Is the product charter accepted, and does it conform to the company charter? | auto + human |
| RB-03 | direction | Is milestone 1's design doc accepted? | auto |
| RB-04 | direction | Are the roadmaps (company and product) written? | auto |
| RB-05 | direction | Are the principles turned into `AGENTS.md` invariants in every repo? | auto |
| RB-06 | brand | Is the name checked: domains, GitHub org, package registries, trademarks? | human |
| RB-07 | brand | Is the brand seed (story, naming rules) written? | auto |
| RB-08 | legal | Is a licence chosen for everything that will be public? | auto |
| RB-09 | legal | Are contribution terms in place (contributor agreement or DCO, code of conduct, security policy)? | auto |
| RB-10 | legal | Is ownership clear: can this work be done on the time, equipment and accounts used, without someone else's claim on it? | human |
| RB-11 | shape | Are the repo tree, orgs, visibility and hosting target decided? | human |
| RB-12 | shape | Do the repos exist and follow the docs standard? | auto |
| RB-13 | money | Are budgets and caps set (subscriptions, API keys with credit limits)? | human |
| RB-14 | security | Are dedicated, revocable credentials in place, with no secrets in any repo, and secret scanning on? | auto + human |
| RB-15 | process | Are the standards (SDD, docs, writing styles) accepted? | auto |
| RB-16 | knowledge | Is the research behind the key decisions recorded? | auto |
| RB-17 | record | Has the journal started? | auto |
| RB-18 | build | Is the implementation plan written and accepted? | auto |
| RB-19 | build | Are the open technical risks identified, with a plan to test them first? | human |
| RB-20 | build | Is the measure of success fixed in advance (benchmark brief and hidden tests, if any)? | auto + human |
| RB-21 | brand | Is a minimal visual identity defined: logo, colour palette with accessible contrast, typography with licensed fonts, and basic design rules? | auto + human |

## Level 2: ready to launch (before `deploy-prod`)

| ID | Area | Question | Check |
| --- | --- | --- | --- |
| RL-01 | legal | Are the privacy policy, terms, data map and deletion process written and reviewed by a qualified person? | auto + human |
| RL-02 | operations | Are runbooks written (deploy, restore, rotate keys, incidents)? | auto |
| RL-03 | operations | Has a backup been restored at least once? | human |
| RL-04 | money | Are cost alerts and caps set with the hosting providers? | human |
| RL-05 | support | Is there a support channel and an incident process? | human |
| RL-06 | brand | Is the complete visual identity done: logo system and usage rules, palette and typography as design tokens, and source assets? | auto + human |
| RL-07 | security | Is production separated from previews (secrets, databases, storage)? | human |
| RL-08 | legal | Has a formal trademark search for the company and product names been run in the official registers of the target markets (for example USPTO, and EUIPO through TMview), with any conflicts resolved? | human |

## Level 3: ready to promote

| ID | Area | Question | Check |
| --- | --- | --- | --- |
| RP-01 | brand | Is the voice guide written? | auto |
| RP-02 | record | Do journal entries carry measured results to quote? | auto |
| RP-03 | content | Is the launch copy written and humanized? | human |
| RP-04 | legal | Is everything to be published scrubbed of secrets and private data? | auto + human |
