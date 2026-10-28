"""Logo proposals for step 6a (brand tools spec §3.2): the review page for the founder's concept and the agent's
alternatives, and the chosen design as the logo's source PNGs.

    proposals.py --resvg PATH DIR CANDIDATES.json [--choose ALTERNATIVE[:FACE]|saved]

CANDIDATES.json: {"name": "Example Studio", "faces": ["plain", "ring"], "alternatives": [{"id": "a", "name": "...",
"strength": "...", "risk": "...", "fails_at": 24, "lettering": false, "image": "path", "mark": "path"}, ...]}.
An alternative without lettering is one image (`image`). One with lettering is a `mark` and the company's name set in the
lettering face (`layout` beside or above), or, with `replaces_letter`, the mark in the place of that letter in the name.
`symbol_in` names the letter whose counter holds the symbol. `faces` are ids in docs/7-branding/identity/choices/fonts-facts.json
(brand.sh fonts); each pairing of alternative and face is checked before the page shows it, and a pairing that does not
work carries a visible note. Paths are inside DIR. Colours come from the palette in tokens.json when it is set, else a
neutral one. Writes docs/7-branding/identity/choices/logo-proposals.html;
with --choose, also logo/source/ and choices/logo.json.
"""
import argparse
import base64
import io
import json
import math
import os
import re
import subprocess
import sys
import tempfile

from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # brand.sh runs this file isolated (-I)
import choicepage  # noqa: E402
import fonts as library  # noqa: E402

CHOICES = "docs/7-branding/identity/choices"
IDENTITY = "docs/7-branding/identity"
HEX = re.compile(r"^#[0-9A-Fa-f]{6}$")
NEUTRAL = {"light": {"bg": "#FFFFFF", "text": "#1A1A1A", "accent": "#0B5FCC", "muted": "#555555"},
           "dark": {"bg": "#121212", "text": "#EDEDED", "accent": "#6EA8FE", "muted": "#B0B0B0"}}
LOGO_SIZES, MARK_SIZES = (16, 24, 32, 48), (16, 32, 64)
MIN_SYMBOL_PX, SYMBOL_LIMIT = 5, 24
SLUG = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class Refused(Exception):
    pass


def rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def inside(company, rel):
    root = os.path.realpath(company)
    path = os.path.realpath(os.path.join(root, rel))
    if not path.startswith(root + os.sep) or not os.path.isfile(path):
        raise Refused(f"{rel}: not a file inside the company folder")
    return path


def read_png(company, rel):
    path = inside(company, rel)
    with open(path, "rb") as fh:
        if fh.read(8) != b"\x89PNG\r\n\x1a\n":
            raise Refused(f"{rel} is not a PNG")
    im = Image.open(path)
    im.load()
    return im.convert("RGBA")


def colours_of(company):
    """{mode: {bg, text, accent, muted}}: the palette when each is set, else the neutral colours."""
    try:
        with open(os.path.join(company, IDENTITY, "tokens.json"), encoding="utf-8") as fh:
            tokens = json.load(fh)
    except (OSError, ValueError):
        tokens = {}
    out = {}
    for mode in ("light", "dark"):
        pal = tokens.get(mode) or {}
        ok = all(isinstance(pal.get(k), str) and HEX.match(pal[k]) for k in ("bg", "text", "accent", "muted"))
        out[mode] = {k: pal[k].upper() for k in NEUTRAL[mode]} if ok else dict(NEUTRAL[mode])
    return out


def recolour(im, targets):
    """The flat colours of `im`, most frequent first, become `targets` in order (the last repeats); the alpha is binary."""
    alpha = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    solid = Image.new("RGB", im.size, (0, 0, 0))
    solid.paste(im.convert("RGB"), mask=alpha)
    counts = {c: n for n, c in (solid.getcolors(1 << 24) or [])}
    counts[(0, 0, 0)] = counts.get((0, 0, 0), 0) - alpha.histogram()[0]
    found = [c for c, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])) if n > 0][:8]
    if not found:
        raise Refused("an image has no opaque pixel")
    src = Image.new("P", (1, 1))
    src.putpalette([v for c in found for v in c])
    q = solid.quantize(palette=src, dither=Image.Dither.NONE)
    dst = [rgb(targets[min(i, len(targets) - 1)]) for i in range(len(found))]
    q.putpalette([v for c in dst for v in c])
    out = q.convert("RGBA")
    out.putalpha(alpha)
    return out


