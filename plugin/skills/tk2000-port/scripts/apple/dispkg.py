#!/usr/bin/env python3
"""Desmonta os pacotes de 4K do Sky Fox (uma trilha crua do disco num endereço fixo: página n =
setor DOS 15-n) em fontes ca65 (src/dis/tNN.s) que remontam nos mesmos bytes (--check).

Código = o que rodou com o pacote na memória (marcas de execução do tools/usage.py, build/use/*.pkl)
mais o rastreio estático do tools/disa2.py (desvios não tomados, destinos de JSR/JMP dentro do
pacote). O resto é dado (.byte).

    dispkg.py [--check] [--tk] [tNN...]        (padrão: todos os pacotes da tabela PKGS)

--tk: gera a versão do TK2000 (src/tk/NAME.s, build/tk/NAME.bin): o código no endereço do TK2000
(sfrelocs.reloc: $4000-$5FFF <-> $A000-$BFFF), operandos pelos rótulos, e os bytes de
sfrelocs.patches (deslocamento de página, bytes altos em tabelas e imediatos).
"""
import os, pickle, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import disa2

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DSK = os.path.join(ROOT, 'reference', 'Skyfox_1984_Electronic_Arts_cr_Black_Bag.dsk')
USE = os.path.join(ROOT, 'build', 'use')

# pacote: (trilha, endereço, região do usage.py, medições do usage.py com o pacote na memória);
# trilha 'res' (tamanho) = código residente, montado pela carga inicial: a referência é a memória
# logo depois dela (reference/resident-14s.bin, do estado do AppleWin build/aw/res/snap-14.yaml)
FLY_A = ['A22', 'A17']
FLY_B = ['B1', 'B2']                    # voo B: build/aw/end1/snap-62 e snap-200, 30 s cada
OPEN = ['O1', 'O2', 'O3']              # abertura (60 s sozinha), menu (joystick), de build/aw/res/snap-14;
                                        # O3: fim da abertura, build/aw/snaps/snap-100, 30 s
BRIEF = ['M1', 'M2']                   # M2: briefing da demonstração, build/aw/snaps/snap-140, 14 s
BRIEF_ONLY = BRIEF                          # briefing e mapa tático (teclas S R Z T I J K M Esc C), de build/aw/sc0/snap-40
ALL = FLY_A + FLY_B + OPEN + BRIEF + ['D1']   # D1: snaps/snap-128, 40 s pela passagem abertura -> demonstração
                                        # (só para as unidades que não mudam entre fases)
RES = os.path.join(ROOT, 'reference', 'resident-14s.bin')  # do estado build/aw/res/snap-14.yaml
PKGS = {
    'r08': (('res', 0x200), 0x0800, 'main', ALL),
    't15': (15, 0x0A00, 'main', [r for r in ALL if r != 'D1']),   # D1 passa pela carga do t10 em $0A00
    't10': (10, 0x0A00, 'main', []),    # carregado em $0A00 no voo da demonstração (antes do t15): só pelos SEEDS
    'r1A': (('res', 0x600), 0x1A00, 'main', ALL),
    'r20': (('res', 0x2000), 0x2000, 'main', ALL),
    'r40': (('res', 0x2000), 0x4000, 'main', ALL),     # vai para $A000 no TK2000
    'rB0': (('res', 0x1000), 0xB000, 'main', ALL),
    't7':  (7, 0x6000, 'main', ALL),
    't16': (16, 0x7000, 'main', FLY_A + OPEN),
    't21': (21, 0x7000, 'main', BRIEF),
    't11': (11, 0x7000, 'main', FLY_B),
    't19': (19, 0x7000, 'main', []),    # carregado em $7000 na demonstração, depois da troca 22 -> 17: pelos SEEDS
    't8':  (8, 0x8000, 'main', ALL),
    't14': (14, 0x9000, 'main', FLY_A + OPEN + BRIEF),
    't9':  (9, 0x9000, 'main', FLY_B),
    't33': (33, 0xA000, 'main', OPEN),
    't20': (20, 0xA000, 'main', BRIEF),
    't22': (22, 0xA000, 'main', ['A22']),
    't17': (17, 0xA000, 'main', ['A17']),
    't12': (12, 0xA000, 'main', FLY_B),
    't25': (25, 0xD000, 'lc1', OPEN + ['O4', 'M2']),   # O4: snaps/snap-128, passa pelas cargas do briefing
    't18': (18, 0xD000, 'lc1', FLY_A),
    't13': (13, 0xD000, 'lc1', FLY_B),
    't31': (31, 0xD000, 'lc2', OPEN),
    't23': (23, 0xD000, 'lc2', FLY_A + FLY_B + BRIEF),
    't32': (32, 0xE000, 'lchi', OPEN),
    't24': (24, 0xE000, 'lchi', FLY_A + FLY_B + BRIEF),
    't30': (30, 0xF000, 'lchi', OPEN),
    't29': (29, 0xF000, 'lchi', FLY_A + FLY_B + BRIEF),
}
X = 4
INLINE = {0xB51B: 8,                    # jsr $B51B: 8 bytes de parâmetros embutidos (uma figura a desenhar)
          0xB06F: lambda b, a: 3 + b(a + 5)}   # jsr $B06F: posição (2), tamanho (1) e o texto
