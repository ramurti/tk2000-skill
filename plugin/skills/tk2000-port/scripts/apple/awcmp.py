#!/usr/bin/env python3
"""Compara o Apple do py65 com o AppleWin: parte de um estado salvo do AppleWin (A.yaml), roda o
py65 até o ciclo exato de outro estado salvo (B.yaml) e lista o que difere (registradores, páginas
da RAM, language card).

    awcmp.py DISK.dsk A.yaml B.yaml [-D 32] [-v]
"""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
import sfboot
from a2boot import Mem
from py65.devices.mpu6502 import MPU


def state(path, dsk):
    ap = sfboot.Study(dsk)
    mpu = MPU(memory=Mem(ap), pc=0)
    mpu.cycletime = list(mpu.cycletime); mpu.cycletime[0xCE] = 6
    ap.mpu = mpu; ap.fire_from = 1 << 62
    sfboot.load_applewin(ap, path)
    return ap


def main():
    a = sys.argv[1:]
    dsk = open(a[0], 'rb').read()
    A, B = state(a[1], dsk), state(a[2], dsk)
    if '-D' in a: A.disk_cycles = int(a[a.index('-D') + 1])
    m = A.mpu
    while m.processorCycles < B.mpu.processorCycles:
        m.step()
    b = B.mpu
    print('ciclo py65 %d, AppleWin %d' % (m.processorCycles, b.processorCycles))
    print('py65:     PC=%04X A=%02X X=%02X Y=%02X S=%02X P=%02X' % (m.pc, m.a, m.x, m.y, m.sp, m.p))
    print('AppleWin: PC=%04X A=%02X X=%02X Y=%02X S=%02X P=%02X' % (b.pc, b.a, b.x, b.y, b.sp, b.p))
    for name, x, y, base in (('RAM', A.ram[:0xC000], B.ram[:0xC000], 0), ('LC1', A.lc[0], B.lc[0], 0xD000),
                             ('LC2', A.lc[1], B.lc[1], 0xD000), ('LChi', A.lc_hi, B.lc_hi, 0xE000)):
        d = [base + k for k in range(len(x)) if x[k] != y[k]]
        pages = sorted({k >> 8 for k in d})
        print('%s: %d bytes diferentes em %d páginas %s' % (name, len(d), len(pages), ' '.join('%02X' % p for p in pages[:40])))
        if '-v' in a:
            for k in d[:40]:
                print('   $%04X py65 %02X AppleWin %02X' % (k, x[k - base], y[k - base]))


if __name__ == '__main__':
    main()
