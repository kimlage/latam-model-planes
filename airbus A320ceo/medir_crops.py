"""Gridded inspection crops of the CC-BFO reference photos.

Each crop is enlarged and overlaid with a fine pixel grid labeled in ORIGINAL
photo coordinates, so anchors can be read off by eye (extrair-cotas: anchor by
hand, on enlarged crops).
"""
import os
import sys
from PIL import Image, ImageDraw

BASE = os.path.dirname(os.path.abspath(__file__))
REFS = os.path.join(BASE, "refs")


def grid_crop(img, box, out, zoom=3, step=25):
    x0, y0, x1, y1 = box
    c = img.crop(box).resize(((x1 - x0) * zoom, (y1 - y0) * zoom), Image.LANCZOS)
    d = ImageDraw.Draw(c)
    for gx in range(x0 - x0 % step + step, x1, step):
        px = (gx - x0) * zoom
        major = gx % 100 == 0
        d.line([(px, 0), (px, c.height)], fill=(255, 0, 255, 128) if major else (0, 255, 255, 90),
               width=2 if major else 1)
        if major:
            d.text((px + 2, 2), str(gx), fill=(255, 0, 255))
    for gy in range(y0 - y0 % step + step, y1, step):
        py = (gy - y0) * zoom
        major = gy % 100 == 0
        d.line([(0, py), (c.width, py)], fill=(255, 0, 255, 128) if major else (0, 255, 255, 90),
               width=2 if major else 1)
        if major:
            d.text((2, py + 2), str(gy), fill=(255, 0, 255))
    c.save(os.path.join(BASE, out))
    print("saved", out, c.size)


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "stbd"
    if which == "stbd":
        im = Image.open(os.path.join(REFS, "ref_CC-BFO_sjo_stbd.jpg"))
        print("stbd", im.size)
        grid_crop(im, (400, 950, 800, 1250), "insp_stbd_nariz.png", zoom=3)
        grid_crop(im, (2650, 850, 3300, 1150), "insp_stbd_cauda.png", zoom=3)
        grid_crop(im, (820, 900, 1100, 1250), "insp_stbd_porta1.png", zoom=3)
        grid_crop(im, (1050, 940, 1900, 1060), "insp_stbd_janelas_fwd.png", zoom=3)
        grid_crop(im, (2300, 900, 2750, 1060), "insp_stbd_janelas_aft.png", zoom=3)
    else:
        im = Image.open(os.path.join(REFS, "ref_CC-BFO_sjo_wide_port.jpg"))
        print("port", im.size)
        # aircraft occupies roughly x 1450..3600 in the 5112px frame
        grid_crop(im, (1450, 1550, 1850, 1950), "insp_port_nariz.png", zoom=3)
        grid_crop(im, (2900, 1500, 3500, 1850), "insp_port_cauda.png", zoom=3)
        grid_crop(im, (1900, 1600, 2700, 1750), "insp_port_janelas.png", zoom=3)
