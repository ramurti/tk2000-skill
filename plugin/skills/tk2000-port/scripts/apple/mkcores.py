#!/usr/bin/env python3
"""Junta os rastreios de cores (tools/sftaint.py --cores, build/taint/cores-NOME.txt) em
src/cores.json: por unidade, os bytes (imediatos e dados) que pintam o céu e o chão com os padrões
do Apple ("troca": sfrelocs.COLOR_MAP) e os bytes preto/branco da moldura da janela com o bit 7
ligado ("bit7"). Cada rastreio tem o estado do AppleWin de onde partiu (RUNS), para saber que
pacote estava em cada área.

    mkcores.py
"""
import os, re, json, sys
sys.path.insert(0, os.path.dirname(__file__))
import dispkg, areas, execpcs
import sflockstep as L
from collections import defaultdict, Counter

ROOT = dispkg.ROOT
AW = os.path.join(ROOT, 'build', 'aw')
RUNS = {
    'D164': 'snaps/snap-164.yaml', 'D161': 'snaps/snap-161.yaml', 'D167': 'snaps/snap-167.yaml',
    'A': 'snaps/snap-170.yaml', 'A17': 'sc0/snap-73.yaml', 'A17j': 'sc0/snap-73.yaml',
    'A22': 'sc1t/snap-50.yaml', 'B': 'end1/snap-62.yaml', 'B2': 'end1/snap-200.yaml',
    'L1': 'land1/snap-96.yaml', 'D128': 'snaps/snap-128.yaml', 'D128L': 'snaps/snap-128.yaml', 'MENU': 'snaps/snap-128.yaml',
}
FILL = {0xD5, 0xAA, 0x2A, 0x55}
MAIORIA = 0.6                           # a fração dos usos de um byte que decide a troca


def main():
    dsk = open(dispkg.DSK, 'rb').read()
    U = L.Units(dsk)
    troca, bit7, sem, conflito = defaultdict(set), defaultdict(set), Counter(), defaultdict(set)
    marks, vals, dyn = defaultdict(Counter), {}, Counter()
    for run, f in RUNS.items():
        path = os.path.join(ROOT, 'build', 'taint', 'cores-%s.txt' % run)
        if not os.path.exists(path):
            continue
        res = execpcs.residency(areas.load(os.path.join(AW, f)), U)

        def unit(a):
            for nm, (b, n, reg) in res.items():
                if reg == 'main' and a < 0xC000 and b <= a < b + n:
                    return nm
                if reg == 'lchi' and a >= 0xE000 and b <= a < b + n:
                    return nm
                if reg == 'lc2' and 0xD000 <= a < 0xE000:
                    return nm
            return None
        for ln in open(path):
            m = re.match(r'(\w+)\s+\$(\w{4})\s+valor \$(\w\w)\s+<- (.*?)(?:  @(\w+))?$', ln.rstrip('\n'))
            if not m:
                continue
            a, v, us = int(m.group(2), 16), int(m.group(3), 16), m.group(4)
            if m.group(5) is not None:          # a unidade anotada pelo rastreio (depois das cargas)
                nm = None if m.group(5) == 'None' else m.group(5)
            else:
                nm = unit(a)
            if 0x2000 <= a < 0x6000 or a < 0x200:      # cópias de tela, página zero e pilha
                continue
            kinds = Counter()
            for mm in re.finditer(r'\$\w{4} (\w+) x(\d+)', us):
                kinds[mm.group(1)] += int(mm.group(2))
            if not nm:
                sem['$%04X' % (a & 0xFF00)] += 1
                continue
            base = dispkg.PKGS[nm][1]
            if not 0 <= a - base < len(U.src[nm]):
                dyn[nm] += 1
                continue
            marks[(nm, a)].update(kinds)        # (o valor no disco: o jogo reescreve alguns imediatos
            vals[(nm, a)] = U.src[nm][a - base]  # de cor durante o desenho, coluna a coluna)
    for (nm, a), kinds in marks.items():        # todas as marcas do byte, de todos os rastreios
        v = vals[(nm, a)]
        if kinds['troca']:                      # regra de tools/sfcores.py, pela maioria dos usos: as
            if kinds['troca'] >= MAIORIA * (kinds['troca'] + kinds['mantem']):   # bordas da máscara e
                troca[nm].add(a)                # as colunas trocadas de vez em quando não contam
            else:
                conflito[nm].add(a)             # pinta céu/chão e outra coisa: fica como está
        if kinds['bit7'] and kinds['bit7'] >= MAIORIA * (kinds['bit7'] + kinds['mbw']) and v not in FILL:
            bit7[nm].add(a)
    out = {'comentario': 'cores do voo e da abertura, opção B (25/11/2026), regra de tools/sfcores.py: "troca" = '
                         'bytes que pintam só céu e chão (sfrelocs.COLOR_MAP); "bit7" = preto/branco da moldura '
                         'da janela com o bit 7 ligado (desligado: sem degraus ciano); "conflito" = pintam céu/chão '
                         'e outra coisa (ficam). Gerado por tools/mkcores.py.',
           'troca': {k: sorted(v) for k, v in sorted(troca.items())},
           'bit7': {k: sorted(v) for k, v in sorted(bit7.items())},
           'conflito': {k: sorted(v) for k, v in sorted(conflito.items())}}
    json.dump(out, open(os.path.join(ROOT, 'src', 'cores.json'), 'w'), indent=1)
    print('troca:', {k: len(v) for k, v in sorted(troca.items())})
    print('bit 7:', {k: len(v) for k, v in sorted(bit7.items())})
    print('conflito (janela e cockpit):', {k: len(v) for k, v in sorted(conflito.items())})
    if dyn:
        print('fora da unidade:', dict(dyn))
    if sem:
        print('sem unidade:', dict(sem.most_common(8)))


if __name__ == '__main__':
    main()
