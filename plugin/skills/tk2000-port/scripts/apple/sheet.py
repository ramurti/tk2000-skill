#!/usr/bin/env python3
"""Folha de contato das capturas do awrun.py: sheet.py OUTDIR [PRIMEIRA [ÚLTIMA]] -> OUTDIR/sheet.png"""
import glob, os, sys
from PIL import Image, ImageDraw
d = sys.argv[1]
lab = {l.split()[0]: l.split()[1] for l in open(os.path.join(d, 'log.txt')) if l[0] != ' '}
fs = sorted(glob.glob(os.path.join(d, 'shot-*.png')))
lo = int(sys.argv[2]) if len(sys.argv) > 2 else 0
hi = int(sys.argv[3]) if len(sys.argv) > 3 else 999
fs = [f for f in fs if lo <= int(f[-7:-4]) <= hi]
W, H, cols = 568, 204, 4
sheet = Image.new('RGB', (cols * (W + 6), ((len(fs) + cols - 1) // cols) * (H + 18)), (30, 30, 30))
dr = ImageDraw.Draw(sheet)
for i, f in enumerate(fs):
    x, y = (i % cols) * (W + 6), (i // cols) * (H + 18)
    dr.text((x + 4, y + 2), f[-7:-4] + ' ' + lab.get(f[-7:-4], ''), fill=(255, 255, 0))
    sheet.paste(Image.open(f), (x, y + 16))
sheet.save(os.path.join(d, 'sheet.png'))
