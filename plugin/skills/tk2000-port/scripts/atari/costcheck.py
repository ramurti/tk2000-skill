#!/usr/bin/env python3
"""Compara, quadro a quadro, o custo em ciclos que o programa estima (o contador de custo na
entrada de Pace + COST_FRAME, em unidades de 5 ciclos) com os ciclos que ele gastou de verdade
(sem a espera de Delay).

Uso: costcheck.py [quadros]
"""
import os
import re
import sys
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from calibrate import Memory, labels, ROOT  # noqa: E402


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 1000
    variant = os.environ.get('VARIANT', 'river')
    lab = labels(variant + '.lbl')
    binary = open(os.path.join(ROOT, 'build', variant + '.bin'), 'rb').read()
    src = open(os.path.join(ROOT, 'src', 'main.s')).read()
    cost_frame = int(re.search(r'^COST_FRAME\s*=\s*(\d+)', src, re.M).group(1))
    mem = Memory()
    mem.mem[0x4000:0x4000 + len(binary)] = binary
    low = open(os.path.join(ROOT, 'build', 'river_low.bin'), 'rb').read()
    mem.mem[0x0800:0x0800 + len(low)] = low
    mpu = MPU(memory=mem, pc=lab['NewGame'])
    while mpu.pc != lab['MainLoop']:
        mpu.step()
    est_total = real_total = 0
    worst = []
    for f in range(frames):
        mem.pressed = [set(), {'up'}, {'left'}, set(), {'down'}, {'right'}][(f // 150) % 6] | ({'space'} if f % 40 < 25 else set())
        start, delay, est, new_life = mpu.processorCycles, 0, None, False
        while True:
            mpu.step()
            pc = mpu.pc
            if pc == lab['Pace']:
                est = (mem.mem[0x20] | mem.mem[0x21] << 8) + cost_frame
            elif pc == lab['Delay']:
                ret = (mem.mem[0x101 + mpu.sp] | mem.mem[0x102 + mpu.sp] << 8) + 1
                d0 = mpu.processorCycles
                while mpu.pc != ret:
                    mpu.step()
                delay = mpu.processorCycles - d0
            elif pc == lab['NewLife']:
                new_life = True
            elif pc == lab['MainLoop']:
                break
        if new_life or f < 50:
            continue
        real = mpu.processorCycles - start - delay
        est_total += est * 5
        real_total += real
        worst.append(real / (est * 5))
    worst.sort()
    print('%s: real/estimado = %.3f (por quadro: 5%% %.2f, mediana %.2f, 95%% %.2f)' % (
        variant, real_total / est_total, worst[len(worst) // 20], worst[len(worst) // 2],
        worst[-len(worst) // 20]))


if __name__ == '__main__':
    main()
