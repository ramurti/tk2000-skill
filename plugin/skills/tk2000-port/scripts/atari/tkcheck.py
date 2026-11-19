#!/usr/bin/env python3
"""Roda o programa do TK2000 (build/tennis.bin, no py65) ao lado do cartucho original
(tools/reference/vcs.py) com as mesmas entradas roteirizadas, e compara as variáveis do original
($80-$D5) a cada quadro: no WaitVblank do original e em TkFrame, para onde a versão do TK2000
salta no lugar dele. Variáveis que só o kernel usa ficam de fora.

Uso: tkcheck.py [quadros]
"""
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py65.devices.mpu6502 import MPU  # noqa: E402
from vcs import VCS, ROOT  # noqa: E402

KERNEL_ONLY = {0x8A, 0x8B, 0xB5, 0xBA, 0xBD, 0xBE} | set(range(0xA4, 0xB4))
frames = int(sys.argv[1]) if len(sys.argv) > 1 else 3000


def labels():
    lab = {}
    for line in open(os.path.join(ROOT, 'build', 'tennis.lbl')):
        _, a, n = line.split()
        lab[n.lstrip('.')] = int(a, 16)
    return lab


def inputs(i, rnd):
    """RESET no quadro 30 e a cada 1500 quadros, o botão de vez em quando, o joystick ao acaso."""
    swchb = 0x0A if 30 <= i < 34 or i % 1500 in range(700, 704) else 0x0B
    fire = i % 97 in range(40, 45)
    return swchb, fire, inputs.joy


inputs.joy = 0xFF
rnd = random.Random(1)
lab = labels()
LOOP = lab['TkFrame']

# o programa do TK2000
mem = bytearray(0x10000)
data = open(os.path.join(ROOT, 'build', 'tennis.bin'), 'rb').read()
mem[0x4000:0x4000 + len(data)] = data
tk = MPU(memory=mem)
tk.cycletime = list(tk.cycletime)
tk.cycletime[0xCE] = 6
tk.pc = 0x4800
while tk.pc != lab['StartScreen']:              # (a tela inicial: nível 3, como no original)
    tk.step()
tk.pc = (mem[0x101 + tk.sp] | mem[0x102 + tk.sp] << 8) + 1
tk.sp += 2
# o original
v = VCS()

def run_tk_to(pc):
    while tk.pc != pc:
        tk.step()


def run_vcs_to(pc):
    while v.mpu.pc != pc:
        v.step()


diffs = 0
set_inputs = lab['SetInputs']
for i in range(frames):
    run_tk_to(LOOP)
    run_vcs_to(0xF051)
    a = [mem[x] for x in range(0x80, 0xD6)]
    b = [v.ram[x - 0x80] for x in range(0x80, 0xD6)]
    bad = [0x80 + k for k in range(len(a)) if a[k] != b[k] and 0x80 + k not in KERNEL_ONLY]
    if bad:
        diffs += 1
        if diffs <= 5:
            print('quadro %d: %s' % (i, ' '.join('$%02X:%02X/%02X' % (x, mem[x], v.ram[x - 0x80]) for x in bad)))
    if i % 20 == 0:
        inputs.joy = rnd.choice((0xFF, 0x7F, 0xBF, 0xDF, 0xEF))
    swchb, fire, joy = inputs(i, rnd)
    # o TK2000: deixa SetInputs rodar, depois põe as entradas roteirizadas por cima do que ela leu
    run_tk_to(set_inputs)
    ret = (mem[0x101 + tk.sp] | mem[0x102 + tk.sp] << 8) + 1
    run_tk_to(ret)
    mem[0x280], mem[0x282], mem[0x0C], mem[0x0D] = joy, swchb, 0x00 if fire else 0x80, 0x80
    v.swcha, v.swchb, v.fire = joy, swchb, fire
    run_vcs_to(0xF056)                          # (fora da espera do temporizador)
print('%d quadros: %d com variáveis diferentes' % (frames, diffs))
