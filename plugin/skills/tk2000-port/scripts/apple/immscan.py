#!/usr/bin/env python3
"""Lista padrões de bytes 'carga imediata + store' (LDA/LDX/LDY #hh, depois STA/STX/STY) cujo
imediato é um byte alto dentro das áreas trocadas, em todos os arquivos, com o que o relocs.py faz
com ele: candidatos a bytes altos que as ferramentas de execução nunca encontraram (código não executado).

    immscan.py
"""
import relocs
from disa2 import units

LOADS = {0xA9: (0x85, 0x8D, 0x95, 0x99, 0x9D, 0x81, 0x91), 0xA2: (0x86, 0x8E, 0x96), 0xA0: (0x84, 0x8C, 0x94)}


def main():
    u = units()
    hb = __import__('records').hi_bytes(u)
    for f in sorted(u):
        if f in ('A', 'F', 'O', 'LOADER', 'B'):
            continue
        base, d = u[f]
        for i in range(len(d) - 3):
            if d[i] in LOADS and d[i + 2] in LOADS[d[i]]:
                v = d[i + 1]
                if 0x40 <= v < 0x60 or 0xA0 <= v < 0xBB:
                    a = base + i + 1
                    known = 'HI' if a in relocs.HI.get(f, []) or a in hb.get(f, {}) else ''
                    ctx = ' '.join('%02X' % b for b in d[max(0, i - 4):i + 6])
                    print('%s $%04X  #$%02X  %-3s %s' % (f, a, v, known, ctx))


if __name__ == '__main__':
    main()
