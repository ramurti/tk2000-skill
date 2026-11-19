#!/usr/bin/env python3
"""Os checkpoints do som (SND, src/sound.s): roda o programa inteiro no py65 (a pilotagem de
tools/sndprev.py), mede o tempo de CPU antes de cada checkpoint desde o anterior (deixando de
fora os ciclos das próprias rotinas de som: SndBorrow já soma esse tempo até a próxima troca), e
imprime, por checkpoint, a média e a dispersão, e os maiores intervalos; --write grava as médias
(em unidades de 8 ciclos) em src/sndk.inc (depois make, e de novo: os tempos mudam um pouco o
código). Também registra o alto-falante (SndTog) e grava build/engine-tk.wav, e o canal 0 do
original para a mesma pilotagem como build/engine-2600.wav (tools/sndprev.py), com as trocas por
segundo de cada um.
Os checkpoints são achados na listagem (build/main.lst: linhas "SND nome", em CODE em $4000).

Uso: sndfit.py [tiques] [--write] [--snow] [--beep] [--tunes]   (--snow: a neve a partir do tique
     250, o ruído também; --beep: o fim do dia a partir do tique 250, os bipes a partir de ~376;
     --tunes: um carro restante a partir do tique 250, a vinheta; a partir do tique 500 o fim do
     dia com carros restantes, o fim de jogo)
"""
import collections
import os
import re
import sys

from py65.devices.mpu6502 import MPU

sys.path.insert(0, os.path.dirname(__file__))
import lockstep as L  # noqa: E402
import sndprev as S  # noqa: E402


