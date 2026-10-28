---
title: The kickstart guide
status: draft
date: 2026-10-28
style: guide
---


# The kickstart guide

How the agent takes a founder from an idea to a company that is ready to build, in nine steps and three stops. It is the
procedure behind the [Asgard v0 design](https://github.com/ouroboric-dev/yggdrasil/blob/main/docs/1-product/design/2026-10-17-asgard-v0-design.md)
(§6 the journey, §7 the template, §8 readiness), written from the first real run, with the tools as they are built.

For each step: **Ask** what to ask the founder and in what order, **Write** what goes where, **Run** which tool or check,
**Approve** what the founder decides and how it is recorded.

## Rules that hold in every step

- **Direction is human.** The agent proposes, checks and builds; the founder decides. A stop is hers: she approves by
  merging the pull request the agent opened, from her own account. Her helper never approves for her.
- **She never needs a terminal.** She talks, reacts to options on a page and clicks. The agent runs every command here.
- **Checks support her decision.** When a choice fails a check, say so plainly, with what it costs. She may keep it. The
  failure becomes an accepted exception with her reason and the date; the company's checks then report it as accepted.
- **Show, do not describe.** A foundation that cannot be seen on a still page (motion, breakpoints) gets a view that shows it.
  In the first run, seeing motion and breakpoints changed two choices the founder had made blind.
- **One thing at a time.** Each decision has its own page, one option at a time, with its explanation.
- **Her files name no tool.** Nothing outside `.ouroboric/` in her repository names Asgard, Yggdrasil or any of their parts.
  The company's `names-check.sh` finds a leak. Her choices are her files; the tools' settings are not.
- **Her language is hers.** Ask once. Keep her own-language answers beside any translation, so that the translation can be
  checked. Words her clients read follow her clients' language; documents are English.
- **Every step can be run again.** A re-run redrafts its outputs from its inputs and keeps what she approved unless she
  reopens it.

## Before step 1

**Ask** whether she has a GitHub account, and who creates the organisation. Her company's repositories are private, and her
account is an owner of the organisation, so that she can merge. Check three things before the first stop, because the first
real run lost time on each: her invitation is accepted; her account can merge into `main`; and the GitHub plan allows what
the journey relies on. On a free plan a private repository has no protected `main` and no secret scanning, so "approval is a
merge" is a convention there, not a rule. Tell the founder's helper what each plan allows and what the journey loses.

**Write** nothing yet.

**Run** `brand.sh setup` once on the machine that runs the agent. It installs the pinned tools and a headless browser; it is
the one command that needs the network besides `brand.sh fonts`.

**Approve** nothing. The helper confirms the organisation and the plan.

## Step 1: Intent

**Ask**, in two short rounds: what she wants to do and why; her time, money and country; a good first year; the monthly range
she hopes for; her clients' languages; photographs or other personal data and consent. Ask what she already holds, before the
name step needs it: a domain, social handles, an email. Ask who owns each (the design wants her to own everything).

**Write** `docs/5-research/<date>-intent.md` (her words, the agent's reading marked as analysis) and the decisions in
`decisions.md`: her language, her first-year target, the add-ons the company takes. Scaffold the company silently with
`scripts/new-company.sh` as a private repository.

**Run** `scripts/new-company.sh`, then the company's checks (`.ouroboric/checks/run.sh`).

**Approve** nothing: this step has no stop.

## Step 2: Customers and offer

**Ask** one round: who her clients are, the moment they need her, what she sells, the price, her first clients. If she has no
price, research the local market and offer two or three priced options with a recommendation.

**Write** `docs/1-company/customers-and-offer.md` and a competitor brief in `docs/5-research/`. Confirm every price on its
source page and date it: a search summary can be wrong. Note tax and registration as step 7 matters, not here.

**Run** the company's checks.

**Approve** her choice among the priced options, recorded in the decision log.

## Step 3: Charter

**Ask** a few questions about style, delivery and what she will not do, then draft the whole charter and let her edit it:
vision, mission, principles, products, north star, boundaries. Write each principle into `AGENTS.md` as a rule: the first run
forgot, and the readiness check caught it later.

**Write** `docs/1-company/charter.md` and the principles in `AGENTS.md`. Correct the earlier documents when her edit changes
them, and say so in the dated notes.

**Run** the company's checks. Before the stop, check that she can merge (she owns the organisation, her invitation is
accepted).

**Approve** the **`charter`** stop: one pull request, in her language, with click-by-click instructions, that sets the charter
to `accepted`. Her merge makes it true. Use one rolling branch for each stop, not a pull request for each step.

## Step 4: Name

**Ask** for the name, unless it was settled before step 1. Check what she already holds before searching.

**Write** `docs/5-research/<date>-name-checks.md`: domains, the GitHub name's own rules (an organisation name cannot hold a
dot), the handles she already holds, and trademarks, marked as not checked. The formal search is a level 2 item.