def snap(im, colours):
    """Flatten an anti-aliased render to the given colours with a binary alpha, as the logo tool expects its input."""
    alpha = im.getchannel("A").point(lambda v: 255 if v >= 128 else 0)
    pal = Image.new("P", (1, 1))
    pal.putpalette([v for c in colours for v in rgb(c)])
    solid = Image.new("RGB", im.size, rgb(colours[0]))
    solid.paste(im.convert("RGB"), mask=alpha)
    out = solid.quantize(palette=pal, dither=Image.Dither.NONE).convert("RGBA")
    out.putalpha(alpha)
    return out


def data_uri(im):
    buf = io.BytesIO()
    im.save(buf, "PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode()


def counter_diameter(font_path, letter):
    """The largest circle in the counter of a letter, as a fraction of the em; None when the letter has no counter."""
    em = 240
    font = ImageFont.truetype(font_path, em)
    im = Image.new("L", (520, 520), 0)
    ImageDraw.Draw(im).text((60, 60), letter, font=font, fill=255)
    outside = im.copy()
    ImageDraw.floodfill(outside, (0, 0), 128)
    hole = outside.point(lambda v: 255 if v == 0 else 0)
    if hole.getbbox() is None:
        return None
    radius = 0
    while hole.getbbox() is not None:
        hole = hole.filter(ImageFilter.MinFilter(3))
        radius += 1
    return 2 * radius / em


class Face:
    def __init__(self, company, spec):
        self.id, self.family = spec["id"], spec.get("family_in_file") or spec["family"]
        self.group = spec.get("group") if spec.get("group") in ("serious", "stylised") else "serious"
        self.joined = bool(spec.get("joined"))
        self.licence = (spec.get("licence") or {}).get("spdx") or "unknown"
        first = (spec.get("files") or [{}])[0].get("name")
        self.path = os.path.join(library.downloads(), spec.get("dir", ""), first or "")
        if not first or not os.path.isfile(self.path):
            raise Refused(f"face {self.id}: its font file is not in the downloads: run brand.sh fonts again")
        # the facts the page shows are read from the file now, not taken from the facts file
        read = choicepage.facts_of(self.path)
        recorded = (spec.get("files") or [{}])[0].get("sha256")
        if recorded and read["sha256"] != recorded:
            raise Refused(f"face {self.id}: its font file changed since its facts were read: run brand.sh fonts again")
        self.weights, self.italic = read["weights"], read["italic"]
        self.cmap = None

    def covers(self, text):
        from fontTools.ttLib import TTFont
        if self.cmap is None:
            self.cmap = set(TTFont(self.path).getBestCmap())
        return [c for c in dict.fromkeys(text) if not c.isspace() and ord(c) not in self.cmap]


def compose(alt, face, name, mark_im, image_im, resvg, work, ink, accent, mode):
    """The alternative set in the face, in `ink` and the mark's own colours as the palette gives them, as an RGBA image."""
    targets = [ink, accent, ink]
    if not alt["lettering"]:
        return recolour(image_im, targets)
    mark = recolour(mark_im, targets)
    m_h = 1000
    m_w = round(1000 * mark.width / mark.height)
    size = 550
    font = ImageFont.truetype(face.path, size)
    pad = 100
    href = data_uri(mark)
    letter = alt.get("replaces_letter")
    if letter and letter.lower() in name.lower():
        at = name.lower().index(letter.lower())
        left, right = name[:at], name[at + 1:]
        lw, rw = font.getlength(left), font.getlength(right)
        sym = round(size * 0.62)
        sw = round(sym * mark.width / mark.height)
        base = pad + round(size * 0.9)
        width, height = pad + lw + sw + rw + pad, pad + round(size * 1.3) + pad
        body = (f'<text x="{pad}" y="{base}" font-family="{face.family}" font-size="{size}" fill="{ink}">{left}</text>'
                f'<image x="{pad + lw:g}" y="{base - sym}" width="{sw}" height="{sym}" xlink:href="{href}"/>'
                f'<text x="{pad + lw + sw:g}" y="{base}" font-family="{face.family}" font-size="{size}" fill="{ink}">'
                f'{right}</text>')
    elif alt.get("layout") == "above":
        tw = font.getlength(name)
        width, height = max(m_w, tw) + 2 * pad, pad + m_h + 200 + round(size * 1.1) + pad
        body = (f'<image x="{(width - m_w) / 2:g}" y="{pad}" width="{m_w}" height="{m_h}" xlink:href="{href}"/>'
                f'<text x="{width / 2:g}" y="{pad + m_h + 200 + round(size * 0.9)}" text-anchor="middle" '
                f'font-family="{face.family}" font-size="{size}" fill="{ink}">{name}</text>')
    else:
        tw = font.getlength(name)
        gap = 250
        width, height = pad + m_w + gap + tw + pad, m_h + 2 * pad
        body = (f'<image x="{pad}" y="{pad}" width="{m_w}" height="{m_h}" xlink:href="{href}"/>'
                f'<text x="{pad + m_w + gap}" y="{pad + m_h / 2 + size * 0.35:g}" font-family="{face.family}" '
                f'font-size="{size}" fill="{ink}">{name}</text>')
    h_px = round(900 * height / width) if width > height else 900
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'viewBox="0 0 {width:g} {height:g}" width="{width:g}" height="{height:g}">{body}</svg>')
    src, dst = os.path.join(work, "c.svg"), os.path.join(work, "c.png")
    with open(src, "w", encoding="utf-8") as fh:
        fh.write(svg)
    subprocess.run([resvg, "-h", str(max(h_px, 1000)), "--skip-system-fonts", "--use-font-file", face.path, src, dst],
                   check=True, capture_output=True)
    return Image.open(dst).convert("RGBA")


