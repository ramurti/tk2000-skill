#!/usr/bin/env python3
"""Ciclos por instrução do programa do TK2000 (build/river.bin no py65), com as linhas do fonte.

Uso: hotspots.py [quadros] [primeiras]
"""
import os
import re
import sys
from collections import defaultdict
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from calibrate import Memory, labels, ROOT  # noqa: E402


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 500
    top = int(sys.argv[2]) if len(sys.argv) > 2 else 40
    lab = labels('river.lbl')
    binary = open(os.path.join(ROOT, 'build', 'river.bin'), 'rb').read()
    mem = Memory()
    mem.mem[0x4000:0x4000 + len(binary)] = binary
    low = open(os.path.join(ROOT, 'build', 'river_low.bin'), 'rb').read()
    mem.mem[0x0800:0x0800 + len(low)] = low
    mpu = MPU(memory=mem, pc=lab['NewGame'])
    while mpu.pc != lab['MainLoop']:
        mpu.step()
    hist = defaultdict(int)
    for f in range(frames):
        mem.pressed = [set(), {'up'}, {'left'}, set(), {'down'}, {'right'}][(f // 150) % 6] | ({'space'} if f % 40 < 25 else set())
        while True:
            pc, c = mpu.pc, mpu.processorCycles
            mpu.step()
            if f >= 100:
                hist[pc] += mpu.processorCycles - c
            if mpu.pc == lab['MainLoop']:
                break
    seg = {}
    for line in open(os.path.join(ROOT, 'build', 'river.map')):
        m = re.match(r'(\w+)\s+([0-9A-F]{6})\s+([0-9A-F]{6})', line)
        if m:
            seg[m.group(1)] = int(m.group(2), 16)
    src, cur = {}, None
    for line in open(os.path.join(ROOT, 'build', 'main.lst'), errors='replace'):
        if '.segment "CODE"' in line:
            cur = 'CODE'
        elif '.segment' in line:
            cur = None
        m = re.match(r'([0-9A-F]{6})r \d+\s+(.*)', line)
        if m and cur == 'CODE':
            txt = m.group(2).strip()
            if txt and not txt.startswith(';'):
                src.setdefault(int(m.group(1), 16) + seg['CODE'], txt[:60])
    names = sorted((a, n) for n, a in lab.items())

    def near(a):
        best = None
        for addr, n in names:
            if addr > a:
                break
            best = n
        return best
    total = sum(hist.values())
    for a, c in sorted(hist.items(), key=lambda x: -x[1])[:top]:
        print('%5.1f%%  %04X  %-16s %s' % (100 * c / total, a, near(a), src.get(a, '')))


if __name__ == '__main__':
    main()
