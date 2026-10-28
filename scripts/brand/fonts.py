"""Candidate typefaces for step 6c (brand tools spec §3.2): fetch each candidate's files and licence from an open
library, read its facts from the files, and write them where the typography page and the agent read them.

    fonts.py DIR CANDIDATES.json

CANDIDATES.json: {"languages": ["pt"], "candidates": [{"id": "x", "family": "Name", "dir": "name",
"files": ["Name[wght].ttf"], ...}]}. `dir` is the library folder and `files` the files to fetch from it; every other
field travels into the facts. The facts come from the files, never from the candidates file: a face with no italic
file is reported without italic whatever the candidates file claims.

The library is ASGARD_FONTS_BASE (default the Google Fonts repository's ofl/ folder; https, or a local folder as
file://). Downloads are kept in ASGARD_FONTS_DIR (default the cache folder) and used again without the network.
"""
import hashlib
import json
import os
import re
import sys
import urllib.parse
import urllib.request

BASE = "https://github.com/google/fonts/raw/main/ofl"
LICENCES = ("OFL.txt", "LICENSE.txt", "UFL.txt")
FILE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 _.,\[\]-]*\.(ttf|otf|woff2)$")
DIR_NAME = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
LIMIT = 40 * 1024 * 1024
OUT = ".ouroboric/choices/fonts-facts.json"


class Refused(Exception):
    pass


def library():
    base = os.environ.get("ASGARD_FONTS_BASE", BASE).rstrip("/")
    if not base.startswith(("https://", "file://")):
        raise Refused(f"the library address {base} is not https or a local folder (file://)")
    return base


def downloads():
    return os.environ.get("ASGARD_FONTS_DIR") or os.path.join(
        os.environ.get("XDG_CACHE_HOME") or os.path.expanduser("~/.cache"), "asgard", "fonts")


def fetch(base, folder, directory, name, optional=False):
    """The file in the downloads folder: kept from an earlier run, else fetched. None when optional and absent."""
    target = os.path.join(folder, name)
    if os.path.isfile(target) and os.path.getsize(target) > 0:
        return target
    url = f"{base}/{urllib.parse.quote(directory)}/{urllib.parse.quote(name)}"
    try:
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read(LIMIT + 1)
    except (OSError, ValueError) as e:
        if optional:
            return None
        raise Refused(f"could not fetch {name} from {directory} of the library ({e})")
    if len(data) > LIMIT:
        raise Refused(f"{name} is over {LIMIT // (1024 * 1024)} MB: refused")
    os.makedirs(folder, exist_ok=True)
    tmp = target + ".part"
    with open(tmp, "wb") as fh:
        fh.write(data)
    os.replace(tmp, target)
    return target


