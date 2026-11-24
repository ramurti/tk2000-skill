#!/usr/bin/env python3
"""Uso da memória: parte de um estado salvo do AppleWin, roda o Apple do py65 e marca cada byte lido,
escrito ou executado (RAM principal, banco 1 e 2 de $D000, $E000-$FFFF do language card), e cada
troca de banco do language card com o PC. Grava OUT.npz-like (OUT.bin: 4 mapas de bits) e imprime
um resumo.

    usage.py DISK.dsk SNAP.yaml CYCLES OUTPREFIX [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA]
"""
import os, pickle, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import sfboot
from a2boot import Mem
from py65.devices.mpu6502 import MPU
from py65.disassembler import Disassembler

R, W, X = 1, 2, 4


class Use(sfboot.Study):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.u = {'main': bytearray(0xC000), 'lc1': bytearray(0x1000), 'lc2': bytearray(0x1000),
                  'lchi': bytearray(0x2000)}
        self.sw = []
        self.joy = [128, 128]
        self.btn = [False, False]

    def mark(self, addr, f, write=False):
        if self.motor:                                         # cargas de disco: não contam como uso
            return
        if addr < 0xC000:
            self.u['main'][addr] |= f
        elif addr >= 0xD000 and (self.lc_write if write else self.lc_read):
            if addr < 0xE000:
                self.u['lc%d' % self.lc_bank][addr - 0xD000] |= f
            else:
                self.u['lchi'][addr - 0xE000] |= f

    def read(self, addr):
        self.mark(addr, R)
        return super().read(addr)

    def write(self, addr, v):
        self.mark(addr, W, True)
        super().write(addr, v)

    def io(self, addr):
        if 0xC080 <= addr <= 0xC08F:
            self.sw.append((self.mpu.processorCycles, self.mpu.pc, addr))
        return super().io(addr)

    def stick(self, n):
        return self.joy[n]

    def buttons(self, b):
        return self.btn[b] if b < 2 else False


def main():
    a = sys.argv[1:]
    dsk = open(a[0], 'rb').read()
    ap = Use(dsk)
    m = MPU(memory=Mem(ap), pc=0)
    m.cycletime = list(m.cycletime); m.cycletime[0xCE] = 6
    ap.mpu = m; ap.fire_from = 1 << 62; ap.disk_cycles = 32
    sfboot.load_applewin(ap, a[1])
    t0 = m.processorCycles
    end = t0 + int(a[2])
    ev = []
    i = 4
    while i < len(a):
        t, _, v = a[i + 1].partition(':')
        ev.append((t0 + int(float(t) * 1020484), a[i], v)); i += 2
    ev.sort()
    d = Disassembler(m)
    ln = {}
    while m.processorCycles < end:
        while ev and m.processorCycles >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ap.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ap.joy['xy'.index(k)] = int(n)
                    else: ap.btn[int(k[1])] = n != '0'
        pc = m.pc
        op = ap.read(pc)
        if op not in ln:
            ln[op] = d.instruction_at(pc)[0]
        for k in range(ln[op]):
            ap.mark((pc + k) & 0xFFFF, X)
        m.step()
    pickle.dump((ap.u, ap.sw), open(a[3] + '.pkl', 'wb'))
    for k, arr in ap.u.items():
        used = sum(1 for b in arr if b)
        print('%-4s usados %5d de %5d (executados %d)' % (k, used, len(arr), sum(1 for b in arr if b & X)))
    c = Counter((pc & 0xFF00, addr) for _, pc, addr in ap.sw)
    print('trilhas lidas:', ' '.join('%.1fs:%d' % ((c - t0) / 1020484, t) for c, t in ap.track_log))
    print('trocas de banco:', len(ap.sw), ' '.join('$%04X@$%04X:%d' % (addr, pc, n) for (pc, addr), n in c.most_common(12)))


if __name__ == '__main__':
    main()
