# .ouroboric

The settings of the tools that set up this company and build its products. They are kept here, and only here, so
that no tool's name or setting appears in the company's own files.

- `company.yaml`: where this umbrella came from: the template version, the date, the add-ons, the founders.
- `standards.yaml` (when the company builds with the factory): the standards the company follows, at a pinned version.
- `mkdocs.yml`: the company's docs as pages, to review on this machine only, at <http://127.0.0.1:8000>. The built pages go to `site/`, which git ignores.
- `checks/`: the checks these tools add to the company's own. `run.sh` runs them all: the repository's lint
  hooks (`.pre-commit-config.yaml` at the root) and secrets over the whole history, then the docs (`docs-check.py`:
  the docs standard's front matter, dated names and links), the brand (`brand.py`: the palettes' contrast, the
  fonts' licence evidence, the generated `tokens.css` and `fonts.css`, and whether the brand board matches its
  inputs), the strict page build, and `names-check.sh` (no tool names outside this folder). The CI
  (`.github/workflows/checks.yml`) runs `run.sh` on every pull request.