SEEDS = {                               # código que não rodou nas medições, achado pelo lockstep
    't8': [0x800B],                     # lda $227E / jsr $4BF8 (depois da troca do pacote de $A000)
    't21': [0x70BF, 0x7425],            # logo depois da carga do briefing da demonstração (lockstep)
    # t25: trechos de código guardados como dados, copiados para $67AE e executados lá (a passagem
    # da abertura para a demonstração; tabelas $DBB8/$DBC7 = origem, $DBD6 = tamanho)
    't25': [0xDBE5, 0xDBEB, 0xDC36, 0xDCA5, 0xDD00, 0xDD51, 0xDD6D],
}
# o carregador de trilhas roda com o motor ligado (as medições não o marcam): as instruções vistas
# numa carga no py65 (build/use/loader-pcs.pkl, a troca t22 -> t17 do voo A)
import glob as _glob
for _f in sorted(_glob.glob(os.path.join(USE, 'exec-*.pkl'))):   # instruções vistas pelo tools/execpcs.py
    for _nm, _p in pickle.load(open(_f, 'rb')).items():
        SEEDS[_nm] = sorted(set(SEEDS.get(_nm, [])) | _p)
_lp = os.path.join(USE, 'loader-pcs.pkl')
if os.path.exists(_lp):
    _pcs = pickle.load(open(_lp, 'rb'))
    SEEDS['rB0'] = sorted(set(SEEDS.get('rB0', [])) | {p for p in _pcs if 0xB000 <= p < 0xC000})
    SEEDS['r40'] = sorted({p for p in _pcs if 0x4000 <= p < 0x6000})
disa2.NAMES.update({0xC083: 'LCRAM2RW', 0xC08B: 'LCRAM1RW', 0xC089: 'LCROM1W'})


def package(dsk, t):
    return b''.join(dsk[t * 4096 + (15 - n) * 256:t * 4096 + (16 - n) * 256] for n in range(16))


def source(dsk, t, base):
    if isinstance(t, tuple):
        return open(RES, 'rb').read()[base:base + t[1]]
    return package(dsk, t)


def executed(region, base, runs, n=0x1000):
    off = {'main': 0, 'lc1': 0xD000, 'lc2': 0xD000, 'lchi': 0xE000}[region]
    cov = set()
    for r in runs:
        u, _ = pickle.load(open(os.path.join(USE, r + '.pkl'), 'rb'))
        arr = u[region]
        for a in range(base, base + n):
            if arr[a - off] & X:
                cov.add(a)
    return cov


def starts(cov, base, data):
    """O usage.py marca todos os bytes de cada instrução executada: cada sequência de bytes marcados
    começa numa instrução, e as seguintes vêm uma depois da outra."""
    out, a = set(), base
    while a < base + len(data):
        if a in cov and (a - 1 not in cov or a == base):
            while a in cov:
                out.add(a)
                mn, mode = disa2.OPS[data[a - base]]
                a += disa2.LEN[mode]
        else:
            a += 1
    return out


def check(name, base, data, kind='dis'):
    src = os.path.join(ROOT, 'src', kind, name + '.s')
    out = os.path.join(ROOT, 'build', kind)
    os.makedirs(out, exist_ok=True)
    o, b = os.path.join(out, name + '.o'), os.path.join(out, name + '.bin')
    subprocess.run(['ca65', src, '-o', o], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'src', 'dis', 'raw.cfg'), o, '-o', b], check=True)
    got = open(b, 'rb').read()
    if data is None:
        return '%d bytes' % len(got)
    bad = [k for k in range(max(len(got), len(data))) if k >= len(got) or k >= len(data) or got[k] != data[k]]
    return 'idêntico' if not bad else '%d bytes diferentes, o primeiro em $%04X' % (len(bad), base + bad[0])


