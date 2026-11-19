#!/usr/bin/env python3
"""A música do título (reference/music.mid: uma melodia, notas de uma semicolcheia) como src/music.inc
para o tocador do src/sfx.s: um passo a cada semicolcheia (136 ms: o andamento do MIDI acelerado
10% frente ao original), 0 = pausa ou o número da nota (1..), e por nota o atraso do meio período
dela e quantos meios períodos ela dura.

    midi2tk.py MIDI OUT.inc [TRANSPOSE]     (TRANSPOSE em semitons: 12 = uma oitava acima)
"""
import struct
import sys

CPU = 1022727                   # ciclos do TK2000 por segundo
SPEED = 1.1                     # o andamento do MIDI 10% mais rápido (passos de 150 ms -> 136 ms)
NOTE_MS = 127                   # de um passo: o resto é silêncio (notas separadas)
LOOP_CYCLES, LOOP_OVERHEAD = 7, 34      # src/sfx.s Music: um meio período = 7 * atraso + 34


def vlq(d, p):
    v = 0
    while True:
        b = d[p]
        p += 1
        v = v << 7 | b & 0x7F
        if b < 0x80:
            return v, p


def notes(path):
    """[(tique inicial, duração, nota MIDI)], tiques por semínima, microssegundos por semínima"""
    d = open(path, 'rb').read()
    assert d[:4] == b'MThd'
    _, ntr, div = struct.unpack('>HHH', d[8:14])
    p, tempo, out = 14, 500000, []
    for _ in range(ntr):
        assert d[p:p + 4] == b'MTrk'
        q, end = p + 8, p + 8 + struct.unpack('>I', d[p + 4:p + 8])[0]
        p, tick, run, on = end, 0, None, {}
        while q < end:
            dt, q = vlq(d, q)
            tick += dt
            if d[q] == 0xFF:
                typ = d[q + 1]
                n, q = vlq(d, q + 2)
                if typ == 0x51:
                    tempo = int.from_bytes(d[q:q + n], 'big')
                q += n
                continue
            if d[q] in (0xF0, 0xF7):
                n, q = vlq(d, q + 1)
                q += n
                continue
            if d[q] & 0x80:
                run = d[q]
                q += 1
            hi = run & 0xF0
            n = 1 if hi in (0xC0, 0xD0) else 2
            a = d[q:q + n]
            q += n
            if hi == 0x90 and a[1]:
                on[a[0]] = tick
            elif hi in (0x80, 0x90) and a[0] in on:
                out.append((on[a[0]], tick - on.pop(a[0]), a[0]))
    return sorted(out), div, tempo


def main():
    src, dst = sys.argv[1:3]
    transpose = int(sys.argv[3]) if len(sys.argv) > 3 else 0
    ns, div, tempo = notes(src)
    step = div // 4                                     # uma semicolcheia
    assert all(t % step == 0 and n <= step for t, n, _ in ns), 'não é uma nota por semicolcheia'
    assert all(ns[i][0] < ns[i + 1][0] for i in range(len(ns) - 1)), 'não é uma melodia só'
    total = (ns[-1][0] + ns[-1][1] + step - 1) // step
    pitches = sorted({m + transpose for _, _, m in ns})
    steps = [0] * total
    for t, _, m in ns:
        steps[t // step] = pitches.index(m + transpose) + 1
    step_ms = tempo / 4 / 1000 / SPEED
    with open(dst, 'w') as o:
        o.write('; gerado por tools/midi2tk.py a partir de %s (transposto %+d)\n' % (src.split('/')[-1], transpose))
        o.write('MUSIC_STEP_MS = %d\nMUSIC_NOTE_MS = %d\nMUSIC_STEPS = %d\n' % (round(step_ms), NOTE_MS, total))
        delays, halves = [], []
        for m in pitches:
            f = 440 * 2 ** ((m - 69) / 12)
            half = CPU / 2 / f
            delays.append(round((half - LOOP_OVERHEAD) / LOOP_CYCLES))
            halves.append(round(NOTE_MS / 1000 * 2 * f))
            assert 1 <= delays[-1] <= 255
        o.write('MusicDelay:   .byte %s\n' % ', '.join(map(str, delays)))
        o.write('MusicHalvesLo: .byte %s\n' % ', '.join('<%d' % h for h in halves))
        o.write('MusicHalvesHi: .byte %s\n' % ', '.join('>%d' % h for h in halves))
        o.write('MusicSteps:\n')
        for i in range(0, total, 16):
            o.write('        .byte   %s\n' % ', '.join(str(s) for s in steps[i:i + 16]))
    print('%d notas, %d passos de %.0f ms (%.1f s), alturas %s' % (
        len(ns), total, step_ms, total * step_ms / 1000, pitches))


if __name__ == '__main__':
    main()
