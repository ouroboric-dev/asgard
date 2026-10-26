#!/usr/bin/env python3
"""The docs check: docs are checked like code. Prints each finding as `path: what is wrong`, and fails if any.

- Every doc in docs/ has front matter: title, status (draft, accepted, implemented, superseded), a real date
  (YYYY-MM-DD), related (a list of links that resolve) and, if set, a style from the writing styles.
- Research notes and journal entries are dated: docs/5-research/ and docs/6-journal/ hold YYYY-MM-DD-<slug>.md.
- Every relative link in a Markdown file resolves. In docs/, a link names a file, not a bare folder, because the
  pages can't follow a folder.

    python3 .ouroboric/checks/docs-check.py
"""
import datetime
import os
import re
import subprocess
import sys

STATUSES = {"draft", "accepted", "implemented", "superseded"}
STYLES = {
    "direction", "spec", "guide", "procedure", "reference", "public-help", "legal", "research", "journal",
    "brand-story", "marketing", "ui-copy", "prompt", "agent-facing",
}
DATED_FOLDERS = ("docs/5-research/", "docs/6-journal/")
DATED_NAME = re.compile(r"^(\d{4}-\d{2}-\d{2})-[a-z0-9]+(-[a-z0-9]+)*\.md$")
LINK = re.compile(r"!?\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
FENCE = re.compile(r"^\s*(```|~~~)")
CODE_SPAN = re.compile(r"`[^`]*`")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)

findings = []


def find(path, message):
    findings.append(f"{path}: {message}")


def real_date(value):
    try:
        datetime.date.fromisoformat(value)
        return re.fullmatch(r"\d{4}-\d{2}-\d{2}", value) is not None
    except ValueError:
        return False


def front_matter(path, lines):
    """The front matter's keys, as plain `key: value` lines; None if the doc has none."""
    if not lines or lines[0].strip() != "---":
        return None
    keys = {}
    for line in lines[1:]:
        if line.strip() == "---":
            return keys
        m = re.match(r"^([a-z_]+):\s*(.*?)\s*$", line)
        if m:
            keys[m.group(1)] = m.group(2)
    find(path, "front matter is not closed with ---")
    return keys


def resolves(base_dir, target):
    return os.path.exists(os.path.normpath(os.path.join(base_dir, target)))


def check_front_matter(path, lines):
    keys = front_matter(path, lines)
    if keys is None:
        find(path, "no front matter (title, status, date, related, style)")
        return
    if not keys.get("title"):
        find(path, "front matter has no title")
    status = keys.get("status")
    if status is None:
        find(path, "front matter has no status")
    elif status not in STATUSES:
        find(path, f"status '{status}' is not one of {', '.join(sorted(STATUSES))}")
    date = keys.get("date")
    if date is None:
        find(path, "front matter has no date")
    elif not real_date(date):
        find(path, f"date '{date}' is not a real date (YYYY-MM-DD)")
    related = keys.get("related")
    if related is None:
        find(path, "front matter has no related (use [] for none)")
    elif not (related.startswith("[") and related.endswith("]")):
        find(path, "related is not a list: related: [a.md, b.md]")
    else:
        for item in filter(None, (i.strip() for i in related[1:-1].split(","))):
            if not resolves(os.path.dirname(path), item.split("#")[0]):
                find(path, f"related doc '{item}' does not exist")
    style = keys.get("style")
    if style is not None and style not in STYLES:
        find(path, f"style '{style}' is not one of the writing styles")


def check_name(path):
    name = os.path.basename(path)
    if name == "README.md" or not path.startswith(DATED_FOLDERS):
        return
    m = DATED_NAME.match(name)
    if not m or not real_date(m.group(1)):
        find(path, "research notes and journal entries are named YYYY-MM-DD-<slug>.md")


def check_links(path, text):
    in_docs = path.startswith("docs/")
    fenced = False
    for line in COMMENT.sub("", text).splitlines():
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        for target in LINK.findall(CODE_SPAN.sub("", line)):
            if re.match(r"^[a-z][a-z0-9+.-]*:", target, re.IGNORECASE) or target.startswith("#"):
                continue
            target = target.split("#")[0]
            full = os.path.normpath(os.path.join(os.path.dirname(path), target))
            if not os.path.exists(full):
                find(path, f"link '{target}' does not resolve")
            elif in_docs and os.path.isdir(full):
                find(path, f"link '{target}' is a folder; link its README.md, the pages can't follow a folder")


def main():
    root = subprocess.run(["git", "rev-parse", "--show-toplevel"], capture_output=True, text=True, check=True)
    os.chdir(root.stdout.strip())
    files = subprocess.run(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard", "--", "*.md"],
        capture_output=True, text=True, check=True,
    ).stdout.split("\0")
    for path in sorted(f for f in files if f and os.path.isfile(f)):
        with open(path, encoding="utf-8") as fh:
            text = fh.read()
        if path.startswith("docs/"):
            check_front_matter(path, text.splitlines())
            check_name(path)
        check_links(path, text)
    for line in findings:
        print(line)
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
