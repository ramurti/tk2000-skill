#!/usr/bin/env python3
"""Mede os custos reais em ciclos do programa do TK2000 no py65, para calibrar as constantes
COST_* do ritmo de quadros (src/main.s).

Roda o próprio programa (build/river.bin) e conta de fora os eventos por trás de cada custo:
chamadas de Tick, NewBlock, DrawRoadRow; linhas e bytes de sprite a cada chamada de AddRowsCost
(desenho ou restauração, pelo endereço de retorno); grupos do renderizador, como escritas nas
tabelas Shown; linhas restauradas cujo fundo é calculado, como chamadas de BackgroundByte vindas
de RestoreRects.
Cada quadro (de MainLoop a MainLoop) é dividido em trabalho e Delay; o trabalho é ajustado por
mínimos quadrados como uma parte fixa mais um custo por evento. Quadros que começam uma vida nova
ficam de fora.

Uso: calibrate.py [quadros]
"""
import os
import sys
from py65.devices.mpu6502 import MPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
KEY_ROWS = {'up': (0x40, 1), 'down': (0x20, 1), 'left': (0x08, 1), 'right': (0x10, 1),
            'space': (0x04, 1)}
ZP = {'mulA': 0x6D, 'nbytes': 0x53, 'vbytes': 0x63, 'wu': 0x77}
SHOWN = (0x0B00, 0x0F00)        # Shown1PF1 .. Shown2PF2
SITES = ['tick', 'group', 'road row', 'block', 'draw row', 'draw byte', 'restore row',
         'restore byte', 'restore new', 'compose row', 'compose byte']
CONSTANTS = ['COST_TICK', 'COST_GROUP', 'COST_ROAD_ROW', 'COST_BLOCK', 'COST_DRAW_ROW',
             'COST_DRAW_BYTE', 'COST_RESTORE_ROW', 'COST_RESTORE_BYTE', 'COST_RESTORE_NEW',
             'COST_COMPOSE_ROW', 'COST_COMPOSE_BYTE']


class Memory:
    """RAM plana mais o teclado do TK2000: KBIN ($C010) responde pela linha selecionada em KBOUT."""

    def __init__(self):
        self.mem = bytearray(0x10000)
        self.kbout = 0
        self.pressed = set()
        self.shown_writes = 0

    def __len__(self):
        return 0x10000

    def __getitem__(self, addr):
        if isinstance(addr, slice):
            return [self[i] for i in range(*addr.indices(0x10000))]
        if addr == 0xC010:
            return 1 if any(self.kbout & KEY_ROWS[k][0] for k in self.pressed) else 0
        return self.mem[addr]

    def __setitem__(self, addr, value):
        if addr == 0xC000:
            self.kbout = value
        elif SHOWN[0] <= addr < SHOWN[1] and addr & 0xFF < 160:
            self.shown_writes += 1
        self.mem[addr] = value & 0xFF


def labels(name):
    out = {}
    for line in open(os.path.join(ROOT, 'build', name)):
        _, addr, label = line.split()
        out[label.lstrip('.')] = int(addr, 16)
    return out


