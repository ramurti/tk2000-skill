#!/usr/bin/env python3
"""Diz que trilha do disco está em cada área de 4K da memória num estado salvo do AppleWin.

Cada carga do Sky Fox grava uma trilha crua numa área de 4K: página n da área = setor DOS 15-n da
trilha. Para cada área (RAM principal $0000-$BFFF, language card banco 1, banco 2, $E000, $F000)
conta quantas das 16 páginas são idênticas às de cada trilha e mostra a melhor.

    areas.py DISK.dsk SNAP.yaml [SNAP.yaml...]
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import sfboot


class _Mpu:
    pass


class _Ap:
    def __init__(self):
        self.ram = bytearray(0x10000)
        self.lc = [bytearray(0x1000), bytearray(0x1000)]
        self.lc_hi = bytearray(0x2000)
        self.mpu = _Mpu()


def load(path):
    ap = _Ap()
    try:
        sfboot.load_applewin(ap, path)
    except SystemExit:                      # motor ligado: a memória já foi lida, basta
        pass
    return ap


def areas(ap):
    out = [('$%04X' % a, ap.ram[a:a + 0x1000]) for a in range(0, 0xC000, 0x1000)]
    out += [('lc1 $D000', ap.lc[0]), ('lc2 $D000', ap.lc[1]),
            ('lc $E000', ap.lc_hi[:0x1000]), ('lc $F000', ap.lc_hi[0x1000:])]
    return out


def best(dsk, data):
    """(trilha, páginas iguais, páginas não-zero da área)"""
    nz = sum(1 for n in range(16) if any(data[n * 256:n * 256 + 256]))
    top = (None, 0)
    for t in range(1, 35):
        same = sum(1 for n in range(16) if any(data[n * 256:n * 256 + 256]) and
                   data[n * 256:n * 256 + 256] == dsk[t * 4096 + (15 - n) * 256:t * 4096 + (16 - n) * 256])
        if same > top[1]:
            top = (t, same)
    return top + (nz,)


def main():
    dsk = open(sys.argv[1], 'rb').read()
    for path in sys.argv[2:]:
        ap = load(path)
        print(os.path.basename(path))
        cells = []
        for name, data in areas(ap):
            t, same, nz = best(dsk, data)
            cells.append('%s:%s' % (name, ('t%d %d/%d' % (t, same, nz)) if t is not None else '-'))
        print('  ' + '  '.join(cells))


if __name__ == '__main__':
    main()
