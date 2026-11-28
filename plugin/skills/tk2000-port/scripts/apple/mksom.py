#!/usr/bin/env python3
"""Monta os sons refeitos do TK2000: a turbina (src/tksom.s em $6A93, no lugar do tratador da Mockingboard
do t7; src/tksom-tab.inc, as tabelas para a taxa de amostras medida; build/tk/tksom.bin) e a música do
título (src/tkmus.s em $DD80, no fim do t25; src/tkmus-tab.inc, as notas; build/tk/tkmus.bin) e os
estalinhos do voo (src/tkestalo.s em $6A19, no caminho da Mockingboard do t7; build/tk/tkestalo.bin) e o
"zuuum" da corrida no tubo (src/tkzuum.s no fim do t22, $4FB2 no TK2000, e src/tkzuumr.s em $6A53).

    mksom.py [AMOSTRAS_POR_SEGUNDO]

A turbina segue a da placa (registro do sfmb.py, AY 1 voz A em 'Prepare To Launch'): período do tom
76 -> 49 em passos de 3 e volume 0, 3, 6, 9, 12, 15, 15...; o volume vira largura do pulso
(0,15 + 0,85 * vol/15 do meio período; 0 = silêncio).
"""
import os, pickle, subprocess, sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
AT, END = 0x6A93, 0x6B1A
HZ = 1020484
SR = float(sys.argv[1]) if len(sys.argv) > 1 else 4850.0      # chamadas de TURB por segundo (medido no emulador do TK2000)

PERIODOS = [76, 73, 70, 67, 64, 61, 58, 55, 52, 49]
VOLUMES = [0, 3, 6, 9, 12, 15, 15, 15, 15, 15]


def tabelas():
    inc = [round(HZ / (16 * p) / SR * 256) for p in PERIODOS]        # fase de 8 bits
    larg = [0 if v == 0 else min(0x7F, round((0.15 + 0.85 * v / 15) * 128)) for v in VOLUMES]
    out = ['; gerado por tools/mksom.py (%.0f amostras por segundo); entra na camada em $64EA' % SR,
           'TINC:   .byte   ' + ','.join('$%02X' % x for x in inc),
           'TVOL:   .byte   ' + ','.join('$%02X' % x for x in larg)]
    open(os.path.join(ROOT, 'src', 'tksom-tab.inc'), 'w').write('\n'.join(out) + '\n')


# a música do título (opção A do dono do projeto: o tema do começo, só a melodia, repetindo): as notas
# de build/mb/melodia2.pkl (a voz mais alta a cada momento, tirada do registro do sfmb.py) de TEMA0 a TEMA1
MELODIA = os.path.join(ROOT, 'build', 'mb', 'melodia2.pkl')
TEMA0, TEMA1 = 18.04, 39.97
BATIDA = 0.130452                       # s; = 65 * 256 unidades de 8 ciclos
MUS_AT, MUS_END = 0xDD80, 0xE000        # o fim do t25 (zeros no disco)


def notas():
    """[(período do AY, batidas)]; notas mais curtas que uma batida (a passagem entre duas vozes) se juntam
    à seguinte, uma oitava acima quando o período não cabe no laço (> 255)"""
    out, resto = [], 0.0
    for t, d, p in pickle.load(open(MELODIA, 'rb')):
        if not TEMA0 <= t < TEMA1:
            continue
        d += resto
        if d < BATIDA * 0.8:
            resto = d
            continue
        resto = 0.0
        while p > 255:
            p //= 2
        out.append((p, round(d / BATIDA)))
    return out


def tab_musica():
    inc = os.path.join(ROOT, 'src', 'tkmus-tab.inc')
    if not os.path.exists(MELODIA):
        print('sem %s: fica o %s que já existe' % (MELODIA, inc))
        return
    ns = notas()
    out = ['; gerado por tools/mksom.py: o tema do título, %d notas, %d batidas (%.1f s)'
           % (len(ns), sum(k for _, k in ns), sum(k for _, k in ns) * BATIDA),
           'NNOTAS = %d' % len(ns)]
    for nome, col in (('TPER', [p for p, _ in ns]), ('TLEN', [65 * k for _, k in ns])):
        for i in range(0, len(col), 16):
            out.append(('%-8s' % (nome + ':' if i == 0 else '')) + '.byte   ' + ','.join('$%02X' % x for x in col[i:i + 16]))
    open(inc, 'w').write('\n'.join(out) + '\n')


def monta(nome='tksom', at=AT, end=END):
    b = os.path.join(ROOT, 'build', 'tk')
    os.makedirs(b, exist_ok=True)
    o, lst, binp = (os.path.join(b, nome + e) for e in ('.o', '.lst', '.bin'))
    subprocess.check_call(['ca65', os.path.join(ROOT, 'src', nome + '.s'), '-I', os.path.join(ROOT, 'src'),
                           '-o', o, '-l', lst])
    cfg = os.path.join(b, nome + '.cfg')
    open(cfg, 'w').write('MEMORY { M: start = $%04X, size = $%04X, file = %%O; }\nSEGMENTS { CODE: load = M; }\n'
                         % (at, end - at))
    subprocess.check_call(['ld65', '-C', cfg, o, '-o', binp])
    n = len(open(binp, 'rb').read())
    print('%s: %d bytes em $%04X-$%04X (cabem %d) -> %s' % (nome, n, at, at + n - 1, end - at, binp))
    return binp


if __name__ == '__main__':
    tabelas()
    monta()
    tab_musica()
    monta('tkmus', MUS_AT, MUS_END)
    monta('tkestalo', 0x6A19, 0x6A53)      # os estalinhos do voo: no caminho da Mockingboard do t7
    monta('tkzuumr', 0x6A53, 0x6A90)       # o "zuuum" da corrida no tubo: a volta do chiado, logo depois
    monta('tkzuum', 0x4FB2, 0x5000)        # e o resto no fim do t22 ($AFB2 no Apple)