def main():
    a = sys.argv[1:]
    chk = '--check' in a
    tk = '--tk' in a
    kind = 'tk' if tk else 'dis'
    if tk:
        import sfrelocs
    names = [x for x in a if not x.startswith('--')] or list(PKGS)
    dsk = open(DSK, 'rb').read()
    os.makedirs(os.path.join(ROOT, 'src', kind), exist_ok=True)
    xseeds = {}                                 # pontos de entrada vindos de saltos de outras unidades
    for rnd in range(4):
        for nm in names:
            one(nm, dsk, kind, tk, chk and False, xseeds, quiet=True)
        new = cross_seeds()
        if all(new.get(k, set()) <= xseeds.get(k, set()) for k in new):
            break
        for k, v in new.items():
            xseeds.setdefault(k, set()).update(v)
    print('pontos de entrada de outras unidades:', {k: len(v) for k, v in sorted(xseeds.items())})
    for nm in names:
        one(nm, dsk, kind, tk, chk, xseeds)


# as unidades sempre na memória (o mesmo endereço em todas as fases): um JSR/JMP de outra unidade
# para dentro delas é um ponto de entrada (ex.: os buracos do r40 pulam para o rB0 $B8D6, que
# nenhuma medição executou)
FIXED = ('r08', 'r1A', 'rB0', 't7', 't8')


def hole_jumps():
    """os JSR/JMP do código dos buracos das telas residentes (relocado à parte, fora do desmontador)"""
    res = open(RES, 'rb').read()
    out = set()
    for nm in ('r20', 'r40'):
        base = PKGS[nm][1]
        d = res[base:base + 0x2000]
        for h in range(0x78, 0x2000, 0x80):
            for k in range(h, h + 6):
                if d[k] in (0x20, 0x4C):
                    out.add(d[k + 1] | d[k + 2] << 8)
    return out


def cross_seeds():
    out = {}
    for src, targets in list(disa2.EXTERNAL.items()) + [('buracos', hole_jumps())]:
        for v in targets:
            for nm in FIXED:
                t, base, region, runs = PKGS[nm]
                n = {'r08': 0x200, 'r1A': 0x600}.get(nm, 0x1000)
                if base <= v < base + n:
                    out.setdefault(nm, set()).add(v)
    return out


def one(nm, dsk, kind, tk, chk, xseeds, quiet=False):
    if True:
        if tk:
            import sfrelocs
        t, base, region, runs = PKGS[nm]
        data = source(dsk, t, base)
        cov = starts(executed(region, base, runs, len(data)), base, data)
        disa2.coverage = lambda name, b, n, cov=cov: cov
        # nas telas, código só nos buracos (os últimos 8 bytes de cada grupo de 128): o resto é imagem
        allow = (lambda x: (x & 0x7F) >= 0x78) if nm in ('r20', 'r40') else None
        seeds = set(SEEDS.get(nm, ())) | xseeds.get(nm, set())
        lines, ncov, tot = disa2.disassemble(nm, base, data, sorted(seeds),
                                             sfrelocs.patches(nm, base, data) if tk else None, allow, INLINE)
        what = ('residente (memória depois da carga inicial)' if isinstance(t, tuple) else 'trilha %d' % t)
        lines[0] = '; Sky Fox (Electronic Arts, 1984), Apple II: %s, %s em $%04X-$%04X (%s)' % (
            nm, what, base, base + len(data) - 1, region)
        lines[1] = '; gerado por tools/dispkg.py: %d instruções que rodaram no voo (%s), mais %d pelo rastreio estático' % (
            ncov, ', '.join(runs), tot - ncov)
        if tk:
            lines[0] += ', para o TK2000 (tools/sfrelocs.py)'
        if quiet:
            return
        open(os.path.join(ROOT, 'src', kind, nm + '.s'), 'w').write('\n'.join(lines) + '\n')
        line = '%-4s %-8s $%04X %-4s  %4d instruções que rodaram, %4d com o rastreio' % (
            nm, 'residente' if isinstance(t, tuple) else 'trilha %d' % t, base, region, ncov, tot)
        if chk:
            line += '  remonta: ' + check(nm, base, None if tk else data, kind)
        print(line)


if __name__ == '__main__':
    main()
