#!/usr/bin/env python3
"""Ciclos por quadro gastos em cada rotina chamada de MainLoop (build/river.bin no py65).

Uso: profile.py [quadros]
"""
import os
import sys
from collections import defaultdict
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from calibrate import Memory, labels, ROOT  # noqa: E402

ROUTINES = ['ReadKeys', 'Tick', 'SetPagePointers', 'JetPrepare', 'JetRowsCheck', 'DrawRiver',
            'ShiftRects', 'JetUpdate', 'ComposeObjects', 'DrawJet', 'Pace']


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 600
    variant = os.environ.get('VARIANT', 'river')
    lab = labels(variant + '.lbl')
    binary = open(os.path.join(ROOT, 'build', variant + '.bin'), 'rb').read()
    mem = Memory()
    mem.mem[0x4000:0x4000 + len(binary)] = binary
    low = open(os.path.join(ROOT, 'build', 'river_low.bin'), 'rb').read()
    mem.mem[0x0800:0x0800 + len(low)] = low
    mpu = MPU(memory=mem, pc=lab['NewGame'])
    while mpu.pc != lab['MainLoop']:
        mpu.step()
    entry = {lab[r]: r for r in ROUTINES}
    total = defaultdict(int)
    counted = 0
    for f in range(frames):
        mem.pressed = [set(), {'up'}, {'left'}, set(), {'down'}, {'right'}][(f // 150) % 6] | ({'space'} if f % 40 < 25 else set())
        start, new_life = mpu.processorCycles, False
        per = defaultdict(int)
        while True:
            mpu.step()
            name = entry.get(mpu.pc)
            if name:
                ret = (mem.mem[0x101 + mpu.sp] | mem.mem[0x102 + mpu.sp] << 8) + 1
                c0 = mpu.processorCycles
                while mpu.pc != ret:
                    mpu.step()
                    if mpu.pc == lab['NewLife']:
                        new_life = True
                per[name] += mpu.processorCycles - c0
            if mpu.pc == lab['MainLoop']:
                break
        if new_life or f < 100:
            continue
        counted += 1
        per['(outros)'] = mpu.processorCycles - start - sum(per.values())
        for k, v in per.items():
            total[k] += v
    work = sum(v for k, v in total.items() if k != 'Pace')
    print('%d quadros, %.0f ciclos de trabalho por quadro (%.1f fps sem esperar)' % (
        counted, work / counted, 1022727 * counted / work))
    for k, v in sorted(total.items(), key=lambda x: -x[1]):
        print('  %-16s %7.0f ciclos/quadro  %5.1f%%' % (k, v / counted, 100 * v / sum(total.values())))


if __name__ == '__main__':
    main()
