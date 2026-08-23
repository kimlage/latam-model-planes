#!/usr/bin/env python3
"""Verify every shipped SDSC GIF with a real parser, never a byte scan."""
import os
import sys
from PIL import Image, ImageSequence

ok = True
for p in sys.argv[1:]:
    im = Image.open(p)
    durs = {}
    n = 0
    for fr in ImageSequence.Iterator(im):
        d = fr.info.get("duration")
        durs[d] = durs.get(d, 0) + 1
        n += 1
    good = (set(durs) == {40})
    ok = ok and good
    print("%-34s %4d frames  %6.2f MB  %-10s durations %s  %s"
          % (os.path.basename(p), n, os.path.getsize(p) / 1e6,
             "%dx%d" % im.size, durs, "OK" if good else "*** NOT 40 ms ***"))
sys.exit(0 if ok else 1)
