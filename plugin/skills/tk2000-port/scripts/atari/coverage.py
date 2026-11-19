#!/usr/bin/env python3
"""Roda o cartucho no simulador (tools/reference/vcs.py) com entradas roteirizadas (SELECT,
RESET, os dois joysticks, as chaves de dificuldade e de cor) e registra quais bytes da ROM rodam
como código e quais são lidos como dados: build/coverage.json, para tools/dis2600.py.

Uso: coverage.py [quadros]
"""
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcs import VCS, ROOT  # noqa: E402

frames = int(sys.argv[1]) if len(sys.argv) > 1 else 4000
rnd = random.Random(2600)
v = VCS()
code = set()
step = v.step


def traced_step():
    code.add(v.mpu.pc & 0x7FF)
    step()


v.step = traced_step
joy = 0xFF
for f in range(frames):
    swchb = 0x0B
    if f % 300 in range(20, 24) and f < 1200:
        swchb &= ~0x02                          # SELECT
    if f % 900 in range(250, 254):
        swchb &= ~0x01                          # RESET
    if (f // 700) % 2:
        swchb ^= 0x08                           # cor / preto e branco
    swchb |= (f // 500 % 4) << 6                # chaves de dificuldade
    v.swchb = swchb
    if f % 15 == 0:
        joy = rnd.choice((0xF, 0x7, 0xB, 0xD, 0xE, 0x5, 0x9, 0x6, 0xA)) << 4 | \
            rnd.choice((0xF, 0x7, 0xB, 0xD, 0xE, 0x5, 0x9, 0x6, 0xA))
    v.swcha = joy
    v.fire = rnd.random() < 0.2
    v.frame(max_cycles=600000)
data = v.reads - code
json.dump({'code': sorted(code), 'reads': sorted(v.reads)},
          open(os.path.join(ROOT, 'build', 'coverage.json'), 'w'))
print('%d quadros: %d inícios de instrução, %d bytes da ROM lidos' % (frames, len(code), len(v.reads)))
