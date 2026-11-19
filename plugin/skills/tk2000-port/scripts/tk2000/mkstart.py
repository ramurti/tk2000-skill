#!/usr/bin/env python3
"""A tela de abertura (src/start.s): o título em vermelho, embaixo dele as faixas do pôr do sol, as
teclas e os créditos, sobre preto. src/start.inc: a fonte (StartGlyphs: 7 linhas de 5 bits por
glifo, bit 4 o da esquerda; as letras pequenas da linha do som, 3 x 5, no mesmo formato), os textos
(StartText: linha, primeiro par, pares e linhas por pixel da fonte, vermelho?, pares de uma letra
para a próxima, glifos, $FF; uma linha de $FF os encerra) e as faixas (StartBands: 8 bytes de
padrão cada, duas linhas cada a partir de BAND_ROW); o src/start.s os desenha. Prévia em
build/start.png (como o emulador desenha, e com o borrado de uma TV); screen() é a imagem esperada
(tools/startcheck.py).

Texto: uma fonte 5 x 7, um pixel da fonte = um par de pixels x 2 linhas (quase quadrado); o título
3 pares x 6 linhas por pixel da fonte; as faixas são as próprias misturas do jogo (SunsetTab do
azul do céu até o amarelo).

Uso: mkstart.py OUT.inc
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import mkcolors as m  # noqa: E402
import mktables as T  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
FONT = {
    'A': '.###. #...# #...# ##### #...# #...# #...#',
    'B': '####. #...# #...# ####. #...# #...# ####.',
    'C': '.#### #.... #.... #.... #.... #.... .####',
    'D': '####. #...# #...# #...# #...# #...# ####.',
    'E': '##### #.... #.... ####. #.... #.... #####',
    'G': '.#### #.... #.... #.### #...# #...# .###.',
    'H': '#...# #...# #...# ##### #...# #...# #...#',
    'I': '##### ..#.. ..#.. ..#.. ..#.. ..#.. #####',
    'K': '#...# #..#. #.#.. ##... #.#.. #..#. #...#',
    'L': '#.... #.... #.... #.... #.... #.... #####',
    'M': '#...# ##.## #.#.# #.#.# #...# #...# #...#',
    'N': '#...# ##..# #.#.# #..## #...# #...# #...#',
    'O': '.###. #...# #...# #...# #...# #...# .###.',
    'P': '####. #...# #...# ####. #.... #.... #....',
    'R': '####. #...# #...# ####. #.#.. #..#. #...#',
    'S': '.#### #.... #.... .###. ....# ....# ####.',
    'T': '##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..',
    'U': '#...# #...# #...# #...# #...# #...# .###.',
    'V': '#...# #...# #...# #...# #...# .#.#. ..#..',
    'W': '#...# #...# #...# #.#.# #.#.# ##.## #...#',
    'Y': '#...# #...# .#.#. ..#.. ..#.. ..#.. ..#..',
    '0': '.###. #...# #..## #.#.# ##..# #...# .###.',
    '1': '..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.',
    '2': '.###. #...# ....# ..##. .#... #.... #####',
    '3': '####. ....# ....# .###. ....# ....# ####.',
    '6': '.###. #.... #.... ####. #...# #...# .###.',
    '8': '.###. #...# #...# .###. #...# #...# .###.',
    '9': '.###. #...# #...# .#### ....# ....# .###.',
    'F': '##### #.... #.... ####. #.... #.... #....',
    'J': '..### ...#. ...#. ...#. ...#. #..#. .##..',
    'Q': '.###. #...# #...# #...# #.#.# #..#. .##.#',
    'X': '#...# #...# .#.#. ..#.. .#.#. #...# #...#',
    'Ç': '.#### #.... #.... #.... .#### ..#.. .##..',
    '/': '....# ....# ...#. ..#.. .#... #.... #....',
    ':': '..... ..##. ..##. ..... ..##. ..##. .....',
    ' ': '..... ..... ..... ..... ..... ..... .....',
}
SMALL = {                           # 3 x 5 (a linha do som): nos 3 bits da esquerda, linhas 0-4
    'A': '### #.# ### #.# #.#', 'C': '### #.. #.. #.. ###', 'D': '##. #.# #.# #.# ##.',
    'L': '#.. #.. #.. #.. ###', 'M': '#.# ### #.# #.# #.#', 'N': '##. #.# #.# #.# #.#',
    'O': '### #.# #.# #.# ###', 'R': '##. #.# ##. #.# #.#', 'S': '### #.. ### ..# ###',
    'T': '### .#. .#. .#. .#.', 'U': '#.# #.# #.# #.# ###', ':': '... .#. ... .#. ...',
    ' ': '... ... ... ... ...',
}


def glyph(ch, small):
    """7 linhas de 5 pixels"""
    if small:
        rows = [r + '..' for r in SMALL[ch].split()] + ['.....'] * 2
        return rows
    return FONT[ch].split()
TITLE, TITLE_ROW, TITLE_PX = 'ENDURO', 8, (3, 5)
KEYS = [('ESQ/DIR', 'VIRAR'), ('BAIXO', 'FREAR'), ('ESPAÇO', 'ACELERAR'), ('RETURN', 'NOVO JOGO')]
KEYS_ROW, KEYS_STEP, KEY_PAIR, WHAT_PAIR = 72, 15, 6, 54
OPT_KEY, OPT_ROW = 'S', 72 + 4 * 15            # o som dos outros carros: S o muda
OPTS = ['SOM DOS CARROS: NORMAL', 'SOM DOS CARROS: CURTO', 'SOM DOS CARROS: MUDO']
OPT_PAIR = 53                                   # letras pequenas (4 pares cada), 2 linhas mais abaixo
PRESS, PRESS_ROW = 'APERTE RETURN', 155
CREDITS = [('ACTIVISION 1983', 175), ('TK2000 2026', 185)]   # (texto, linha): centralizado, 1 linha por pixel
OPT_BYTE = 2 * OPT_PAIR // 7                    # o primeiro byte da opção (apagado para mudá-la)


def strings():
    """(texto, linha, primeiro par, (pares, linhas) por pixel da fonte, vermelho, pequena)"""
    out = [(TITLE, TITLE_ROW, 70 - width(TITLE, TITLE_PX[0]) // 2, TITLE_PX, True, False)]
    for k, (key, what) in enumerate(KEYS):
        out.append((key, KEYS_ROW + KEYS_STEP * k, KEY_PAIR, (1, 2), False, False))
        out.append((what, KEYS_ROW + KEYS_STEP * k, WHAT_PAIR, (1, 2), False, False))
    out.append((OPT_KEY, OPT_ROW, KEY_PAIR, (1, 2), False, False))
    out.append((PRESS, PRESS_ROW, 70 - width(PRESS) // 2, (1, 2), True, False))
    for t, row in CREDITS:
        out.append((t, row, 70 - width(t) // 2, (1, 1), False, False))
    return out


def option(k):
    return (OPTS[k], OPT_ROW + 2, OPT_PAIR, (1, 2), False, True)


BAND_ROW = TITLE_ROW + 7 * TITLE_PX[1] + 8
BANDS = m.SUNSET[11:2:-1]


def width(s, sx=1):
    return sx * (6 * len(s) - 1)


def text(grid, s, row, pair, color, px=(1, 2), small=False):
    sx, sy = px
    adv = 4 if small else 6
    for i, ch in enumerate(s):
        g = glyph(ch, small)
        for y in range(7):
            for x in range(5):
                if g[y][x] == '#':
                    for dy in range(sy):
                        for dx in range(sx):
                            grid[row + sy * y + dy][pair + sx * (adv * i + x) + dx] = color


def screen(opt=0):
    black, white, red = m.pure(m.K), m.pure(m.W), m.pure(m.R)
    grid = [[black] * 140 for _ in range(192)]
    for s, row, pair, px, isred, small in strings() + [option(opt)]:
        text(grid, s, row, pair, red if isred else white, px, small)
    for k, c in enumerate(BANDS):
        for y in range(BAND_ROW + 2 * k, BAND_ROW + 2 * k + 2):
            grid[y] = [T.mix_of(c)] * 140
    return grid


def main():
    recs = strings()
    opts = [option(k) for k in range(len(OPTS))]
    glyphs = sorted({(small, ch) for s, *_, small in recs + opts for ch in s})

    def rec(r):
        s, row, pair, (sx, sy), isred, small = r
        return '        .byte   %d, %d, %d, %d, %d, %d, %s, $FF   ; %s\n' % (
            row, pair, sx, sy, isred, sx * (4 if small else 6),
            ', '.join('%d' % glyphs.index((small, ch)) for ch in s), s)
    with open(sys.argv[1], 'w') as f:
        f.write('; gerado por tools/mkstart.py: a tela de abertura\n')
        f.write('BAND_ROW = %d\nBANDS = %d\n' % (BAND_ROW, len(BANDS)))
        f.write('StartGlyphs:\n')
        for small, ch in glyphs:
            rows = [int(r.replace('#', '1').replace('.', '0'), 2) for r in glyph(ch, small)]
            f.write('        .byte   %s   ; %s%s\n' % (', '.join('$%02X' % v for v in rows), ch,
                                                     ' (pequena)' if small else ''))
        f.write('StartText:\n')
        for r in recs:
            f.write(rec(r))
        f.write('        .byte   $FF\n')
        f.write('OPT_ROW = %d\nOPT_BYTE = %d\nOPTS = %d\n' % (OPT_ROW, OPT_BYTE, len(OPTS)))
        for k, r in enumerate(opts):
            f.write('StartOpt%d:\n' % k + rec(r) + '        .byte   $FF\n')
        f.write('StartOptLo: .byte   %s\n' % ', '.join('<StartOpt%d' % k for k in range(len(OPTS))))
        f.write('StartOptHi: .byte   %s\n' % ', '.join('>StartOpt%d' % k for k in range(len(OPTS))))
        f.write('StartBands:\n')
        for c in BANDS:
            f.write('        .byte   %s\n' % ', '.join('$%02X' % v for v in T.pattern(T.mix_of(c))))
    img = m.render(m.encode(screen()))
    from PIL import Image
    out = Image.new('RGB', (840 * 2 + 20, 576), (40, 40, 40))
    out.paste(m.big(img), (0, 0))
    out.paste(m.tv(img), (860, 0))
    out.save(os.path.join(ROOT, 'build', 'start.png'))


if __name__ == '__main__':
    main()
