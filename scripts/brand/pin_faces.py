"""Pin the curated typefaces: turn faces-source.json into faces.json (a maintainer's tool, not the agent's).

    pin_faces.py --ref COMMIT [--listing FILE] [--max-kb N] [--max-files N] SOURCE OUT

Fetches each face's files and licence at one commit of the Google Fonts repository and records their SHA-256, so that
a page built from the curated list can refuse a file that is not the one reviewed. The listing of the repository's `ofl/`
folder is read from the GitHub API once (or from --listing, a JSON {folder: [[file, bytes], ...]}). A face is left out,
and said so, when its folder is not in the library at that commit, it has no licence file, it has more than 4 font
files, or its files are over 3000 KB: prefer variable families. Prints a review table (weights, italic, glyph coverage of
the languages the tools know) for the person who reviews the voices and roles. ASGARD_FONTS_BASE changes the library, as
for brand.sh fonts. Exit 0 when faces.json is written.
"""
import argparse
import hashlib
import json
import os
import sys
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "templates", "company", "core", ".ouroboric", "checks"))
sys.dont_write_bytecode = True
import brand  # noqa: E402

KIND = {"formal-script": "script", "casual-script": "script", "handwriting": "script", "mono": "mono"}
SERIF = {"old-style-serif", "text-serif", "high-contrast-serif", "soft-serif", "slab-serif"}
LANGS = ("en", "pt", "de", "es", "fr")


def get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "asgard", "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def listing_from_api(ref):
    root = json.loads(get(f"https://api.github.com/repos/google/fonts/git/trees/{ref}"))
    ofl = next(t for t in root["tree"] if t["path"] == "ofl")
    tree = json.loads(get(f"https://api.github.com/repos/google/fonts/git/trees/{ofl['sha']}?recursive=1"))
    if tree.get("truncated"):
        raise SystemExit("pin_faces: the library's listing was truncated")
    out = {}
    for t in tree["tree"]:
        if t["type"] == "blob" and t["path"].endswith(".ttf"):
            folder, _, name = t["path"].partition("/")
            out.setdefault(folder, []).append([name, t["size"]])
    return out


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", required=True)
    ap.add_argument("--listing")
    ap.add_argument("--max-kb", type=int, default=3000)
    ap.add_argument("--max-files", type=int, default=4)
    ap.add_argument("source")
    ap.add_argument("out")
    args = ap.parse_args(argv)
    with open(args.source, encoding="utf-8") as fh:
        source = json.load(fh)
    if args.listing:
        with open(args.listing, encoding="utf-8") as fh:
            listing = json.load(fh)
    else:
        listing = listing_from_api(args.ref)
    base = os.environ.get("ASGARD_FONTS_BASE", f"https://github.com/google/fonts/raw/{args.ref}/ofl").rstrip("/")
    directions, faces, left_out, table = [], [], [], []
    for d in source["directions"]:
        directions.append({k: d[k] for k in ("id", "name", "text", "voices", "suits")})
        for tier in ("start", "deeper"):
            for fid, family, note in d[tier]:
                files = sorted(listing.get(fid, []))
                if not files:
                    left_out.append(f"{family}: not in the library at this commit")
                    continue
                if len(files) > args.max_files or sum(s for _, s in files) > args.max_kb * 1024:
                    left_out.append(f"{family}: {len(files)} files, {sum(s for _, s in files) // 1024} KB: too heavy, prefer a variable family")
                    continue
                try:
                    licence = get(f"{base}/{fid}/OFL.txt")
                except OSError:
                    left_out.append(f"{family}: no OFL.txt")
                    continue
                spdx = brand.known_licence(licence.decode("utf-8", "replace"))
                if spdx != "OFL-1.1":
                    left_out.append(f"{family}: its licence file is not the OFL 1.1 ({spdx})")
                    continue
                pinned, facts = [], []
                for name, _ in files:
                    data = get(f"{base}/{fid}/{urllib.parse.quote(name)}")
                    pinned.append({"name": name, "sha256": hashlib.sha256(data).hexdigest(), "bytes": len(data)})
                    tmp = os.path.join(os.environ.get("TMPDIR", "/tmp"), f"pin-{fid}-{len(pinned)}.ttf")
                    with open(tmp, "wb") as fh:
                        fh.write(data)
                    font = brand.open_font(tmp)
                    facts.append((brand.font_weights(font), brand.font_is_italic(font), set(font.getBestCmap())))
                    os.remove(tmp)
                kind = KIND.get(d["id"], "serif" if d["id"] in SERIF else "sans")
                faces.append({"id": fid, "family": family, "dir": fid, "kind": kind, "direction": d["id"], "tier": tier,
                              "voices": d["voices"], "suits": d["suits"], "note": note, "licence": "OFL-1.1",
                              "licence_sha256": hashlib.sha256(licence).hexdigest(), "files": pinned})
                cover = []
                for lang in LANGS:
                    need = brand.required_characters(lang)
                    miss = max(len([c for c in need if ord(c) not in cm]) for _, _, cm in facts)
                    cover.append(f"{lang}:{'ok' if not miss else '-' + str(miss)}")
                weights = ", ".join(sorted({f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}" for (lo, hi), _, _ in facts}))
                table.append(f"| {d['id']} | {tier} | {family} | {len(files)} | {sum(p['bytes'] for p in pinned) // 1024} | {weights} | "
                             f"{'yes' if any(i for _, i, _ in facts) else 'no'} | {' '.join(cover)} |")
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump({"library": "https://github.com/google/fonts", "ref": args.ref, "licence_file": "OFL.txt",
                   "directions": directions, "faces": faces}, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    print("| direction | tier | family | files | KB | weights | italic | coverage |")
    print("| --- | --- | --- | --- | --- | --- | --- | --- |")
    print("\n".join(table))
    for line in left_out:
        print(f"left out: {line}")
    print(f"pinned {len(faces)} faces in {len(directions)} directions at {args.ref[:10]}: {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