**Run** the domain check through the registry's lookup. Rename the placeholder with the rename script when the name changed.

**Approve** the name, in the decision log. Renaming is mechanical and does not reopen the charter.

## Step 5: Brand, words

**Ask** four things: the feelings she wants, how she talks, her story, her references and what to avoid. When she rejects a
round of taglines, widen the next round instead of repeating it.

**Write** the positioning line, the tagline, the short pitch, the about text and the voice guide (a table of what each
trait means and does not mean, rules, examples, and an error message for the products' interface), in her clients'
languages side by side. These words feed step 6: the sample site of the playground is set in them.

**Run** the company's checks.

**Approve** the words she edits and keeps.

## Step 6: Brand, look

Seven sub-steps, in this order, because the logo's design is settled first and the rest is built around it. Each sub-step
proposes valid candidates by a stated method, checks them before showing them, and shows them in light and dark with her own
name and words. Each page saves her confirmed choice and her reason in `docs/7-branding/identity/choices/<step>.json`.

**How a page reaches her.** The agent runs `brand.sh serve DIR`, which serves the pages on the machine's own address only and
writes her choice into the repository when she presses Save. If she looks on another device, she downloads her choice and
gives the file to her helper. Before sharing any page, run `brand.sh check-page DIR PAGE`: it opens the page in a headless
browser and proves that every face loads, every image decodes, every option visibly changes the page (in light and dark at
phone, tablet and desktop widths) and the saved choice is restored. A page that fails is not shown.

**Ask** her to bring her logo concept first (any format, any quality, a sketch or a generated image).

**Write** the choices as they are saved, and the identity page of the company's docs.

**Run** the tools named in each sub-step.

**Approve** at the **`brand`** stop, after the playground, from the brand board.

### 6a Logo design

**Ask** for her concept and, when the concept has lettering, what the voice's personality words are.

**Write** the prepared concept and the review page in the choices folder; the chosen design in `logo/source/`.

**Run** `brand.sh logo-prep DIR IMAGE` (add `--mark` for a mark; a mark needs 2400 pixels on its short side, or the tracer
cuts long arcs short). It cuts out a flat background, flattens the edges to the logo's flat colours and enlarges it. Critique
the concept plainly: legibility at small sizes, light and dark, distinctiveness in her trade, irregular geometry, lettering
that is not a real typeface; name the **mark**, the part that stands alone as the favicon. Offer two to four alternatives and,
for lettering, serious and stylised typefaces with open licences. Write a candidates file and run
`brand.sh logo-proposals DIR CANDIDATES.json`: each alternative in its own bordered panel with its Strength and Risk, the
logo at four sizes and the mark at three, each in a light and a dark row, and a lettering picker. A pairing that does not work
(a letter the face lacks, a counter too narrow for the symbol, a join it breaks) carries a visible note.

**Approve** one alternative and one typeface. `brand.sh logo-proposals DIR CANDIDATES.json --choose saved` writes the chosen
design as the logo's source PNGs and records the typeface for the wordmark role. Then `brand.sh logo DIR` traces it, checks
the trace and exports the favicons and icons; a trace that is not faithful is shown as a gap, not hidden.

### 6b Palette

**Ask** for her mood words (step 5), any colour she already uses, and her references.

**Write** a round of two to four named presets, each seeded from something she said or brought, each with a light and a dark
palette, and candidate values for single colours.

**Run** `brand.sh palette DIR ROUND.json`: it checks every preset with the company's own contrast rules before it is shown,
and refuses a failing one with the failing pairs named. Then `brand.sh palette-page DIR` builds the page: one palette at a
time, then one colour role at a time, with the logo recoloured live. After three rounds without a choice, ask what is missing
instead of offering a fourth.

**Approve** a palette; she may change any colour on the page, and the final palette is saved with her reason.

### 6c Typography

**Ask** for nothing new: the voice words choose the directions to offer.

**Write** nothing by hand: the pages are built from what she saves.

**Run** `brand.sh type-page DIR CANDIDATES.json`, three times, each page after she saved the one before. Taste: one style at a
time (geometric sans, humanist, old-style serif, a script, and so on), two faces each, in her own words; she says which she
likes. Depth: only the styles she liked, with more faces there. Roles: the wordmark, display, heading, body and interface
roles, each with its job, where it appears and how often it is seen. The facts shown (weights, italic, licence, glyph
coverage) are read from the font files. The curated list is pinned by file hash; `brand.sh fonts DIR CANDIDATES.json` fetches
any other family.

**Approve** a face for each role. A body face without an italic is a plain warning; she may keep it and write emphasis in bold.

### 6d Imagery

**Ask** what her images look like, never look like, and how they are used; up to six sample images, each with its consent
record.

**Write** the imagery guidelines and the table of sample images in `docs/7-branding/imagery.md`; save images at 1600 pixels or
less, without location data, under neutral names.

**Run** the company's checks.

**Approve** the guidelines and which images stay.

### 6e Foundations

**Ask** for nothing new.

**Write** nothing by hand.

**Run** `brand.sh foundations-page DIR`: ten cards, one foundation each (body size, type scale, line height, spacing, corners,
depth, motion, focus, touch size, breakpoints), three looks that set them all, and one live sample where motion plays and the
breakpoints are a ruler with a width slider. The minimums are checked as she chooses.

**Approve** each foundation, and any minimum she keeps with her reason.

### 6f Playground

**Ask** her to look at everything together once more.

**Write** the exported token file, which the agent applies.

**Run** `brand.sh playground DIR`. It opens on her saved choices, on a sample site painted only from the tokens, and lets her
change the palette, the faces, the foundations and a variant of each component. The Checks tab lists every rule; a failure
she keeps becomes an accepted exception. Then `brand.sh playground-apply DIR --by NAME` validates the export with the
company's checks before it writes anything: a failure she did not keep refuses it. It writes `tokens.json`, copies the shipped
fonts and their licences, and makes `tokens.css`, `fonts.css` and the web fonts again.

**Approve** the playground's final settings.

### 6g Board and applications

**Ask** for nothing.

**Write** nothing by hand: the board and the first applications (a square profile picture, a link preview, an email
signature) are generated only from the saved settings.

**Run** `brand.sh board DIR`, then `brand.sh reference DIR`, which writes the design system as products will build it: a
component stylesheet, the final playground as one page without saving, and screenshots in light and dark at three widths.
Then the company's checks (`brand.py check` runs the contrast, font, foundation, type and component checks, the accepted
exceptions, and whether the generated files, the board and the reference are fresh).