def lstsq(rows, ys):
    n = len(rows[0])
    a = [[sum(r[i] * r[j] for r in rows) for j in range(n)] for i in range(n)]
    b = [sum(r[i] * y for r, y in zip(rows, ys)) for i in range(n)]
    for i in range(n):
        p = max(range(i, n), key=lambda k: abs(a[k][i]))
        a[i], a[p], b[i], b[p] = a[p], a[i], b[p], b[i]
        if abs(a[i][i]) < 1e-9:
            continue
        for k in range(i + 1, n):
            f = a[k][i] / a[i][i]
            for j in range(i, n):
                a[k][j] -= f * a[i][j]
            b[k] -= f * b[i]
    x = [0.0] * n
    for i in reversed(range(n)):
        x[i] = (b[i] - sum(a[i][j] * x[j] for j in range(i + 1, n))) / a[i][i] if abs(a[i][i]) > 1e-9 else 0
    return x


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 3000
    lab = labels('river.lbl')
    binary = open(os.path.join(ROOT, 'build', 'river.bin'), 'rb').read()
    mem = Memory()
    mem.mem[0x4000:0x4000 + len(binary)] = binary
    low = open(os.path.join(ROOT, 'build', 'river_low.bin'), 'rb').read()
    mem.mem[0x0800:0x0800 + len(low)] = low
    mpu = MPU(memory=mem, pc=lab['NewGame'])
    while mpu.pc != lab['MainLoop']:
        mpu.step()
    draw_range = (lab['SpriteDraw'], lab['AddRowsCost'])
    restore_range = (lab['RestoreRect'], lab['BackgroundByte'])
    compose_range = (lab['ComposeUnion'], lab['SpriteSetup'])
    caller = lambda: (mem.mem[0x101 + mpu.sp] | mem.mem[0x102 + mpu.sp] << 8) + 1
    rows, works = [], []
    for f in range(frames):
        # mudanças de velocidade e algumas curvas, para variar o trabalho
        mem.pressed = [set(), {'up'}, {'left'}, set(), {'down'}, {'right'}][(f // 150) % 6] | ({'space'} if f % 40 < 25 else set())
        counts = [0] * len(SITES)
        mem.shown_writes = 0
        start, delay_cycles, new_life = mpu.processorCycles, 0, False
        while True:
            mpu.step()
            pc = mpu.pc
            if pc == lab['Tick']:
                counts[0] += 1
            elif pc == lab['DrawRoadRow']:
                counts[2] += 1
            elif pc == lab['NewBlock']:
                counts[3] += 1
            elif pc == lab['AddRowsCost']:
                ret, n = caller(), mem.mem[ZP['mulA']]
                if draw_range[0] <= ret < draw_range[1]:
                    counts[4] += n
                    counts[5] += n * mem.mem[ZP['vbytes']]
                elif restore_range[0] <= ret < restore_range[1]:
                    counts[6] += n
                    counts[7] += n * mem.mem[ZP['nbytes']]
                elif compose_range[0] <= ret < compose_range[1]:
                    counts[9] += n
                    counts[10] += n * mem.mem[ZP['wu']]
            elif pc == lab['BackgroundByte']:
                ret = caller()
                if restore_range[0] <= ret < restore_range[1]:
                    counts[8] += 1.0 / mem.mem[ZP['nbytes']]
                elif compose_range[0] <= ret < compose_range[1]:
                    counts[8] += 1.0 / mem.mem[ZP['wu']]
            elif pc == lab['Delay']:
                ret = caller()
                d0 = mpu.processorCycles
                while mpu.pc != ret:
                    mpu.step()
                delay_cycles = mpu.processorCycles - d0
            elif pc == lab['NewLife']:
                new_life = True
            elif pc == lab['MainLoop']:
                break
        if new_life:
            continue
        counts[1] = mem.shown_writes
        rows.append([1] + counts)
        works.append(mpu.processorCycles - start - delay_cycles)
    coef = lstsq(rows, works)
    worst = max(abs(w - sum(c * x for c, x in zip(coef, r))) for r, w in zip(rows, works))
    avg = [sum(r[i + 1] for r in rows) / len(rows) for i in range(len(SITES))]
    print('%d quadros; média de eventos por quadro: %s' % (
        len(rows), ', '.join('%s %.1f' % (s, a) for s, a in zip(SITES, avg))))
    print('ciclos: quadro %.0f; %s  (pior erro de quadro %.0f)' % (
        coef[0], ', '.join('%s %.0f' % (s, c) for s, c in zip(SITES, coef[1:])), worst))
    print('constantes (unidades de 5 ciclos): COST_FRAME + COST_OBJECTS = %d; %s' % (
        round(coef[0] / 5), ', '.join('%s = %d' % (n, max(0, round(c / 5)))
                                      for n, c in zip(CONSTANTS, coef[1:]))))


if __name__ == '__main__':
    main()