def sites():
    out = {}
    for line in open('build/main.lst'):
        m = re.match(r'([0-9A-F]{6})r\s+\d+\s+(?:[0-9A-Fr]{2}\s+)*\s*(?:[@\w]*:\s*)?SND\s+(\w+)\s*(?:;.*)?$',
                     line)
        if m:
            out[0x4000 + int(m.group(1), 16)] = m.group(2)
    return out


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    n = int(args[0]) if args else 1800
    lab = L.labels()
    site = sites()
    names = set(re.findall(r'^SNDK_(\w+)', open('src/sndk.inc').read(), re.M))
    if names != set(site.values()):
        sys.exit('checkpoints: em sndk.inc %s, na listagem %s' % (sorted(names - set(site.values())),
                                                                    sorted(set(site.values()) - names)))
    lo, hi = lab['SndBorrow'], lab['SndRegs']
    mem = bytearray(0x10000)
    prog = open('build/enduro.bin', 'rb').read()
    mem[0x4000:0x4000 + len(prog)] = prog
    t = MPU(memory=mem, pc=0x4000)
    gaps = collections.defaultdict(list)
    worst = []
    tog, regs, ends = [], [], []
    last = None
    snd = 0
    ksum = sndall = 0
    kval = {m.group(1): int(m.group(2)) for m in re.finditer(r'^SNDK_(\w+)\s*=\s*(\d+)', open('src/sndk.inc').read(), re.M)}
    f = 0
    while f < n:
        pc = t.pc
        if pc == lab['ReadKeys']:
            s, b, fi = S.drive(f + 1)
            mem[0x280], mem[0x282], mem[0x3C] = s, b, 0 if fi else 0x80
            r = mem[0x100 + ((t.sp + 1) & 0xFF)] | mem[0x100 + ((t.sp + 2) & 0xFF)] << 8
            t.sp = (t.sp + 2) & 0xFF
            t.pc = r + 1
            continue
        cy = t.processorCycles
        if pc in site:
            ksum += kval.get(site[pc], 0) * 8
            if last is not None and f > 100:
                g = cy - last - snd
                gaps[site[pc]].append(g)
                worst.append((g, site[pc], f))
            last, snd = cy, 0
        if pc == lab['TkFrame']:
            regs.append(tuple(mem[0x15:0x1B]))
            ends.append(cy)
        if pc in (lab['SndTog'], lab['SndTog1'], lab['SndTog2'], lab['SndTog3'], lab['SndTog4']):
            tog.append(cy / S.CPU)
        t.step()
        if lo <= pc < hi:
            snd += t.processorCycles - cy
            sndall += t.processorCycles - cy
        if pc == L.MAINLOOP:
            f += 1
            if f == 250 and '--snow' in sys.argv:
                mem[0xB1] = 0xB0
            if f == 250 and '--beep' in sys.argv:
                mem[0xB1] = 0xC8
            if f == 250 and '--tunes' in sys.argv:          # um carro restante, depois o fim do dia
                mem[0xAB], mem[0xAC] = 1, 0
            if f == 500 and '--tunes' in sys.argv:
                mem[0xAB], mem[0xAC], mem[0xB1] = 1, 0, 0xC1
    allg = sorted(g for v in gaps.values() for g in v)
    print('%d checkpoints; intervalos: mediana %d, 90%% %d, 99%% %d, máx %d ciclos' % (
        len(allg), allg[len(allg) // 2], allg[len(allg) * 9 // 10], allg[len(allg) * 99 // 100], allg[-1]))
    k = {}
    for name in sorted(gaps, key=lambda x: -sum(gaps[x])):
        v = sorted(gaps[name])
        mean = sum(v) / len(v)
        k[name] = max(1, min(255, round(mean / 8)))
        print('  %-10s %6d vezes, média %5.0f, 10%%-90%% %5d-%5d' % (name, len(v), mean, v[len(v) // 10],
                                                                 v[len(v) * 9 // 10]))
    worst.sort(reverse=True)
    print('maiores:', ', '.join('%d antes de %s' % (g, s) for g, s, _ in worst[:8]))
    for name in names - set(k):
        k[name] = 50
    if '--write' in sys.argv:
        with open('src/sndk.inc', 'w') as fo:
            fo.write('; gerado por tools/sndfit.py: por checkpoint, o tempo médio desde o '
                     'anterior (unidades de 8 ciclos)\n')
            for name in sorted(k):
                fo.write('SNDK_%-12s = %d\n' % (name, k[name]))
    length = ends[-1] / S.CPU
    S.write('build/engine-tk.wav', S.speaker(tog, length), 0, length)
    S.write('build/engine-2600.wav', S.tia(regs, 0), 0, len(regs) * S.TICK)
    def ch0(r):                         # o canal 0 como tocado: o motor, os freios, o estrondo da batida
        return r[4] & 15 and (r[0] & 15 == 3 and r[2] & 31 >= 8 or r[0] & 15 == 8 and 8 <= r[2] & 31 <= 10)
    ref = S.tia([r if ch0(r) else (0,) * 6 for r in regs], 0)
    ch = sum(1 for i in range(1, len(ref)) if (ref[i] > 0) != (ref[i - 1] > 0))
    b9 = S.BIT9
    per9 = sum(b9[i] != b9[i - 1] for i in range(511)) / 511   # as trocas do ruído por pulso de relógio
    print('tempo: %d ciclos, os checkpoints contaram %d, o som levou %d' % (t.processorCycles, ksum, sndall))
    cat = collections.defaultdict(lambda: [0, 0.0])     # pelo que toca: trocas, devidas na
    j = 0                                               # linha do tempo do próprio TK2000
    for k in range(len(ends) - 1):
        r, dt = regs[k], (ends[k + 1] - ends[k]) / S.CPU * S.TIA
        e = r[4] & 15 and r[0] & 15 == 3 and r[2] & 31 >= 8
        b = r[4] & 15 and r[0] & 15 == 8 and 8 <= r[2] & 31 <= 10
        n = r[5] & 15 and r[1] & 15 == 8
        o = r[5] & 15 == 6 and r[1] & 15 == 3           # o outro carro mais próximo
        beep = r[5] & 15 and r[1] & 15 == 4             # o bipe: sozinho, uma troca por pulso de relógio
        jin = r[5] & 15 and r[1] & 15 == 12             # a vinheta: uma troca a cada 3 pulsos de relógio
        over = r[5] & 15 and r[1] & 15 == 7             # o fim de jogo: 16 trocas em 31 pulsos de relógio
        if beep:
            e = b = n = o = False
        due = (e and dt / ((r[2] & 31) + 1) * 128 / 465) + (b and dt / ((r[2] & 31) + 1) * per9) + \
            (n and dt / ((r[3] & 31) + 1) / 2 * per9) + (o and dt / ((r[3] & 31) + 1) * 128 / 465) + \
            (beep and dt / ((r[3] & 31) + 1)) + (jin and dt / ((r[3] & 31) + 1) / 3) + \
            (over and dt / ((r[3] & 31) + 1) * 16 / 31)
        name = 'motor' if e else ('freios' if r[2] & 31 == 10 else 'batida') if b else 'silêncio'
        c = cat['bipe' if beep else 'vinheta' if jin else 'fim de jogo' if over else
                name + ('+neve' if n else '+outro' if o else '')]
        while j < len(tog) and tog[j] * S.CPU < ends[k + 1]:
            if tog[j] * S.CPU >= ends[k]:
                c[0] += 1
            j += 1
        c[1] += due
    exp = sum(v[1] for v in cat.values())
    print('alto-falante: %d trocas, %.0f devidas na sua linha do tempo (%.1f%%)' % (len(tog), exp,
                                                                      100 * (len(tog) / exp - 1)))
    print('  ' + ', '.join('%s %d/%.0f (%+.1f%%)' % (x, v[0], v[1], 100 * (v[0] / v[1] - 1) if v[1] else 0)
                           for x, v in sorted(cat.items())))
    print('%.1f s: alto-falante %.0f trocas/s; o original (canal 0 como tocado) %.0f/s' % (
        length, len(tog) / length, ch / (len(regs) * S.TICK)))


if __name__ == '__main__':
    main()
