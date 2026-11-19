#!/usr/bin/env python3
"""Páginas hi-res do Apple II de um dump de memória como PNG (cores NTSC simples: pares de pixels).
    hgr.py MEM.bin OUT.png [PAGE...]   (página 1 = $2000, 2 = $4000)"""
import sys
from PIL import Image

mem = open(sys.argv[1], 'rb').read()
pages = [int(p) for p in sys.argv[3:]] or [1, 2]
COL = {(0, 0): (0, 0, 0), (1, 1): (255, 255, 255)}
PAL = [{0: (255, 68, 253), 1: (20, 245, 60)}, {0: (20, 207, 253), 1: (255, 106, 60)}]   # x par: violeta / azul
img = Image.new('RGB', (280 * len(pages) + 8 * (len(pages) - 1), 192))
for n, pg in enumerate(pages):
    base = 0x2000 * pg
    for y in range(192):
        a = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
        bits, pal = [], []
        for b in mem[a:a + 40]:
            for k in range(7):
                bits.append((b >> k) & 1)
                pal.append(b >> 7)
        for x in range(280):
            on = bits[x]
            if on and ((x > 0 and bits[x - 1]) or (x < 279 and bits[x + 1])):
                c = (255, 255, 255)
            elif on:
                c = PAL[pal[x]][x & 1]
            else:
                c = (0, 0, 0)
            img.putpixel((n * 288 + x, y), c)
img.resize((img.width * 2, 384), Image.NEAREST).save(sys.argv[2])
