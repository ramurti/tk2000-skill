#!/usr/bin/env python3
"""Registra o que o kernel original desenha, linha a linha: PF1, PF2 e GRP1 (objeto inimigo) mais
o ciclo de cada RESP1 (posição horizontal), para um quadro do original rodando no py65.

Tempo das linhas: 76 ciclos de CPU por linha de varredura; WSYNC (que para a CPU do 2600 até o
fim da linha) leva o contador de ciclos para o começo da linha seguinte. Linha 0 = primeira linha
depois do VBLANK.

Usado como módulo: frame_lines(atari) -> lista de 160 dicts {PF1, PF2, GRP1, RESP1}
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import atari as atari_mod  # noqa: E402

REGS = {0x0E: 'PF1', 0x0F: 'PF2', 0x1C: 'GRP1', 0x11: 'RESP1', 0x1B: 'GRP0', 0x08: 'COLUPF', 0x07: 'COLUP1'}


def frame_lines(machine):
    """Roda um quadro e devolve as 160 linhas do kernel."""
    writes = []
    state = {'start': None}
    mpu = machine.mpu
    original = atari_mod.Memory.__setitem__

    def spy(self, addr, value):
        a = addr & 0x1FFF
        if not a & 0x1000 and not a & 0x80:
            reg = a & 0x3F
            if reg == 0x02:                                     # WSYNC: espera a próxima linha
                mpu.processorCycles += (-mpu.processorCycles) % 76
            elif reg == 0x01 and value & 0x02 == 0 and state['start'] is None:
                state['start'] = mpu.processorCycles + (-mpu.processorCycles) % 76
            elif reg in REGS:
                writes.append((mpu.processorCycles, REGS[reg], value))
        original(self, addr, value)

    atari_mod.Memory.__setitem__ = spy
    try:
        mpu.processorCycles += (-mpu.processorCycles) % 76
        machine.frame()
    finally:
        atari_mod.Memory.__setitem__ = original
    lines = [dict() for _ in range(160)]
    current = {'PF1': 0, 'PF2': 0, 'GRP1': 0, 'COLUPF': 0, 'COLUP1': 0}
    start = state['start']
    for cycles, reg, value in sorted(writes):
        line = (cycles - start) // 76 if start is not None else -1
        if reg == 'RESP1':
            if 0 <= line < 160:
                lines[line]['RESP1'] = (cycles - start) % 76
            continue
        current[reg] = value
        if 0 <= line < 160:
            lines[line][reg] = value
    # leva os valores dos registradores para as linhas seguintes (os registradores mantêm o valor)
    value = {'PF1': None, 'PF2': None, 'GRP1': None, 'COLUPF': None, 'COLUP1': None}
    for d in lines:
        for k in value:
            if k in d:
                value[k] = d[k]
            elif value[k] is not None:
                d[k] = value[k]
    return lines


if __name__ == '__main__':
    m = atari_mod.Atari()
    m.start_game()
    for f in range(int(sys.argv[1]) if len(sys.argv) > 1 else 400):
        m.swcha = 0xEF if m.zp(0xC6) == 48 else 0xFF
        m.frame()
    print('blockOffset', m.zp(0x8B), 'shapes', [m.zp(0xA0 + i) for i in range(6)])
    for n, d in enumerate(frame_lines(m)):
        print(n, ' '.join('%s=%s' % (k, ('%02X' % d[k]) if k != 'RESP1' else d[k]) for k in sorted(d)))
