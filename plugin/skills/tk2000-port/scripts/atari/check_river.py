#!/usr/bin/env python3
"""Compara o porte para o TK2000 do gerador de blocos com o código original do 2600.

A ROM original roda no py65 (veja atari.py) e cada bloco novo é registrado: a página zero antes e
depois do gerador, mais a posição x do objeto. Depois o NewBlock do porte (build/river.bin) roda a
partir da mesma página zero e os resultados são comparados campo a campo.

Uso: check_river.py [quadros]
"""
import os
import sys
from py65.devices.mpu6502 import MPU

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from atari import Atari  # noqa: E402

ROOT = os.path.join(HERE, '..', '..')

FIELDS = {
    'prevPF1PatId': [0x88], 'PF_State': [0x89], 'sectionEnd': [0x8A], 'blockOffset': [0x8B],
    'blockLst': range(0x8E, 0x94), 'XPos1Lst(shifted)': range(0x94, 0x99),
    'State1Lst(shifted)': range(0x9A, 0x9F), 'Shape1IdLst': range(0xA0, 0xA6),
    'PF1Lst': range(0xA6, 0xAC), 'PF2Lst': range(0xAC, 0xB2), 'blockPart': [0xB6],
    'sectionBlock': [0xB9], 'PF1PatId': [0xBC], 'level': [0xBD], 'randomSave': [0xBE, 0xBF],
    'random': [0xE9, 0xEA], 'randomSave2': [0xEB, 0xEC], 'valleyWidth': [0xEE],
}


def record_original(frames):
    atari = Atari()
    events, current = [], {}

    def pre(m):
        current['pre'] = bytes(m.ram)

    def at_end_shape(m):
        current['x'] = m.mpu.a

    def post(m):
        if 'pre' in current:
            events.append((current.pop('pre'), bytes(m.ram), current.pop('x')))

    atari.hooks[0xF879] = pre                           # "é hora de criar um bloco novo"
    atari.hooks[atari.syms['2.endNewShape']] = at_end_shape
    atari.hooks[atari.syms['2.loopNext']] = post
    atari.start_game()
    for f in range(frames):
        if atari.zp(0xC6) == 48:                        # esperando depois da introdução: decola
            atari.swcha = 0xEF
        else:                                           # varia a velocidade: acelera, neutro, freia
            atari.swcha = (0xEF, 0xFF, 0xDF, 0xFF)[(f // 300) % 4]
        atari.frame()
    return events


def load_labels():
    labels = {}
    for line in open(os.path.join(ROOT, 'build', 'river.lbl')):
        _, addr, name = line.split()
        labels[name.lstrip('.')] = int(addr, 16)
    return labels


def run_port(binary, labels, zp):
    mem = bytearray(0x10000)
    mem[0x4000:0x4000 + len(binary)] = binary
    low = open(os.path.join(ROOT, 'build', 'river_low.bin'), 'rb').read()
    mem[0x0800:0x0800 + len(low)] = low
    mem[0x80:0x100] = zp[0:0x80]                       # variáveis originais em $80-$FF
    call = labels['NewBlock']
    mem[0x0300:0x0303] = bytes([0x20, call & 0xFF, call >> 8])  # JSR NewBlock
    mpu = MPU(memory=mem, pc=0x0300)
    mpu.sp = 0xFF
    for _ in range(100000):
        mpu.step()
        if mpu.pc == 0x0303:
            return mem
    raise RuntimeError('NewBlock não retornou')


def main():
    frames = int(sys.argv[1]) if len(sys.argv) > 1 else 6000
    events = record_original(frames)
    binary = open(os.path.join(ROOT, 'build', 'river.bin'), 'rb').read()
    labels = load_labels()
    errors = 0
    levels, islands, roads = set(), 0, 0
    for n, (pre, post, x) in enumerate(events):
        mem = run_port(binary, labels, pre)
        got = lambda a: mem[a]
        want = lambda a: post[a & 0x7F]
        diffs = []
        for name, addrs in FIELDS.items():
            if [got(a) for a in addrs] != [want(a) for a in addrs]:
                diffs.append('%s port=%s 2600=%s' % (name, [hex(got(a)) for a in addrs],
                                                      [hex(want(a)) for a in addrs]))
        if got(0x9F) != (want(0x9F) & 0x0F):           # State1LstEnd sem os bits finos da TIA
            diffs.append('State1LstEnd port=%02X 2600=%02X' % (got(0x9F), want(0x9F)))
        if got(0x99) != x:
            diffs.append('XPos1LstEnd port=%d 2600=%d' % (got(0x99), x))
        levels.add(want(0xBD))
        islands += bool(want(0x89) & 0x80)
        roads += bool(want(0x93) & 0x80)
        if diffs:
            errors += 1
            if errors <= 10:
                print('bloco %d: %s' % (n, '; '.join(diffs)))
    print('%d blocos comparados (níveis %s, %d com ilha, %d com estrada): %d diferenças'
          % (len(events), sorted(levels), islands, roads, errors))
    sys.exit(1 if errors else 0)


if __name__ == '__main__':
    main()