**Approve** the board at the **`brand`** stop. The kept exceptions are on it, with her reasons.

## Step 7: Business basics

**Ask** four things: registration, tax, accounts and contracts; then, for her terms, a deposit, rescheduling, delivery time,
consent for her portfolio, source files and travel. Never lecture and never give legal advice: record what she defers as an
open item for a qualified person, with one plain note that paid work usually needs registration.

**Write** the founders' agreement (two founders only), the admin checklist, the accounts inventory (each account, its owner and
where its recovery details are kept, never the details), the budget, the client terms and the client data table; every legal
document marked as a draft for a qualified person.

**Run** the company's checks.

**Approve** the terms she chooses. Nothing legal is final until a qualified person has read it.

## Step 8: Roadmap

**Ask** which product comes first.

**Write** the company roadmap, each item with "done when".

**Run** the company's checks.

**Approve** it at the `brand` stop's pull request.

## Step 9: Readiness

**Ask** her to judge the human items.

**Write** a level 1 assessment from the readiness checklist, a table with the evidence of each item or "missing", and the
accepted exceptions under their items. Products are `n/a` until each one's own kickstart.

**Run** the readiness check on the company's files. A level 1 company can build; a product needs its own charter and its
design before its first spec.

**Approve** the **readiness** stop. Then each product has its own kickstart: a product charter that conforms to the company's.

## When something goes wrong

- She cannot merge: her invitation is pending or her account is not an owner. Fix it before the stop, not at it.
- A tool refuses to run: it names `brand.sh setup`. Run that, then run it again.
- A page fails `check-page`: do not show it. Fix the page; the failing option or face is named.
- The template changed since the company was made: bring the new template into her repository in one pull request, with the
  checks passing, and rerun the readiness items that changed.
