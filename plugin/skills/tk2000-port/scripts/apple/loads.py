#!/usr/bin/env python3
"""Inventário das cargas de disco: dá boot no .dsk (Apple do py65) e, para cada intervalo em que o
motor do disco fica ligado, registra as trilhas lidas, as faixas de memória escritas (RAM principal,
language card) e os PCs que escreveram. Também marca o código executado depois de cada carga.

    loads.py DISK.dsk OUT.txt [-c MAX_CYCLES] [-k CYCLE[:KEY]]... [-A SNAP.yaml] [-D N]
"""
import os, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(__file__))
import sfboot
from a2boot import Mem, P2D, WRITE_TABLE
from py65.devices.mpu6502 import MPU


class Loads(sfboot.Study):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.cur = None
        self.done = []

    def where(self, addr):
        if addr < 0xC000:
            return 'main', addr
        if addr >= 0xD000 and self.lc_write:
            if addr < 0xE000:
                return 'lc%d' % self.lc_bank, addr
            return 'lchi', addr
        return None, addr

    def write(self, addr, v):
        if self.cur is not None:
            k, a = self.where(addr)
            if k:
                self.cur['w'][(k, a >> 8)] += 1
                self.cur['pc'][self.mpu.pc & 0xFF00] += 1
        super().write(addr, v)

    def io(self, addr):
        a = addr & 0xFF
        if a == 0xE9 and self.cur is None:
            self.cur = {'start': self.mpu.processorCycles, 'tracks': [], 'w': Counter(), 'pc': Counter()}
        if a == 0xE8 and self.cur is not None:
            self.cur['end'] = self.mpu.processorCycles
            self.done.append(self.cur)
            self.cur = None
        if a == 0xEC and self.cur is not None:
            t = self.ht // 2
            if not self.cur['tracks'] or self.cur['tracks'][-1] != t:
                self.cur['tracks'].append(t)
        return super().io(addr)


def ranges(pages):
    ps = sorted(pages)
    out, s = [], None
    for p in ps:
        if s is None:
            s = e = p
        elif p == e + 1:
            e = p
        else:
            out.append((s, e)); s = e = p
    if s is not None:
        out.append((s, e))
    return ' '.join('$%02X00-$%02XFF' % r for r in out)


def main():
    a = sys.argv[1:]
    dsk = open(a[0], 'rb').read()
    out = a[1]
    maxc, keys, snap, dc = 205_000_000, [], None, 0
    i = 2
    while i < len(a):
        if a[i] == '-c': maxc = int(a[i + 1]); i += 2
        elif a[i] == '-k':
            c, _, k = a[i + 1].partition(':')
            keys.append((int(c), {'r': 0x0D, 'esc': 0x1B}.get(k, ord(k) if k else 0x20) | 0x80)); i += 2
        elif a[i] == '-A': snap = a[i + 1]; i += 2
        elif a[i] == '-D': dc = int(a[i + 1]); i += 2
        else: sys.exit('desconhecido: ' + a[i])
    ap = Loads(dsk)
    mpu = MPU(memory=Mem(ap), pc=0x0801)
    mpu.cycletime = list(mpu.cycletime); mpu.cycletime[0xCE] = 6
    ap.mpu = mpu; ap.fire_from = 1 << 62; ap.disk_cycles = dc
    if snap:
        sfboot.load_applewin(ap, snap)
    else:
        n = dsk[0]
        for p in range(n):
            ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[P2D[p] * 256:P2D[p] * 256 + 256]
        ap.ram[0x2B] = 0x60
        for k, v in enumerate(WRITE_TABLE):
            ap.ram[0x02D6 + v] = k
        ap.ram[0x3D] = n
        mpu.x = 0x60; mpu.sp = 0xFF
    keys.sort()
    f = open(out, 'w')
    nd = 0
    while mpu.processorCycles < maxc:
        if keys and mpu.processorCycles >= keys[0][0]:
            ap.key = keys.pop(0)[1]
        mpu.step()
        while nd < len(ap.done):
            L = ap.done[nd]; nd += 1
            by = {}
            for (k, p), n in L['w'].items():
                by.setdefault(k, set()).add(p)
            line = 'carga %d: ciclos %d-%d (%.1f-%.1f s) trilhas %s\n' % (
                nd, L['start'], L['end'], L['start'] / 1.0205e6, L['end'] / 1.0205e6,
                ','.join(map(str, L['tracks'])))
            for k in ('main', 'lc1', 'lc2', 'lchi'):
                if k in by:
                    line += '   %-4s %s\n' % (k, ranges(by[k]))
            line += '   escrito por código em %s\n' % ' '.join('$%04X:%d' % x for x in L['pc'].most_common(6))
            f.write(line); f.flush(); print(line, end='', flush=True)


if __name__ == '__main__':
    main()
