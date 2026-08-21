#!/usr/bin/env python3
"""Build the fleet gallery: three angles per aircraft, one strip each.

    python3 galeria.py

Writes `capa.png` (the whole fleet, one row per aircraft) and one
`galeria_<key>.png` strip per aircraft for the README table.

The three angles are the ones that answer the three questions a viewer asks:
**hero** for the shape, **perfil** for the proportions and the paint
application along the hull, **cauda** for the fin sash and the rear wedge —
which are the marks this project spent the most measurement on.

Rendered angles come from the gate (`render_gate.py`), so this script only
composes: it never renders, and it fails loudly if an aircraft is missing an
angle rather than quietly shipping a gallery with a hole in it. Regenerate it
after any round that changes how an aircraft looks.
"""
import os

from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.dirname(os.path.abspath(__file__))

# (folder, label, registration) in the order the gallery reads
FROTA = [
    ("airbus A319",       "Airbus A319",        "PT-TMT"),
    ("airbus A320ceo",    "Airbus A320ceo",     "CC-BFO"),
    ("airbus A320neo",    "Airbus A320neo",     "PT-TMN"),
    ("airbus A321ceo",    "Airbus A321ceo",     "PT-MXP"),
    ("airbus A321neo",    "Airbus A321neo",     "PS-LBA"),
    ("boeing 767-300ER",  "Boeing 767-300ER",   "CC-CWY"),
    ("boeing 767-300F",   "Boeing 767-300F",    "N536LA"),
    ("boeing 767-300BCF", "Boeing 767-300BCF",  "CC-CXE"),
    ("boeing 777-300ER",  "Boeing 777-300ER",   "PT-MUG"),
    ("boeing 787-8",      "Boeing 787-8",       "CC-BBF"),
    ("boeing 787-9",      "Boeing 787-9",       "CC-BGK"),
]

ANGULOS = [("render_hero.png", "3/4 hero"),
           ("render_perfil.png", "perfil"),
           ("render_cauda.png", "cauda")]

CELL_W = 580          # width of one angle in the strip
GAP = 8
PAD = 10
TITLE_H = 46
CAPTION_H = 26
BG = (17, 17, 19)
FG = (232, 232, 235)
DIM = (150, 150, 156)


def _font(size, bold=False):
    for p in ("/System/Library/Fonts/Helvetica.ttc",
              "/System/Library/Fonts/Supplemental/Arial.ttf"):
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size, index=1 if bold else 0)
            except Exception:
                pass
    return ImageFont.load_default()


def faixa(folder, label, reg):
    """One aircraft: title bar, three angles side by side, captions."""
    ims = []
    for fname, _ in ANGULOS:
        p = os.path.join(ROOT, folder, fname)
        if not os.path.exists(p):
            raise SystemExit("missing angle: %s" % p)
        ims.append(Image.open(p).convert("RGB"))

    cell_h = round(CELL_W * ims[0].height / ims[0].width)
    w = PAD * 2 + CELL_W * 3 + GAP * 2
    h = TITLE_H + cell_h + CAPTION_H
    strip = Image.new("RGB", (w, h), BG)
    d = ImageDraw.Draw(strip)

    d.text((PAD, 12), label, font=_font(25, bold=True), fill=FG)
    tw = d.textlength(label, font=_font(25, bold=True))
    d.text((PAD + tw + 14, 14), "· " + reg, font=_font(23), fill=DIM)

    for i, (im, (_, cap)) in enumerate(zip(ims, ANGULOS)):
        x = PAD + i * (CELL_W + GAP)
        strip.paste(im.resize((CELL_W, cell_h), Image.LANCZOS), (x, TITLE_H))
        d.text((x + 2, TITLE_H + cell_h + 5), cap, font=_font(18), fill=DIM)
    return strip


def main():
    faixas = []
    for folder, label, reg in FROTA:
        f = faixa(folder, label, reg)
        out = os.path.join(ROOT, "galeria_%s.png"
                           % folder.split("/")[-1].replace(" ", "_"))
        f.save(out)
        print("wrote", os.path.basename(out), f.size)
        faixas.append(f)

    w = max(f.width for f in faixas)
    capa = Image.new("RGB", (w, sum(f.height for f in faixas)), BG)
    y = 0
    for f in faixas:
        capa.paste(f, (0, y))
        y += f.height
    capa.save(os.path.join(ROOT, "capa.png"))
    print("wrote capa.png", capa.size, "-", len(faixas), "aircraft x 3 angles")


if __name__ == "__main__":
    main()
