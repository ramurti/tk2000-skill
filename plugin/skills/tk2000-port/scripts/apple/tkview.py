#!/usr/bin/env python3
"""Mostra uma tela de alta resolução como o Apple II a mostra e como o TK2000 mostraria os mesmos
bytes, lado a lado (cores do TK2000 copiadas do Video.cpp do emulador: pares de pixels a partir de
x = 0, paleta pelo bit 7 do byte do pixel esquerdo do par).

    tkview.py OUT.png TITULO:MEM.bin:BASE_HEX [TITULO:MEM.bin:BASE_HEX ...]
      MEM.bin: despejo da memória a partir de $0000; BASE_HEX: 2000 ou 4000 (página do Apple)
"""
import sys
from PIL import Image, ImageDraw


def rows(mem, base):
    for y in range(192):
        a = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
        yield y, mem[a:a + 40]


def apple(mem, base):
    """Apple II (aproximado): pixel isolado = cor pela paridade da coluna e pela paleta"""
    img = Image.new('RGB', (280, 192))
    px = img.load()
    for y, line in rows(mem, base):
        bits, pal = [], []
        for b in line:
            for k in range(7):
                bits.append((b >> k) & 1)
                pal.append(b >> 7)
        for x in range(280):
            if not bits[x]:
                continue
            if (x > 0 and bits[x - 1]) or (x < 279 and bits[x + 1]):
                c = (255, 255, 255)
            else:
                c = [[(255, 68, 253), (20, 245, 60)], [(20, 207, 253), (255, 106, 60)]][pal[x]][x & 1]
            px[x, y] = c
    return img


TK = {(0, 0): None, (1, 1): (255, 255, 255)}


def tk2000(mem, base):
    """TK2000 como o emulador desenha (Video.cpp drawColor)"""
    img = Image.new('RGB', (280, 192))
    px = img.load()
    for y, line in rows(mem, base):
        bits = []
        for b in line:
            for k in range(7):
                bits.append((b >> k) & 1)
        for x in range(0, 280, 2):
            cm = line[x // 7] & 0x80
            pair = (bits[x], bits[x + 1])
            if pair == (0, 0):
                continue
            if pair == (1, 1):
                c = (255, 255, 255)
            elif pair == (0, 1):
                c = (250, 16, 0) if cm else (0, 128, 255)
            else:
                c = (32, 176, 176) if cm else (32, 192, 0)
            px[x, y] = c
            px[x + 1, y] = c
    return img


def main():
    out = sys.argv[1]
    shots = []
    for spec in sys.argv[2:]:
        title, path, base = spec.rsplit(':', 2)
        mem = open(path, 'rb').read()
        shots.append((title, apple(mem, int(base, 16)), tk2000(mem, int(base, 16))))
    S = 2
    W, H = 280 * S, 192 * S
    sheet = Image.new('RGB', (W * 2 + 24, len(shots) * (H + 40) + 8), (40, 40, 40))
    d = ImageDraw.Draw(sheet)
    for i, (title, a, t) in enumerate(shots):
        y = 8 + i * (H + 40)
        d.text((8, y), title + ' - Apple II (original)', fill=(255, 255, 0))
        d.text((W + 16, y), title + ' - TK2000 (mesmos bytes, sem adaptar)', fill=(255, 255, 0))
        sheet.paste(a.resize((W, H), Image.NEAREST), (8, y + 16))
        sheet.paste(t.resize((W, H), Image.NEAREST), (W + 16, y + 16))
    sheet.save(out)


if __name__ == '__main__':
    main()
