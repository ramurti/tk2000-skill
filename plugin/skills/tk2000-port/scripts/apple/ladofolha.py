#!/usr/bin/env python3
"""Folhas lado a lado (Apple II | TK2000) com um título por par, a partir das capturas do lockstep
(tools/sflockstep.py -L NOME:T1,T2 -> build/lado/NOME-T.png) e de build/lado/titulos.json
({"arquivo.png": "título"}, na ordem em que entram nas folhas).

    ladofolha.py [POR_FOLHA]   -> build/lado/folha-NN.png
"""
import json, os, sys
from PIL import Image, ImageDraw, ImageFont

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
D = os.path.join(ROOT, 'build', 'lado')


def font(n):
    for f in ('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', '/Library/Fonts/Arial Bold.ttf'):
        if os.path.exists(f):
            return ImageFont.truetype(f, n)
    return ImageFont.load_default()


def main():
    per = int(sys.argv[1]) if len(sys.argv) > 1 else 4
    tit = json.load(open(os.path.join(D, 'titulos.json')))
    items = [(f, t) for f, t in tit.items() if os.path.exists(os.path.join(D, f))]
    f1, f2 = font(22), font(16)
    for n in range(0, len(items), per):
        chunk = items[n:n + per]
        w, h = Image.open(os.path.join(D, chunk[0][0])).size
        head, gap = 40, 14
        sheet = Image.new('RGB', (w, 30 + len(chunk) * (head + h + gap)), (255, 255, 255))
        d = ImageDraw.Draw(sheet)
        d.text((4, 4), 'Apple II (original)', font=f2, fill=(80, 80, 80))
        d.text((w // 2 + 8, 4), 'TK2000 (porte)', font=f2, fill=(80, 80, 80))
        y = 30
        for k, (f, t) in enumerate(chunk):
            d.text((4, y + 8), '%d. %s' % (n + k + 1, t), font=f1, fill=(0, 0, 0))
            sheet.paste(Image.open(os.path.join(D, f)), (0, y + head))
            y += head + h + gap
        out = os.path.join(D, 'folha-%02d.png' % (n // per + 1))
        sheet.save(out)
        print(out)


if __name__ == '__main__':
    main()
