#!/usr/bin/env python3
"""Ciclos de CPU por quadro do programa do TK2000 no py65 (build/tennis.bin), com uma troca de
bolas em andamento (RESET, o botão de vez em quando): a parte do original (de Overscan a TkFrame)
e o desenho deste programa (TkFrame sem Pace). Para calibrar o ritmo (src/main.s).

Uso: cost.py [quadros] [--polls]

--polls: também o tempo médio de TkFrame até cada checkpoint do som (Poll em src/sound.s, com o
argumento em A), para CHECKPOINTS em tools/mktables.py.
"""
import os
import statistics
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from py65.devices.mpu6502 import MPU  # noqa: E402
from vcs import ROOT  # noqa: E402

lab = {}
for line in open(os.path.join(ROOT, 'build', 'tennis.lbl')):
    _, a, n = line.split()
    lab[n.lstrip('.')] = int(a, 16)
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
args = [a for a in sys.argv[1:] if not a.startswith('-')]
frames = int(args[0]) if args else 600
polls = {}
orig_lo, orig_hi = 0x4000, 0x4800
logic, draw = [], []
t_frame = t_pace = None
pace = lab['Pace']
inside = 0
for i in range(frames):
    while tk.pc != lab['TkFrame']:
        tk.step()
    t = tk.processorCycles
    if t_frame is not None:
        logic.append(t - t_exit)
    # o quadro: até voltar ao original, sem Pace
    paced = 0
    while not (orig_lo <= tk.pc < orig_hi):
        if tk.pc == pace:
            p0 = tk.processorCycles
            ret = (mem[0x101 + tk.sp] | mem[0x102 + tk.sp] << 8) + 1
            while tk.pc != ret:
                tk.step()
            paced += tk.processorCycles - p0
            continue
        if tk.pc == lab['Poll']:
            polls.setdefault(tk.a, []).append(tk.processorCycles - t)
        tk.step()
    t_exit = tk.processorCycles
    draw.append(t_exit - t - paced)
    t_frame = t
    # entradas: RESET no quadro 30, o botão a cada 97 quadros
    mem[0x282] = 0x0A if 30 <= i < 34 else 0x0B
    mem[0x0C] = 0x00 if i % 97 in range(40, 45) else 0x80
for name, v in (('original', logic[60:]), ('desenho', draw[60:])):
    print('%-9s média %5d  mín %5d  máx %5d' % (name, statistics.mean(v), min(v), max(v)))
if '--polls' in sys.argv:
    print('checkpoints:', [round(statistics.median(polls[k])) for k in sorted(polls)])
