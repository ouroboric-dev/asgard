---
title: Readiness checklist
status: draft
date: 2026-10-11
style: procedure
---

# Readiness checklist

This is the readiness checklist for companies and products.

1. Copy this checklist into `docs/1-company/readiness/YYYY-MM-DD-<level>.md`.
2. Fill one row for each item.
3. Give evidence (a link) for each item, or mark the item missing.

Check type **auto** means that the docs check can verify the item. The check verifies that the
artifact exists and has the correct status. Check type **human** means that a person must judge the item.

The column **Applies to** says who answers the item. A **company** item is checked once for the company, when it
asks for the level. A **product** item is checked for each product, at its kickstart and before its first spec.

Use these status values: `met`, `partial`, `missing`, `n/a` (give a reason).

## Level 1: ready to build (before the first spec)

| ID | Area | Applies to | Question | Check |
| --- | --- | --- | --- | --- |
| RB-01 | direction | company | Is the company charter accepted? | auto |
| RB-02 | direction | product | Is the product charter accepted, and does it conform to the company charter? | auto + human |
| RB-03 | direction | product | Is milestone 1's design doc accepted? | auto |
| RB-04 | direction | company | Are the roadmaps (company and product) written? | auto |
| RB-05 | direction | company | Are the principles turned into `AGENTS.md` invariants in every repo? | auto |
| RB-06 | brand | company | Is the name checked: domains, GitHub org, package registries, trademarks? | human |
| RB-07 | brand | company | Is the brand seed (story, naming rules) written? | auto |
| RB-08 | legal | company | Is a licence chosen for everything that will be public? | auto |
| RB-09 | legal | company | Are contribution terms in place (contributor agreement or DCO, code of conduct, security policy)? | auto |
| RB-10 | legal | company | Is ownership clear: can this work be done on the time, equipment and accounts used, without someone else's claim on it? | human |
| RB-11 | shape | company | Are the repo tree, orgs, visibility and hosting target decided? | human |
| RB-12 | shape | company | Do the repos exist and follow the docs standard? | auto |
| RB-13 | money | company | Are budgets and caps set (subscriptions, API keys with credit limits)? | human |
| RB-14 | security | company | Are dedicated, revocable credentials in place, with no secrets in any repo, and secret scanning on? | auto + human |
| RB-15 | process | company | Are the standards (SDD, docs, writing styles) accepted? | auto |
| RB-16 | knowledge | company | Is the research behind the key decisions recorded? | auto |
| RB-17 | record | company | Has the journal started? | auto |
| RB-18 | build | product | Is the implementation plan written and accepted? | auto |
| RB-19 | build | product | Are the open technical risks identified, with a plan to test them first? | human |
| RB-20 | build | product | Is the measure of success fixed in advance (benchmark brief and hidden tests, if any)? | auto + human |
| RB-21 | brand | company | Is the identity defined: logo and mark in light and dark, a palette whose pairs pass WCAG 2.2 AA in both modes? | auto + human |
| RB-22 | brand | company | Is the typography chosen for every role, the wordmark included, with its reason, under a licence that allows web use, covering every glyph of the clients' languages? | auto + human |
| RB-23 | brand | company | Are the foundations set as tokens: type scale with a minimum body size, spacing, radius, elevation, motion, breakpoints? | auto |
| RB-24 | brand | company | Are interaction states defined, with a focus indicator that reaches 3:1, and is reduced motion honoured? | auto + human |
| RB-25 | brand | product | Does the product's theme come from the company's tokens, through the token contract, and does its styleguide match the company's reference? | auto |

## Level 2: ready to launch (before `deploy-prod`)

| ID | Area | Applies to | Question | Check |
| --- | --- | --- | --- | --- |
| RL-01 | legal | company | Are the privacy policy, terms, data map and deletion process written and reviewed by a qualified person? | auto + human |
| RL-02 | operations | company | Are runbooks written (deploy, restore, rotate keys, incidents)? | auto |
| RL-03 | operations | company | Has a backup been restored at least once? | human |
| RL-04 | money | company | Are cost alerts and caps set with the hosting providers? | human |
| RL-05 | support | company | Is there a support channel and an incident process? | human |
| RL-06 | brand | company | Is the full visual identity done: the component baseline (buttons, links, fields, cards, messages) in both modes, an icon set with its licence, logo usage rules (clear space, minimum size, misuse) and the brand's applications? | auto + human |
| RL-07 | security | company | Is production separated from previews (secrets, databases, storage)? | human |
| RL-08 | legal | company | Has a formal trademark search for the company and product names been run in the official registers of the target markets (for example USPTO, and EUIPO through TMview), with any conflicts resolved? | human |

## Level 3: ready to promote

| ID | Area | Applies to | Question | Check |
| --- | --- | --- | --- | --- |
| RP-01 | brand | company | Is the voice guide written? | auto |
| RP-02 | record | company | Do journal entries carry measured results to quote? | auto |
| RP-03 | content | company | Is the launch copy written and humanized? | human |
| RP-04 | legal | company | Is everything to be published scrubbed of secrets and private data? | auto + human |

## Accepted exceptions

A founder may keep a choice that fails one of the brand checks. Her company's checks then report it as accepted, not as
a failure, and it does not stop the build, but a reviewer must still see it. List each accepted exception here, under
the item it belongs to, with the check, the value that fails, her reason, who accepted it and the date. An exception
covers one check on one value: when the value changes, the check applies again and the entry is out of date.

| Item | Check | Value | Reason | By | Date |
| --- | --- | --- | --- | --- | --- |
| | | | | | |
