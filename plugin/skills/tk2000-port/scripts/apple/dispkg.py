#!/usr/bin/env python3
"""Desmonta os pacotes de 4K do Sky Fox (uma trilha crua do disco num endereço fixo: página n =
setor DOS 15-n) em fontes ca65 (src/dis/tNN.s) que remontam nos mesmos bytes (--check).

Código = o que rodou com o pacote na memória (marcas de execução do tools/usage.py, build/use/*.pkl)
mais o rastreio estático do tools/disa2.py (desvios não tomados, destinos de JSR/JMP dentro do
pacote). O resto é dado (.byte).

    dispkg.py [--check] [tNN...]        (padrão: todos os pacotes da tabela PKGS)
"""
import os, pickle, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import disa2

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
DSK = os.path.join(ROOT, 'reference', 'Skyfox_1984_Electronic_Arts_cr_Black_Bag.dsk')
USE = os.path.join(ROOT, 'build', 'use')

# pacote: (trilha, endereço, região do usage.py, medições do usage.py com o pacote na memória);
# trilha 'res' (tamanho) = código residente, montado pela carga inicial: a referência é a memória
# logo depois dela (build/study/resident-14s.bin, do estado do AppleWin build/aw/res/snap-14.yaml)
FLY_A = ['A22', 'A17']
RES = os.path.join(ROOT, 'build', 'study', 'resident-14s.bin')
PKGS = {
    'r08': (('res', 0x200), 0x0800, 'main', FLY_A),
    't15': (15, 0x0A00, 'main', FLY_A),
    'r1A': (('res', 0x600), 0x1A00, 'main', FLY_A),
    'r20': (('res', 0x4000), 0x2000, 'main', FLY_A),
    'rB0': (('res', 0x1000), 0xB000, 'main', FLY_A),
    't7':  (7, 0x6000, 'main', FLY_A),
    't16': (16, 0x7000, 'main', FLY_A),
    't8':  (8, 0x8000, 'main', FLY_A),
    't14': (14, 0x9000, 'main', FLY_A),
    't22': (22, 0xA000, 'main', ['A22']),
    't17': (17, 0xA000, 'main', ['A17']),
    't18': (18, 0xD000, 'lc1', FLY_A),
    't23': (23, 0xD000, 'lc2', FLY_A),
    't24': (24, 0xE000, 'lchi', FLY_A),
    't29': (29, 0xF000, 'lchi', FLY_A),
}
X = 4
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


def check(name, base, data):
    src = os.path.join(ROOT, 'src', 'dis', name + '.s')
    out = os.path.join(ROOT, 'build', 'dis')
    os.makedirs(out, exist_ok=True)
    o, b = os.path.join(out, name + '.o'), os.path.join(out, name + '.bin')
    subprocess.run(['ca65', src, '-o', o], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'src', 'dis', 'raw.cfg'), o, '-o', b], check=True)
    got = open(b, 'rb').read()
    bad = [k for k in range(max(len(got), len(data))) if k >= len(got) or k >= len(data) or got[k] != data[k]]
    return 'idêntico' if not bad else '%d bytes diferentes, o primeiro em $%04X' % (len(bad), base + bad[0])


def main():
    a = sys.argv[1:]
    chk = '--check' in a
    names = [x for x in a if not x.startswith('--')] or list(PKGS)
    dsk = open(DSK, 'rb').read()
    os.makedirs(os.path.join(ROOT, 'src', 'dis'), exist_ok=True)
    for nm in names:
        t, base, region, runs = PKGS[nm]
        data = source(dsk, t, base)
        cov = starts(executed(region, base, runs, len(data)), base, data)
        disa2.coverage = lambda name, b, n, cov=cov: cov
        lines, ncov, tot = disa2.disassemble(nm, base, data)
        what = ('residente (memória depois da carga inicial)' if isinstance(t, tuple) else 'trilha %d' % t)
        lines[0] = '; Sky Fox (Electronic Arts, 1984), Apple II: %s, %s em $%04X-$%04X (%s)' % (
            nm, what, base, base + len(data) - 1, region)
        lines[1] = '; gerado por tools/dispkg.py: %d instruções que rodaram no voo A (%s), mais %d pelo rastreio estático' % (
            ncov, ', '.join(runs), tot - ncov)
        open(os.path.join(ROOT, 'src', 'dis', nm + '.s'), 'w').write('\n'.join(lines) + '\n')
        line = '%-4s %-8s $%04X %-4s  %4d instruções que rodaram, %4d com o rastreio' % (
            nm, 'residente' if isinstance(t, tuple) else 'trilha %d' % t, base, region, ncov, tot)
        if chk:
            line += '  remonta: ' + check(nm, base, data)
        print(line)


if __name__ == '__main__':
    main()
