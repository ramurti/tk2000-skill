#!/usr/bin/env python3
"""Recolorir um pedaço da tela ponto a ponto: lê a cor de cada ponto no Apple (sfboot.hgr_img), troca
as cores por um mapa e monta os bytes do TK2000 de novo (pares de pontos a partir de x = 0, paleta do
byte da esquerda: 0 = verde "10" / azul "01", 1 = ciano "10" / vermelho "01"; "11" branco, "00"
preto). Usado para o tanque do menu do Sky Fox (violeta no Apple, verde sobre o verde no TK2000).

    recolor(page, y0, y1, c0, c1, mapa) -> {deslocamento na página: byte novo}
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import sfcores as C

AP = {(255, 68, 253): 'violeta', (20, 245, 60): 'verde', (20, 207, 253): 'azul', (255, 106, 60): 'laranja',
      (255, 255, 255): 'branco', (0, 0, 0): 'preto'}
TK = {'verde': (0, 1, 0), 'azul': (0, 0, 1), 'ciano': (1, 1, 0), 'vermelho': (1, 0, 1)}


def apple_pixels(page):
    import sfboot
    mem = bytearray(0x4000)
    mem[0x2000:0x4000] = page
    img = sfboot.hgr_img(mem, 1)
    return lambda x, y: AP.get(img.getpixel((x, y)), 'preto')


def recolor(page, y0, y1, c0, c1, mapa):
    px = apple_pixels(page)
    out = {}
    for y in range(y0, y1):
        want = []
        for x in range(280):
            c = px(x, y)
            want.append(mapa.get(c, c))
        bits = [0] * 280
        pal = [0] * 40
        for x in range(0, 280, 2):              # cada par: branco, preto ou uma cor (a do ponto aceso)
            a, b = want[x], want[x + 1]
            if a == 'branco' and b == 'branco':
                bits[x] = bits[x + 1] = 1
                continue
            cor = a if a not in ('preto', 'branco') else b if b not in ('preto', 'branco') else None
            if cor is None or cor not in TK:
                if 'branco' in (a, b):
                    bits[x] = bits[x + 1] = 1
                continue
            p, l, r = TK[cor]
            bits[x], bits[x + 1] = l, r
            pal[x // 7] = p
        for c in range(c0, c1):
            v = sum(bits[c * 7 + j] << j for j in range(7)) | (0x80 if pal[c] else 0)
            out[C.row(y) + c] = v
    return out


def figure(mapfile, page, mapa, out):
    """uma figura recolorida: mapfile = {endereço do dado: [[deslocamento na tela, valor], ...]} (onde a
    rotina de figuras a copiou, medido no Apple); page = a tela do Apple com a figura; grava
    {endereço: byte novo} em out (json)"""
    import json
    m = {int(a, 16): v for a, v in json.load(open(mapfile)).items()}
    offs = [o for v in m.values() for o, _ in v]
    ys = [C.line(o) for o in offs]
    cs = [C.col(o) for o in offs]
    new = recolor(page, min(ys), max(ys) + 1, min(cs), max(cs) + 1, mapa)
    res = {'%04X' % a: new[v[0][0]] for a, v in sorted(m.items())}
    json.dump({'comentario': 'figura recolorida por tools/sfrecolor.py (%s)' % mapa, 'bytes': res},
              open(out, 'w'), indent=0)
    return res


if __name__ == '__main__':                     # o tanque do menu do Sky Fox: opção B (ciano com contorno)
    ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
    page = open(os.path.join(ROOT, 'src', 'menu-ref.bin'), 'rb').read()
    r = figure(os.path.join(ROOT, 'src', 'tanque-map.json'), page, {'violeta': 'ciano', 'laranja': 'vermelho'},
               os.path.join(ROOT, 'src', 'tanque.json'))
    print(len(r), 'bytes ->', 'src/tanque.json')
