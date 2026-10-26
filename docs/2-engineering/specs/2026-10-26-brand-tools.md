---
title: Brand tools spec
status: draft
date: 2026-10-26
related: [../../../templates/company/core/docs/7-branding/identity/README.md, ../../../templates/company/core/docs/7-branding/identity/tokens.json, ../../../templates/company/core/docs/7-branding/identity/logo/README.md, ../../../templates/company/core/.ouroboric/checks/run.sh, ../../../templates/company/core/.ouroboric/mkdocs.yml, ../../../scripts/company-site.sh, ../../../templates/readiness/checklist.md]
style: spec
---

# Brand tools spec

## 1. Summary

This spec says how Asgard delivers the tools of step 6, **Brand: look**, in the
[Asgard v0 design](https://github.com/ouroboric-dev/yggdrasil/blob/main/docs/1-product/design/2026-10-17-asgard-v0-design.md)
(§6.1 row 6, §6.2, §8). Step 6 ends at the founder's `brand` stop, where she approves a **brand board**.

There are four tools:

- **The contrast check** reads the palettes in `tokens.json` and checks every text and shape pair against WCAG 2.2
  level AA, in light and dark mode.
- **The font licence check** reads the licence file and the metadata of each font the company ships. It passes a
  font only on evidence of a known open licence and flags everything else for a person.
- **Logo processing** traces the founder's PNG into SVG with **VTracer 0.6.15 (MIT)**, recolours it with the palette
  tokens, derives the missing mode, exports the favicon and app icons, and checks that the trace is faithful. A trace
  that is not faithful is recorded as a gap and shown on the board.
- **The brand board** is a generated page in the company's docs. It shows the palettes with their contrast, the
  fonts, her PNG beside the SVGs, the icons, sample images and every open gap.

The two checks are company checks: the company's CI runs them on every pull request. Logo processing and the board
are Asgard scripts that the agent runs. Every tool works offline after a one-time setup, and nothing it writes into
the company's repository names Ouroboric or any of its parts.

Section 10 lists the open questions for the founder.

## 2. Architecture and components

```text
asgard leaf (AGPL-3.0)
├── scripts/brand.sh            setup | logo DIR | board [--check] DIR
├── scripts/brand/              logo.py, board.py, requirements.txt (hashed pins), resvg.lock (URL and SHA-256 per platform)
└── scripts/tests/              brand.test.sh, brand-checks.test.sh

a company repository (from templates/company, MIT)
├── .ouroboric/checks/brand.py  contrast | fonts | tokens [--write] | board-fresh | check
├── .ouroboric/checks/run.sh    gains the step "brand: contrast, fonts, generated files"
├── .ouroboric/mkdocs.yml       gains extra_css: 7-branding/identity/fonts.css
└── docs/7-branding/identity/
    ├── tokens.json             the source: palettes and fonts (written by the agent from her choices)
    ├── tokens.css, fonts.css   generated from tokens.json and the font files
    ├── fonts/<family>/         font files as published, with the licence file they came with
    ├── board.md                generated: the brand board
    └── logo/
        ├── source/             her PNG: logo.png (for light backgrounds), logo-dark.png (for dark), or both
        ├── logo.svg, logo-dark.svg, favicon.svg, favicon.ico, icon-192.png, icon-512.png
        ├── trace-light.png, trace-dark.png   generated: where the trace differs from her PNG
        └── trace.json          generated: the faithfulness result, the colour mapping and the gaps
```

The checks live in the company template so the company's CI runs them with no Asgard code. The board script reads
their results with `brand.py contrast --json` and `brand.py fonts --json`, so each rule has one implementation.

### 2.1 Dependencies

| Tool | Version | Licence | Used for | Pinning |
| --- | --- | --- | --- | --- |
| Python | 3.10 or later | PSF-2.0 | every tool; the contrast check needs only the standard library | the CI's `setup-python` (3.11) |
| [VTracer](https://github.com/visioncortex/vtracer) (PyPI `vtracer`) | 0.6.15 (2026-03-23) | [MIT](https://github.com/visioncortex/vtracer/blob/0.6.15/LICENSE) | tracing | `requirements.txt`, exact version and `--hash` |
| [Pillow](https://python-pillow.org) | 12.3.0 (2026-07-01) | MIT-CMU (PyPI metadata) | PNG reading, alpha cleanup, comparison, ICO and PNG export | same |
| [fontTools](https://github.com/fonttools/fonttools) | 4.66.1 (2026-09-29) | MIT | font `name` and `OS/2` tables | same; also in the company's `checks.yml` |
| [Brotli](https://github.com/google/brotli) | 1.2.0 (2025-11-05) | MIT | WOFF2 reading for fontTools | same |
| [resvg](https://github.com/linebender/resvg) CLI | 0.48.1 (2026-08-02) | [Apache-2.0 OR MIT](https://github.com/linebender/resvg/blob/main/Cargo.toml) | SVG to PNG, for the faithfulness check and the icons | release binary (`linux-x86_64`, `macos-aarch64`, `macos-x86_64`), SHA-256 in `resvg.lock` |
| MkDocs, Material for MkDocs | 1.5.3, 9.2.7 | BSD, MIT (PyPI classifiers) | renders the board with the other pages | unchanged from the template |

Every version is a release at least two weeks old, as the template's lint pins are. Newer releases exist (Pillow
13.0.0, fontTools 4.67.0, Brotli 1.2.1) but are younger than two weeks today. Every licence in the table is
permissive, so Asgard's AGPL-3.0 scripts can call each tool. The tools run on the founder's files, and their output
carries none of their code: the one mark a tool leaves, VTracer's generator comment, is removed (§5.3).

## 3. Interfaces and contracts

### 3.1 `brand.py` (company check)

```text
.ouroboric/checks/brand.py contrast [--json]    the palette pairs (§5.1)
.ouroboric/checks/brand.py fonts [--json]       the font licence evidence (§5.2)
.ouroboric/checks/brand.py tokens [--write]     tokens.css and fonts.css from tokens.json; without --write, fail when stale
.ouroboric/checks/brand.py board-fresh          board.md matches its inputs (§5.4)
.ouroboric/checks/brand.py check                all four; run.sh runs this
```

Each finding prints as `path: what is wrong`, like `docs-check.py`. Exit codes: 0 when every check passes, 1 when a
check has a finding, 2 when it cannot run (for example, `tokens.json` is not valid JSON). `--json` prints one object
per pair or font, with its result, for the board.

### 3.2 `brand.sh` (Asgard script)

```text
brand.sh setup               install the pinned tools into the cache; the only command that uses the network
brand.sh logo DIR            trace, recolour, derive, export and check the logo of the company in DIR
brand.sh board [--check] DIR write DIR/docs/7-branding/identity/board.md; --check fails when it is stale
```

- `setup` creates a virtual environment under `${XDG_CACHE_HOME:-$HOME/.cache}/asgard/brand/<key>`, where `<key>` is
  a hash of `requirements.txt` and `resvg.lock`. It runs `pip install --require-hashes --only-binary :all:`. It
  downloads the resvg binary for the platform and refuses it when its SHA-256 differs from `resvg.lock`.
- `logo` and `board` refuse to run when the environment for the current `<key>` is missing, and name `setup`.
- Exit codes follow `company-site.sh`: 0 done, 2 refused (usage, missing setup, an input refused). A gap is not a
  failure: `logo` prints it, records it in `trace.json`, and exits 0.

### 3.3 How step 6 uses them

1. The agent writes her palette and font choices into `tokens.json`. It copies each font's folder, unchanged, from
   its publisher into `fonts/<family>/`.
2. The agent runs `brand.py tokens --write`, then `brand.py check`, and resolves each finding with her.
3. The agent saves her PNG in `logo/source/` and runs `brand.sh logo`.
4. The agent runs `brand.sh board`, then `run.sh`, and opens the pull request for the `brand` stop.
5. She reviews the rendered board and approves by merging (design §6.2).

Each tool writes only its generated files and never edits a document a person wrote. Running a step again gives the
same files from the same inputs.

## 4. Data model

### 4.1 `tokens.json` (changed)

The colour keys stay as the template has them: `bg`, `surface`, `border`, `text`, `muted`, `accent`, `accent-text`,
`on-accent`, `ok`, `warn`, `crit`, in `light` and in `dark`. Each value is `#RRGGBB` (opaque) or `null` before step 6.

Each font role gains the evidence the font check reads. `type.licence` is removed.

```json
"heading": {
  "family": "Literata",
  "fallback": "Georgia, serif",
  "weights": [600, 700],
  "files": "fonts/literata",
  "licence": "OFL-1.1",
  "source": "https://github.com/google/fonts/tree/main/ofl/literata"
}
```

- `files` is a folder relative to `identity/`, or `null` for a font the products do not ship (the reader's device
  supplies it).
- `licence` is an SPDX id. `source` is where the folder came from, for the person who reads a flag.
- `licence_review: {"by": "<name>", "date": "YYYY-MM-DD"}` is optional. It records that a person read a licence the
  check flagged (§5.2).

### 4.2 `trace.json` (generated)

```json
{
  "inputs": {"source/logo.png": "sha256:..."},
  "tracer": {"name": "vtracer", "version": "0.6.15", "params": {"colormode": "color", "hierarchical": "stacked"}},
  "modes": {
    "light": {"from": "given", "mismatch": 0.004, "inner_mismatch_px": 0, "colour_delta": 0.006,
              "colours": [{"traced": "#1B1B1B", "token": "text", "value": "#1A1A1A", "delta": 0.003}]},
    "dark": {"from": "derived", "colours": [{"token": "text", "value": "#EDEFF3"}]}
  },
  "gaps": [{"what": "a detail of the logo is lost", "where": "trace-light.png"}],
  "faithful": false
}
```

The readiness check script reads `faithful` and `gaps` as evidence for RB-21. That script is not in this spec.

### 4.3 `tokens.css` and `fonts.css` (generated)

- `tokens.css` holds the light values in `:root`, the dark values in `@media (prefers-color-scheme: dark)` and in
  `:root[data-theme="dark"]`, and one `--font-<role>` stack for each role.
- `fonts.css` holds one `@font-face` for each shipped font file, with `font-display: swap`. Each `url()` is relative to
  `fonts.css`, so the browser resolves it on any page and on any host.
- Each file opens with a comment that says it is generated from `tokens.json` and must not be edited.

## 5. Features and acceptance criteria

### 5.1 The contrast check

The check computes each ratio with the WCAG 2.2 definitions of
[relative luminance and contrast ratio](https://www.w3.org/TR/WCAG22/#dfn-relative-luminance) (the sRGB threshold
is 0.04045). It compares the ratio with the minimum unrounded, as the
[Understanding document for 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html) says
(4.499:1 does not meet 4.5:1).

| Foreground | Background | Kind | Minimum | Source |
| --- | --- | --- | --- | --- |
| `text`, `muted`, `accent-text` | `bg`, `surface` | text | 4.5:1 | [SC 1.4.3](https://www.w3.org/TR/WCAG22/#contrast-minimum) |
| `on-accent` | `accent` | text | 4.5:1 | SC 1.4.3 |
| `ok`, `warn`, `crit` | `bg`, `surface` | text | 4.5:1 | SC 1.4.3 |
| `accent` | `bg`, `surface` | shape | 3:1 | [SC 1.4.11](https://www.w3.org/TR/WCAG22/#non-text-contrast) |
| `border` | `bg`, `surface` | decorative | none: reported only | — |

Status colours carry messages, such as an error, so they are checked as text. Text pairs also report whether they
meet the enhanced level, 7:1 ([SC 1.4.6](https://www.w3.org/TR/WCAG22/#contrast-enhanced)), for information.

1. The check MUST test each pair in the table in the light palette and in the dark palette.
2. The check MUST use the WCAG 2.2 formula for relative luminance, with the threshold 0.04045.
3. The check MUST NOT round a ratio before it compares the ratio with the minimum.
4. A pair below its minimum MUST fail the check.
5. A failure MUST name the mode, the two tokens, the ratio and the minimum.
6. The output MUST show each ratio rounded down to two decimals.
7. A colour value that is not `#RRGGBB` MUST fail the check.
8. When all colour values are `null`, the check MUST pass and say that the palette is not set.
9. When only some colour values are `null`, the check MUST fail and name each missing token.
10. `#767676` text on a `#FFFFFF` background MUST pass (4.54:1). `#777777` MUST fail (4.47:1).

### 5.2 The font licence check

For each font role with a `family`, the check reads the evidence in its `files` folder:

- the licence file (`OFL.txt`, `UFL.txt`, `LICENSE*` or `LICENCE*`). The check knows three licences by their text:
  SIL Open Font License 1.1 (`OFL-1.1`, "SIL OPEN FONT LICENSE Version 1.1"), Apache License 2.0 (`Apache-2.0`,
  "Apache License" and "Version 2.0, January 2004") and Ubuntu Font Licence 1.0 (`UFL-1.0`, "UBUNTU FONT LICENCE
  Version 1.0"). These are the licences of the Google Fonts library's folders `ofl/`, `apache/` and `ufl/`.
- each font file (`.ttf`, `.otf`, `.woff`, `.woff2`): the family name (`name` IDs 16 and 1), the licence description
  and URL (`name` IDs 13 and 14), and the embedding flags (`OS/2.fsType`). The
  [OS/2 table](https://learn.microsoft.com/en-us/typography/opentype/spec/os2#fstype) defines usage values 0
  (installable), 2 (restricted), 4 (preview and print) and 8 (editable), bit 8 (no subsetting) and bit 9 (bitmap
  embedding only).

Each font gets one of three results:

| Result | When |
| --- | --- |
| **known open licence** | the licence file is one of the three, `licence` names the same one, and every font file agrees |
| **needs a person** | the licence file is not one of the three; or `fsType` has usage 2 or 4, or bit 9; or `name` ID 13 or 14 names another licence or a limit such as "personal use", "non-commercial", "demo", "trial" or "evaluation" |
| **missing evidence** | `files` does not exist or holds no font file; there is no licence file or more than one; `licence` differs from the licence file; or a font file's family differs from `family` |

A font with `files: null` is reported as not shipped and needs no licence evidence.

1. The check MUST give each font with a `family` exactly one result from the table.
2. Missing evidence MUST fail the check.
3. "Needs a person" MUST fail the check while the font has no `licence_review`.
4. A font with a `licence_review` MUST be reported as "read by a person", with the name and the date.
5. The check MUST NOT report a reviewed font as a known open licence.
6. Every report MUST end with this sentence: "This check compares licence files and font data. It is not legal advice."
7. The check MUST NOT use the words "legal", "allowed" or "permitted" about a font.
8. The tools MUST NOT change a font file.

### 5.3 Logo processing

**Inputs.** She brings one PNG or one per mode (design §8). `logo/source/logo.png` is for light backgrounds;
`logo/source/logo-dark.png` is for dark backgrounds. `logo` refuses an input, with a sentence the agent can relay,
when it:

- is not a PNG (checked by its first bytes, not its name);
- is larger than 8192 pixels on a side, or smaller than 512 pixels on its short side;
- has no transparent background: fewer than 20% of the pixels on its outer rows are transparent. VTracer takes
  transparency out of the trace at the same 20% rule
  ([`converter.rs`](https://github.com/visioncortex/vtracer/blob/0.6.15/cmdapp/src/converter.rs), `KEYING_THRESHOLD`).

It records a gap, and goes on, when the short side is under 1000 pixels or the PNG holds more than eight main
colours (each covering at least 0.5% of the logo's pixels), which shows gradients or a photo rather than flat colours.

**Trace.** Pixels with alpha under 128 become transparent and the others opaque. VTracer traces the result with
fixed settings: `colormode="color"`, `hierarchical="stacked"`, `mode="spline"`, `filter_speckle=4`,
`color_precision=6`, `layer_difference=16`, `corner_threshold=60`, `length_threshold=4.0`, `max_iterations=10`,
`splice_threshold=45`, `path_precision=3`. The stacked mode layers the colour regions, so no gap opens between two
colours.

**Faithfulness.** resvg renders the traced SVG, before recolouring, at the PNG's size. Then:

- **shape:** the pixels whose opaque or transparent state differs, divided by the PNG's opaque pixels, MUST be 1% or
  less;
- **detail:** after the differing pixels within 2 pixels of an edge are removed (a 5 by 5 minimum filter), differing
  pixels MUST NOT remain. This catches a lost dot or a filled hole that the shape ratio hides;
- **colour:** for each traced colour, the mean OKLab distance from her PNG's pixels inside that region MUST be 0.02 or
  less.

These limits are first values. The plan's first task tunes them on the test fixtures and on Talita's logo, and a
change to them is a change proposal. A failed limit is a gap: `trace.json` records it, `trace-<mode>.png` shows the
differing pixels in `crit` over a faded copy of her PNG, and the board shows both.

**Recolour and derive.** Each traced colour maps to the nearest colour token of the same mode, by OKLab distance.

- With one PNG, the other mode uses the dark (or light) value of the same tokens. A white shape inside a dark mark
  maps to `bg`, so it follows the background in the other mode.
- With two PNGs, each is traced and mapped in its own mode. Nothing is derived.
- A traced colour farther than 0.05 from every token is kept unchanged in both modes and recorded. When a kept colour
  is under 3:1 against `bg` of a mode, that is a gap: "the logo may be hard to see on dark backgrounds".

**Exports.**

| File | Content |
| --- | --- |
| `logo.svg`, `logo-dark.svg` | the recoloured traces for light and dark backgrounds |
| `favicon.svg` | the logo fitted into a square, light colours, with a `prefers-color-scheme: dark` style that switches to the dark colours |
| `favicon.ico` | 16, 32 and 48 pixels, each rendered by resvg at its own size, transparent background |
| `icon-192.png`, `icon-512.png` | the light logo on the light `bg`, opaque, inside the maskable safe zone: a centred circle with a radius of 40% of the icon ([Web App Manifest §2.3](https://www.w3.org/TR/appmanifest/#icon-masks)) |

A logo wider than 1.5 times its height gives a hard-to-read favicon: that is a gap.

1. `logo` MUST refuse each input that §5.3 lists, with exit code 2 and a plain sentence.
2. `logo` MUST trace with VTracer 0.6.15 and the fixed settings in §5.3.
3. `logo` MUST compute the shape, detail and colour results for each given PNG.
4. A failed limit MUST be a gap in `trace.json` and on the board.
5. `logo` MUST NOT change or remove a gap to make the trace look faithful.
6. With one PNG, `logo` MUST derive the other mode from the same tokens.
7. With two PNGs, `logo` MUST NOT derive a mode.
8. Each SVG MUST hold only the elements `svg` and `path`. `favicon.svg` MAY also hold one `style` element.
9. Each SVG MUST hold a `viewBox` and no comment, script, link or external reference.
10. `favicon.ico` MUST hold the sizes 16, 32 and 48.
11. Each PNG icon MUST be opaque, and its logo MUST be inside the safe-zone circle.
12. Two runs on the same inputs MUST write byte-identical files.
13. `logo` MUST NOT write outside `docs/7-branding/identity/logo/`.

VTracer writes a comment that names itself (`<!-- Generator: visioncortex VTracer ... -->`,
[`svg.rs`](https://github.com/visioncortex/vtracer/blob/0.6.15/cmdapp/src/svg.rs)) and sets no `viewBox`. Criteria 8
and 9 remove and add these.

### 5.4 The brand board

`brand.sh board` writes `docs/7-branding/identity/board.md`, a page of the company's docs. It shows, in order:

1. **Palette:** a light panel on light `bg` and a dark panel on dark `bg`, side by side in either site theme.
   Each token is a swatch with its name and value. Under each panel, the contrast table: each pair, its ratio, its
   minimum and "passes" or "fails" in words, never by colour alone.
2. **Type:** each role in its own font and weights, from `fonts.css`, with its licence result in words.
3. **Logo:** her PNG, `logo.svg` on light `bg` and `logo-dark.svg` on dark `bg`, side by side. Then the colour
   mapping, the favicon at 16, 32 and 48 pixels, and the icons inside a circle mask. Then "Faithful", or each gap with
   its numbers and `trace-<mode>.png`.
4. **Sample images:** the images in `docs/7-branding/imagery/`, if any, beside a strip of the palette (see §10).
5. **Open items:** every gap and every font that needs a person, in plain words.

**Rendering.** The board is Markdown with HTML blocks (`md_in_html` and `attr_list`, both on in the template's
`mkdocs.yml`). Images use Markdown image syntax, so the strict build checks each link. The page uses relative links
only, no script and no external URL. So it renders the same through `company-site.sh` on 127.0.0.1 today, and on any
static host later, under any path. Hosting a private preview is not in this spec.

**No tool names.** The board's fixed text is plain English with no tool names. It opens with a comment that says it is
generated and must not be edited, a `markdownlint-disable MD033` comment (its swatches need inline HTML), and a
SHA-256 of its inputs: `tokens.json`, `fonts.css`, the font files, the files in `logo/`, and the sample images.

1. `board` MUST show the five parts in the order of §5.4.
2. The board MUST show the light and the dark palette at the same time.
3. Each result MUST be in words. Colour MUST NOT be the only sign of a result.
4. The board MUST use no script, no external URL and no absolute link.
5. The company's docs MUST build with `mkdocs build --strict` after `board` runs.
6. `names-check.sh` MUST pass on a company after `logo` and `board` run.
7. `board --check` and `brand.py board-fresh` MUST fail when an input changed after `board` ran.
8. `brand.py board-fresh` MUST pass on the template's placeholder board, which has no input hash.

### 5.5 Where they run

| Tool | Agent, at step 6 | Company CI (`run.sh`) | Asgard CI (`ci.yml`) |
| --- | --- | --- | --- |
| contrast check | `brand.py contrast` | yes, in `brand.py check` | through `brand-checks.test.sh` |
| font licence check | `brand.py fonts` | yes; `checks.yml` installs `fonttools[woff]==4.66.1` and `brotli==1.2.0` | same |
| generated files fresh | `brand.py tokens --write` | yes | same |
| logo processing | `brand.sh logo` | no: it writes files | through `brand.test.sh` |
| brand board | `brand.sh board` | freshness only (`board-fresh`) | through `brand.test.sh` |

1. `run.sh` MUST run `brand.py check` as one step.
2. A fresh scaffold MUST pass `run.sh`.
3. `brand.sh logo` and `brand.sh board` MUST NOT open a network connection.

## 6. Template changes

- `tokens.json`: `files`, `licence` and `source` per font; `type.licence` removed (§4.1).
- `tokens.css`, `fonts.css`: placeholder comments, replaced by `brand.py tokens --write`.
- `identity/board.md`: a placeholder page ("The brand board appears here once the palette, the fonts and the logo
  are in."), linked from `identity/README.md`.
- `logo/README.md`: the source files and the generated files of §2.
- `.ouroboric/mkdocs.yml`: `extra_css: [7-branding/identity/fonts.css]`.
- `.ouroboric/checks/brand.py`, the `run.sh` step, and the `checks.yml` install line.

## 7. Security considerations

- **Untrusted input.** Her PNG can come from anywhere. `logo` checks the PNG signature and the size before Pillow
  decodes the image, so a decompression bomb is refused.
- **Safe SVG output.** The SVGs hold only the elements of §5.3, with no script and no external reference, so a page
  or a product can inline them.
- **Supply chain.** Python packages install from wheels only, with hashes. The resvg binary is checked against its
  SHA-256. Nothing installs globally. Updates arrive as pull requests that change `requirements.txt` or `resvg.lock`.
- **Offline.** After `setup`, no tool uses the network. The checks read only the repository's files.
- **Privacy.** Her logo and sample images stay in her private repository and on the machine that runs the tools.
  `company-site.sh` serves the board on 127.0.0.1 only.
- **No secrets.** No tool reads or needs a token.

## 8. Testing approach

Test first, in bash, like the existing `scripts/tests/*.test.sh`. Each test scaffolds a company with
`new-company.sh` in a temporary folder.

- `brand-checks.test.sh` covers §5.1, §5.2 and the freshness rules. It writes palettes with known ratios
  (criterion 5.1.10). It builds test fonts with fontTools' `FontBuilder`, with the `name` and `fsType` values each
  case needs, and writes short licence files. No font file is committed.
- `brand.test.sh` covers §5.3 and §5.4. It draws its PNG fixtures with Pillow: a two-colour mark that traces
  faithfully, a mark with a 3-pixel dot that `filter_speckle` drops (a gap), a wide wordmark, an opaque background,
  and an image that is too small. It checks the files, `trace.json`, the strict build, `names-check.sh`, byte-identical
  re-runs, and `board --check` after a token changes.
- Criterion 5.5.3 is checked in two ways: `brand.py`, `logo.py` and `board.py` import no network module (`socket`,
  `urllib`, `http`), and resvg does not fetch external resources
  ([resvg README](https://github.com/linebender/resvg/blob/main/README.md): no `a` or `script` elements).
- Asgard's `ci.yml` runs `brand.sh setup` before the tests. The pr-bot cannot change workflows, so the operator
  pushes that change.
- CI runs on Linux only. VTracer wheels and resvg binaries exist for macOS, but the shared MacBook is not tested in
  CI.

## 9. Decisions

**Decided 2026-10-26:** VTracer 0.6.15 (MIT) traces the logo. It traces colour images in one pass, and its stacked
mode leaves no gaps between colours. Potrace 1.16 (GPL-2.0-or-later, last release 2019-09-17) traces black and white
only: each colour would need its own trace and our own colour separation, and separate traces leave hairline gaps.
AutoTrace (GPL-2.0, last release 0.31.10 in January 2024) is less active. Inkscape's Trace Bitmap uses Potrace inside
a desktop application. imagetracerjs (Unlicense) has had no change since 2023. Each licence would allow running the
tool. The choice rests on colour, gaps and maintenance.

**Decided 2026-10-26:** The stable VTracer 0.6.15 is pinned, not the 1.0 alphas. VTracer 1.0 adds `--palette`, which
snaps colours to given values during the trace. A later change can adopt it when 1.0 is stable.

**Decided 2026-10-26:** resvg renders SVG to PNG. It is a single binary with no system libraries, and it has no
script support.

**Decided 2026-10-26:** The contrast and font checks are company checks in the template, so the company's CI runs
them without Asgard. Logo processing and the board are Asgard scripts, because the design keeps Asgard outside her
repository (§6.1) and they write files.

**Decided 2026-10-26:** Status colours are checked as text (4.5:1). Borders are decorative and only reported.

**Decided 2026-10-26:** A font flagged "needs a person" fails the check until a person's reading is recorded in
`tokens.json`. The check never says a licence allows a use.

**Decided 2026-10-26:** A trace that is not faithful does not stop the tools. It is a gap on the board, and she
decides at the `brand` stop.

**Decided 2026-10-26:** The board is a page of the company's docs, so every host of the docs shows it.

## 10. Open questions for the founder

The operator answers these as the Ouroboric founder who approves this spec. Questions marked (Talita) need her
answer, through her helper. Until an answer, the spec uses the default given.

1. **Her PNG in the repository.** The docs standard keeps raw sources out of the repository and commits only final
   vectors and exports. Re-runs, the board and the faithfulness check need her PNG. Default: commit it in
   `logo/source/`.
2. **Sample images (Talita).** The design puts sample images on the board; the template's `imagery.md` links images
   and does not copy them. Default: up to six images she chooses, copied at 1600 pixels or less into
   `docs/7-branding/imagery/`. A photo that shows a client needs that client's consent, which the tools flag for a
   person and do not judge.
3. **A square mark for the favicon.** A wordmark gives a favicon nobody can read at 16 pixels. The design takes one
   PNG or one per mode. Default: the favicon comes from the logo, with a gap when the logo is wide. Alternative: accept
   a third, optional PNG, a square mark.
4. **Logo colours outside the palette.** The design recolours the logo with the palette tokens. Default: a logo colour
   with no near token is kept unchanged and flagged. Alternative: add a `brand` token to both palettes for it.
5. **Who may record a font review.** "Asgard is not a lawyer" makes the check flag non-open licences. Default: the
   founder, or a person she names, records the reading. Is a font licence a legal item that needs a qualified person?
6. **How Talita sees the board.** She cannot open 127.0.0.1, and GitHub's Free plan serves no pages for private
   repositories (run log, entry 4). Until a private preview exists, does she review the board on her helper's
   screen?
7. **Red checks at the `brand` stop.** On the Free plan, a failed check does not block a merge (run log, entry 5).
   Default: the agent does not ask her to merge while `run.sh` fails, and the board lists every open item.
8. **Where this spec lives.** Design §5.2 places specs in the `yggdrasil` umbrella and keeps the Asgard leaf to
   `README.md`, `AGENTS.md` and `docs/architecture.md`. This spec is in the Asgard leaf at the operator's request.

## 11. Not in this spec

- Making the logo, the palette or the font choices: the founder's work, with the step 6 skill in Havamal.
- The step 6 kickstart skill and its eval.
- The readiness check script, which reads `trace.json` and the check results for RB-21.
- A hosted private preview, and the pull request's link to the rendered board.
- Converting or subsetting fonts for the web: the web realm's build, from the files as published.
- The full logo system and usage rules (RL-06, level 2).
- The moodboard of step 6.
- Prose checks (Vale) for the board's text.

## 12. Deviations from the design doc

None in what the tools do. The spec's location differs from design §5.2 (question 8).

## 13. Not verified

- The resvg binaries' SHA-256 values: the plan's first task records them in `resvg.lock` when it downloads them.
- resvg's output on the fixtures: this spec relies on its documentation; it was not run while writing.
- VTracer was run once on a generated two-colour PNG while writing: the transparent background was left out, the
  output was byte-identical across two runs, and the paths kept the two colours. The faithfulness limits are not yet
  measured. The 0.6.15 wheel writes "0.6.12" in its generator comment, which criterion 5.3.9 removes in any case.