def sha256(path):
    with open(path, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def facts_for(brand, cand, base, root, languages):
    directory = cand.get("dir")
    if not isinstance(directory, str) or not DIR_NAME.match(directory):
        raise Refused(f"candidate {cand.get('id')}: dir {directory!r} is not a folder name of the library")
    names = cand.get("files")
    if not isinstance(names, list) or not names or not all(isinstance(n, str) and FILE_NAME.match(n) for n in names):
        raise Refused(f"candidate {cand.get('id')}: files must be plain font file names (.ttf, .otf or .woff2)")
    folder = os.path.join(root, directory)
    paths = [fetch(base, folder, directory, n) for n in names]
    licence = None
    for name in LICENCES:
        licence = fetch(base, folder, directory, name, optional=True)
        if licence:
            break
    notes = []
    fonts = [brand.open_font(p) for p in paths]
    facts = {k: v for k, v in cand.items() if k not in ("files", "italic")}
    facts["folder"] = folder
    facts["files"] = []
    ranges, statics = set(), set()
    for name, path, font in zip(names, paths, fonts):
        lo, hi = brand.font_weights(font)
        facts["files"].append({"name": name, "sha256": sha256(path), "bytes": os.path.getsize(path),
                               "weights": {"min": lo, "max": hi}, "italic": brand.font_is_italic(font)})
        (ranges if lo != hi else statics).add((lo, hi))
    ranges = sorted(ranges)
    statics = sorted(s for s in statics if not any(a <= s[0] <= b for a, b in ranges))
    facts["weights"] = [{"min": lo, "max": hi} for lo, hi in sorted(ranges + statics)]
    italic_files = [f["name"] for f in facts["files"] if f["italic"]]
    facts["italic"] = bool(italic_files)
    facts["italic_from"] = italic_files[0] if italic_files else None
    if "italic" in cand and cand["italic"] != facts["italic"]:
        notes.append(f"the candidates file says italic is {'there' if cand['italic'] else 'missing'}; "
                     f"the font files {'have' if facts['italic'] else 'have no'} one: the files are right")
    family = brand.font_facts(paths[0])[0]
    facts["family_in_file"] = family
    if cand.get("family") and family != cand["family"]:
        notes.append(f"the files name the family {family}, not {cand['family']}")
    for p, name in zip(paths, names):
        if brand.font_facts(p)[3] & 0x000F in (2, 4):
            notes.append(f"{name} limits its embedding: a person reads its licence")
    glyphs = {}
    for lang in languages:
        chars = brand.required_characters(lang)
        if chars is None:
            glyphs[lang] = {"covers": None, "missing": None, "examples": [],
                            "note": "no list of characters for this language"}
            continue
        gone = max(([c for c in chars if ord(c) not in set(f.getBestCmap())] for f in fonts), key=len)
        glyphs[lang] = {"covers": not gone, "missing": len(gone), "examples": gone[:5]}
    facts["glyphs"] = glyphs
    if licence:
        with open(licence, encoding="utf-8", errors="replace") as fh:
            spdx = brand.known_licence(fh.read())
        facts["licence"] = {"file": os.path.basename(licence), "spdx": spdx, "sha256": sha256(licence)}
        if spdx is None:
            notes.append("the licence file is not one the tool knows: a person reads it before the face is used")
    else:
        facts["licence"] = {"file": None, "spdx": None, "sha256": None}
        notes.append("the library folder has no licence file: a person finds the licence before the face is used")
    facts["notes"] = notes
    return facts


def main(argv):
    if len(argv) != 2:
        print("usage: brand.sh fonts DIR CANDIDATES.json", file=sys.stderr)
        return 2
    company, candidates = argv
    try:
        with open(candidates, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"brand.sh fonts: cannot read {candidates} as JSON ({e})", file=sys.stderr)
        return 2
    try:
        if not isinstance(spec, dict) or not isinstance(spec.get("candidates"), list) or not spec["candidates"]:
            raise Refused(f"{candidates} needs a list of candidates")
        checks = os.path.join(company, ".ouroboric", "checks")
        if not os.path.isfile(os.path.join(checks, "brand.py")):
            raise Refused(f"{company} is not a company folder: no .ouroboric/checks/brand.py")
        sys.dont_write_bytecode = True
        sys.path.insert(0, os.path.abspath(checks))
        import brand
        languages = spec.get("languages")
        if not isinstance(languages, list):
            try:
                with open(os.path.join(company, "docs/7-branding/identity/tokens.json"), encoding="utf-8") as fh:
                    languages = json.load(fh).get("languages")
            except (OSError, ValueError):
                languages = None
        languages = [str(x) for x in languages] if isinstance(languages, list) and languages else ["en"]
        base, root = library(), downloads()
        results = [facts_for(brand, c, base, root, languages) for c in spec["candidates"] if isinstance(c, dict)]
    except Refused as e:
        print(f"brand.sh fonts: {e}", file=sys.stderr)
        return 2
    out = os.path.join(company, OUT)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        json.dump({"languages": languages, "candidates": results}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    for f in results:
        weights = ", ".join(f"{w['min']:g}" if w["min"] == w["max"] else f"{w['min']:g} to {w['max']:g}" for w in f["weights"])
        covers = "; ".join(f"{lang}: " + ("covered" if g["covers"] else "not checked" if g["covers"] is None
                                           else f"{g['missing']} characters missing") for lang, g in f["glyphs"].items())
        print(f"{f.get('id', f['family_in_file'])}: {f['family_in_file']}: weights {weights}; "
              f"{'italic' if f['italic'] else 'no italic'}; {covers}; licence {f['licence']['spdx'] or 'unknown'}")
        for note in f["notes"]:
            print(f"  note: {note}")
    print(f"The facts are written: {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