def at_height(im, h):
    return im.resize((max(1, round(im.width * h / im.height)), h), Image.LANCZOS)


def ladder(im, heights, bg, enlarge=None):
    tiles = [at_height(im, h) for h in heights]
    if enlarge:
        small = at_height(im, enlarge)
        tiles.append(small.resize((small.width * 4, small.height * 4), Image.NEAREST))
    gap = 16
    width = sum(t.width for t in tiles) + gap * (len(tiles) + 1)
    height = max(t.height for t in tiles) + 2 * gap
    sheet = Image.new("RGBA", (width, height), rgb(bg) + (255,))
    x = gap
    for t in tiles:
        sheet.alpha_composite(t, (x, (height - t.height) // 2))
        x += t.width + gap
    return sheet


def notes_for(alt, face, name):
    if not alt["lettering"]:
        return []
    notes = []
    lacking = face.covers(name)
    if lacking:
        notes.append(f"{face.family} lacks {len(lacking)} characters of the name: {' '.join(lacking[:6])}")
    if alt.get("symbol_in"):
        letter = alt["symbol_in"]
        d = counter_diameter(face.path, letter)
        if d is None:
            notes.append(f"the letter {letter} has no counter in {face.family}: the symbol cannot sit inside it")
        else:
            floor = math.ceil(MIN_SYMBOL_PX / (0.55 * d))
            if floor > SYMBOL_LIMIT:
                notes.append(f"the counter of {letter} in {face.family} is narrow ({d * 100:.0f}% of the em): the symbol "
                             f"reads as a dot below about {floor} px")
    if alt.get("replaces_letter") and face.joined:
        notes.append(f"{face.family} is a joined script: replacing the letter {alt['replaces_letter']} breaks the join")
    own = (alt.get("poor_fit") or {}).get(face.id)
    if own:
        notes.append(str(own))
    return notes


CSS = """
.picker { background: var(--surface); border: 1px solid var(--line); border-radius: 12px; padding: 16px; margin-bottom: 24px; }
.group { display: flex; flex-wrap: wrap; gap: 8px; margin-top: 8px; }
.group label { display: flex; gap: 8px; align-items: center; border: 1px solid var(--line); border-radius: 8px; padding: 6px 10px; background: var(--bg); cursor: pointer; }
.licence { color: var(--muted); font-size: .8rem; }
.panels { display: grid; grid-template-columns: repeat(auto-fit, minmax(300px, 1fr)); gap: 16px; }
.panel { border: 2px solid var(--line); border-radius: 12px; padding: 16px; background: var(--surface); display: grid; gap: 4px; align-content: start; }
.panel:has(input[name="alternative"]:checked) { border-color: var(--accent); box-shadow: 0 0 0 2px var(--accent); }
.panel p { margin: 0; } .panel .k { font-weight: 600; }
.panel .choose { display: flex; gap: 8px; align-items: center; font-weight: 600; cursor: pointer; }
.panel img { max-width: 100%; height: auto; display: block; border-radius: 6px; border: 1px solid var(--line); }
.notes { list-style: none; margin: 0; padding: 0; display: grid; gap: 4px; }
.notes li { background: var(--warn-bg); color: var(--warn); border-radius: 6px; padding: 4px 8px; font-size: .85rem; }
"""

JS = """
(function () {
  var d = JSON.parse(document.getElementById("data").textContent);
  var radios = document.querySelectorAll('input[name="face"]');
  function show(face) {
    d.alternatives.forEach(function (a) {
      var set = d.images[a.id][face];
      ["light", "dark"].forEach(function (m) { var i = document.getElementById("logo-" + a.id + "-" + m); if (i) i.src = set[m]; });
      var ul = document.getElementById("notes-" + a.id);
      ul.innerHTML = "";
      d.notes[a.id][face].forEach(function (n) { var li = document.createElement("li"); li.textContent = n; ul.appendChild(li); });
    });
  }
  radios.forEach(function (r) { r.addEventListener("change", function () { show(r.value); }); });
  if (radios.length) { show(document.querySelector('input[name="face"]:checked').value); }
})();
"""


def page(name, alts, faces, images, marks, notes, saved):
    chosen = (saved or {}).get("choice") or {}
    first = chosen.get("face") if chosen.get("face") in [f["id"] for f in faces] else (faces[0]["id"] if faces else "none")
    picker = ""
    if faces:
        groups = []
        for group, title in (("serious", "Serious"), ("stylised", "Stylised")):
            members = [f for f in faces if f["group"] == group]
            if not members:
                continue
            labels = "".join(
                f'<label><input type="radio" name="face" value="{choicepage.esc(f["id"])}"{" checked" if f["id"] == first else ""}>'
                f'<span>{choicepage.esc(f["family"])}</span> <span class="licence">{choicepage.esc(f["licence"])}</span></label>'
                for f in members)
            hint = ("calm and clear: they hold up at any size" if group == "serious"
                    else "more character: more care at small sizes")
            groups.append(f'<h3>{title} <span class="licence">{hint}</span></h3><div class="group">{labels}</div>')
        picker = ('<section class="picker" aria-label="Lettering"><h2>Lettering</h2>'
                  '<span class="licence">Picking one sets every lettered proposal in it.</span>'
                  f'<fieldset data-option-group="face">{"".join(groups)}</fieldset></section>')
    panels = []
    for a in alts:
        e = choicepage.esc
        fails = f'<p><span class="k">Size:</span> it fails at {a["fails_at"]} px and below.</p>' if a.get("fails_at") else ""
        first_notes = "".join(f"<li>{e(n)}</li>" for n in notes[a["id"]].get(first, []))
        mark_imgs = ""
        if marks[a["id"]]["light"]:
            mark_imgs = ('<h3>The mark</h3>'
                         f'<img alt="The mark of {e(a["name"])} at 16, 32 and 64 pixels, light" src="{marks[a["id"]]["light"]}">'
                         f'<img alt="The mark of {e(a["name"])} at 16, 32 and 64 pixels, dark" src="{marks[a["id"]]["dark"]}">')
        sets = images[a["id"]][first]
        ticked = " checked" if chosen.get("alternative") == a["id"] else ""
        panels.append(
            f'<section class="panel" id="panel-{e(a["id"])}"><h2>{e(a["name"])}</h2>'
            f'<label class="choose"><input type="radio" name="alternative" value="{e(a["id"])}"{ticked}> Choose this proposal</label>'
            f'<p><span class="k">Strength:</span> {e(a["strength"])}</p><p><span class="k">Risk:</span> {e(a["risk"])}</p>{fails}'
            f'<ul class="notes" id="notes-{e(a["id"])}">{first_notes}</ul><h3>The logo</h3>'
            f'<img id="logo-{e(a["id"])}-light" alt="{e(a["name"])} at 16, 24, 32 and 48 pixels, light" src="{sets["light"]}">'
            f'<img id="logo-{e(a["id"])}-dark" alt="{e(a["name"])} at 16, 24, 32 and 48 pixels, dark" src="{sets["dark"]}">'
            f'{mark_imgs}</section>')
    return picker + '<div class="panels" data-preview data-option-group="alternative">' + "\n".join(panels) + "</div>"


def load(company, path):
    try:
        with open(path, encoding="utf-8") as fh:
            spec = json.load(fh)
    except (OSError, ValueError) as e:
        raise Refused(f"cannot read {path} as JSON ({e})")
    if not isinstance(spec, dict) or not isinstance(spec.get("name"), str) or not spec["name"].strip():
        raise Refused("the candidates file needs the company's name: \"name\"")
    alts = spec.get("alternatives")
    if not isinstance(alts, list) or not 1 <= len(alts) <= 4:
        raise Refused("the candidates file needs one to four alternatives")
    seen = set()
    for a in alts:
        if not isinstance(a, dict) or not isinstance(a.get("id"), str) or not SLUG.match(a["id"]):
            raise Refused("every alternative needs an id of lowercase letters, digits and hyphens")
        if a["id"] in seen:
            raise Refused(f"the alternative id {a['id']} appears twice")
        seen.add(a["id"])
        for key in ("name", "strength", "risk"):
            if not isinstance(a.get(key), str) or not a[key].strip():
                raise Refused(f"alternative {a['id']}: {key} is missing: every alternative has a plain Strength and Risk")
        a["lettering"] = bool(a.get("lettering"))
        if a["lettering"] and not a.get("mark"):
            raise Refused(f"alternative {a['id']}: a lettered alternative needs its mark")
        if not a["lettering"] and not a.get("image"):
            raise Refused(f"alternative {a['id']}: an alternative without lettering needs its image")
        if a.get("layout", "beside") not in ("beside", "above"):
            raise Refused(f"alternative {a['id']}: layout is beside or above")
        for key in ("symbol_in", "replaces_letter"):
            if key in a and not (isinstance(a[key], str) and len(a[key]) == 1 and a[key].isalpha()):
                raise Refused(f"alternative {a['id']}: {key} is one letter")
    return spec


def run(company, candidates, resvg, choose):
    spec = load(company, candidates)
    alts, name = spec["alternatives"], spec["name"].strip()
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    faces = []
    if any(a["lettering"] for a in alts):
        ids = spec.get("faces")
        if not isinstance(ids, list) or not ids:
            raise Refused("lettered alternatives need faces: a list of ids from the fonts' facts")
        try:
            with open(os.path.join(company, CHOICES, "fonts-facts.json"), encoding="utf-8") as fh:
                facts = {c["id"]: c for c in json.load(fh)["candidates"] if "id" in c}
        except (OSError, ValueError, KeyError):
            raise Refused("there are no facts about the faces: run brand.sh fonts first")
        for i in ids:
            if i not in facts:
                raise Refused(f"the face {i} is not in the fonts' facts: run brand.sh fonts with it first")
            faces.append(Face(company, facts[i]))
    pals = colours_of(company)
    images, marks, notes, big = {}, {}, {}, {}
    with tempfile.TemporaryDirectory() as work:
        for a in alts:
            mark_im = read_png(company, a["mark"]) if a.get("mark") else None
            image_im = read_png(company, a["image"]) if a.get("image") else None
            images[a["id"]], notes[a["id"]], marks[a["id"]] = {}, {}, {"light": "", "dark": ""}
            for mode in ("light", "dark"):
                p = pals[mode]
                if mark_im is not None:
                    m = recolour(mark_im, [p["text"], p["accent"], p["text"]])
                    marks[a["id"]][mode] = data_uri(ladder(m, MARK_SIZES, p["bg"], enlarge=16))
            for face in (faces or [None]):
                key = face.id if face else "none"
                images[a["id"]][key] = {}
                notes[a["id"]][key] = notes_for(a, face, name) if face else []
                for mode in ("light", "dark"):
                    p = pals[mode]
                    made = compose(a, face, name, mark_im, image_im, resvg, work, p["text"], p["accent"], mode)
                    big[(a["id"], key, mode)] = made
                    images[a["id"]][key][mode] = data_uri(ladder(made, LOGO_SIZES, p["bg"]))
        face_rows = [{"id": f.id, "family": f.family, "group": f.group, "licence": f.licence, "weights": f.weights,
                      "italic": f.italic} for f in faces]
        data = {"name": name, "alternatives": [{k: a.get(k) for k in ("id", "name", "strength", "risk", "fails_at", "lettering")}
                                              for a in alts],
                "faces": face_rows, "images": images, "marks": marks, "notes": notes}
        saved = choicepage.saved_choice(company, "logo")
        body = page(name, alts, face_rows, images, marks, notes, saved)
        html = choicepage.skeleton("logo", f"Logo proposals for {name}",
                                   "Each proposal is shown in the same order and parts: the logo at 16, 24, 32 and 48 pixels, "
                                   "then the mark at 16, 32 and 64 pixels with an enlarged 16, each in a light and a dark row. "
                                   "Choose one proposal and one lettering.", body, data, saved, css=CSS, js=JS)
        out = os.path.join(company, CHOICES)
        os.makedirs(out, exist_ok=True)
        with open(os.path.join(out, "logo-proposals.html"), "w", encoding="utf-8") as fh:
            fh.write(html)
        print(f"The review page is written: {CHOICES}/logo-proposals.html")
        for a in alts:
            for f in (faces or [None]):
                for n in notes[a["id"]][f.id if f else "none"]:
                    print(f"note: {a['id']} with {f.family}: {n}")
        if choose:
            write_choice(company, choose, alts, faces, pals, big, name)


def write_choice(company, choose, alts, faces, pals, big, name):
    existing = choicepage.saved_choice(company, "logo") or {}
    if choose == "saved":
        picked = existing.get("choice") or {}
        if not picked.get("alternative"):
            raise Refused("no choice saved yet: the founder confirms a proposal on the page first")
        choose = picked["alternative"] + (":" + picked["face"] if picked.get("face") else "")
    alt_id, _, face_id = choose.partition(":")
    alt = next((a for a in alts if a["id"] == alt_id), None)
    if alt is None:
        raise Refused(f"the alternative {alt_id} is not in the candidates file")
    face = next((f for f in faces if f.id == face_id), None) if face_id else None
    if alt["lettering"] and face is None:
        raise Refused(f"the alternative {alt_id} has lettering: choose it with a face, {alt_id}:FACE")
    if face_id and face is None and alt["lettering"]:
        raise Refused(f"the face {face_id} is not in the candidates file")
    # an alternative without lettering is the same whatever face the picker holds
    key = face.id if face else next(k for (a, k, _) in big if a == alt["id"])
    source = os.path.join(company, IDENTITY, "logo", "source")
    os.makedirs(source, exist_ok=True)
    for mode, fname in (("light", "logo.png"), ("dark", "logo-dark.png")):
        im = big[(alt["id"], key, mode)]
        p = pals[mode]
        if min(im.size) < 1000:
            k = 1000 / min(im.size)
            im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
        snap(im, [p["text"], p["accent"]]).save(os.path.join(source, fname))
    if alt.get("mark"):
        mark_im = read_png(company, alt["mark"])
        if 0.8 <= mark_im.width / mark_im.height <= 1.25:
            p = pals["light"]
            m = recolour(mark_im, [p["text"], p["accent"], p["text"]])
            if min(m.size) < 1000:
                k = 1000 / min(m.size)
                m = m.resize((round(m.width * k), round(m.height * k)), Image.LANCZOS)
            snap(m, [p["text"], p["accent"]]).save(os.path.join(source, "mark.png"))
    record = {**existing, "step": "logo", "alternative": alt["id"], "name": alt["name"], "face": face.id if face else None,
              "wordmark": {"family": face.family, "licence": face.licence} if face else None}
    with open(os.path.join(company, CHOICES, "logo.json"), "w", encoding="utf-8") as fh:
        json.dump(record, fh, indent=2)
        fh.write("\n")
    print(f"The chosen design is written to {IDENTITY}/logo/source/ (logo.png, logo-dark.png"
          f"{', mark.png' if alt.get('mark') else ''}) and recorded in {CHOICES}/logo.json")


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument("--resvg", required=True)
    ap.add_argument("--choose")
    ap.add_argument("company")
    ap.add_argument("candidates")
    args = ap.parse_args(argv)
    try:
        run(args.company, args.candidates, args.resvg, args.choose)
    except Refused as e:
        print(f"brand.sh logo-proposals: {e}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
