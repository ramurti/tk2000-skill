#!/usr/bin/env python3
"""Lê os resultados do tools/taint.py e lista os bytes que são bytes altos de endereços dentro das
áreas trocadas ($4000-$5FFF, $A000-$BFFF) e ainda não estão no tools/relocs.py, com o valor deles no
arquivo (a saída do taint mostra a memória no fim, que cargas posteriores podem ter mudado).
Operandos de código (rótulos: o montador cuida deles) ficam de fora.

    candidates.py build/taint*.txt
"""
import os
import re
import sys

import relocs
from disa2 import units, coverage, OPS, LEN

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


def code_operand(name, base, data, a, cov):
    """a = o byte alto do operando de uma instrução de 3 bytes executada? (o rótulo dela o move)"""
    c = a - 2
    return c in cov and LEN[OPS[data[c - base]][1]] == 3


def main():
    u = units()
    covs = {f: coverage(f, b, len(d)) for f, (b, d) in u.items()}
    found = {}
    for path in sys.argv[1:]:
        for line in open(path):
            m = re.match(r'(imm|data) +(\w+) +\$([0-9A-F]{4})', line)
            if not m or m.group(2) == 'boot':
                continue
            kind, f, a = m.group(1), m.group(2), int(m.group(3), 16)
            if f not in u:
                continue
            base, data = u[f]
            v = data[a - base]
            if (0x40 <= v < 0x60 or 0xA0 <= v < 0xC0) and not code_operand(f, base, data, a, covs[f]):
                if a not in relocs.HI.get(f, []):
                    found.setdefault(f, {})[a] = (kind, v, line.split('<-')[1].strip()[:70])
    for f in sorted(found):
        print(f, ', '.join('0x%04X' % a for a in sorted(found[f])))
        for a in sorted(found[f]):
            k, v, users = found[f][a]
            print('   $%04X %-4s $%02X  %s' % (a, k, v, users))


if __name__ == '__main__':
    main()
