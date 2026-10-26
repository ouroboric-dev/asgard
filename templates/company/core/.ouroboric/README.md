# .ouroboric

Configuration of the tools that set up this company (Asgard, a realm of Yggdrasil) and build its products. It is
kept here, and only here, so that no tool's name or setting appears in the company's own files.

- `company.yaml`: where this umbrella came from: the template version, the date, the add-ons, the founders.
- `standards.yaml` (with the yggdrasil add-on): the standards the company follows, at a pinned version.
- `mkdocs.yml`: the company's docs as pages, to review on this machine only: Asgard's `company-site.sh serve`
  shows them at <http://127.0.0.1:8000>. The built pages go to `site/`, which git ignores.
