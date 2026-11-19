#!/usr/bin/env python3
"""Compara Collide com a rotina que ela substituiu (CollideOld, numa compilação com COLLTEST): o
programa inteiro no py65 (as pilotagens de tools/lockstep.py, tools/hillcheck.py e
tools/sndprev.py: o carro jogado contra as bordas, freando), e a cada chamada de Collide as duas
rotinas rodam sobre cópias da memória naquele momento; as colisões delas (CXM0P, CXP0FB) e os
intervalos das bordas (minL, maxL, minR, maxR) têm de ser iguais. Também os ciclos de cada uma.

Uso: collcheck.py [tiques]
"""
import os
import subprocess
import sys

from py65.devices.mpu6502 import MPU

sys.path.insert(0, os.path.dirname(__file__))
import hillcheck as H  # noqa: E402
import lockstep as L  # noqa: E402
import sndprev as S  # noqa: E402


def build():
    subprocess.check_call(['ca65', '-g', '-D', 'COLLTEST', '-I', 'src', '-I', '.', '-o', 'build/colltest.o',
                           'src/main.s'])
    subprocess.check_call(['ld65', '-C', 'cfg/enduro.cfg', '-Ln', 'build/colltest.lbl', '-o',
                           'build/colltest.bin', 'build/colltest.o'])
    lab = {}
    for line in open('build/colltest.lbl'):
        _, a, nm = line.split()
        lab[nm.lstrip('.')] = int(a, 16)
    return lab


def call(mem, addr):
    m = bytearray(mem)
    u = MPU(memory=m, pc=addr)
    u.sp = 0xF0
    m[0x1F1] = m[0x1F2] = 0xFF
    while u.pc != 0:
        u.step()
    return m, u.processorCycles


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 2000
    lab = build()
    prog = open('build/colltest.bin', 'rb').read()
    calls = bad = 0
    cyc_old = cyc_new = 0
    for drive in (L.inputs, H.drive, S.drive):
        mem = bytearray(0x10000)
        mem[0x4000:0x4000 + len(prog)] = prog
        t = MPU(memory=mem, pc=0x4000)
        f = 0
        while f < n:
            pc = t.pc
            if pc == lab['ReadKeys']:
                s, b, fi = drive(f + 1)
                mem[0x280], mem[0x282], mem[0x3C] = s, b, 0 if fi else 0x80
                r = mem[0x100 + ((t.sp + 1) & 0xFF)] | mem[0x100 + ((t.sp + 2) & 0xFF)] << 8
                t.sp = (t.sp + 2) & 0xFF
                t.pc = r + 1
                continue
            if pc == lab['Collide']:
                a, ca = call(mem, lab['CollideOld'])
                b, cb = call(mem, lab['Collide'])
                calls += 1
                cyc_old += ca
                cyc_new += cb
                keys = [0x00, 0x02] + [lab[k] for k in ('minL', 'maxL', 'minR', 'maxR')]
                if [a[k] for k in keys] != [b[k] for k in keys]:
                    bad += 1
                    if bad <= 5:
                        print('tique %d: antiga %s nova %s' % (f, [a[k] for k in keys], [b[k] for k in keys]))
            t.step()
            if pc == L.MAINLOOP:
                f += 1
                mem[0] = mem[2] = mem[7] = 0
    print('%d chamadas, %d diferentes; ciclos por chamada: antiga %.0f, nova %.0f' % (
        calls, bad, cyc_old / max(calls, 1), cyc_new / max(calls, 1)))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
