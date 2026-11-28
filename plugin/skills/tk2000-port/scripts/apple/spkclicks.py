#!/usr/bin/env python3
"""Os cliques do alto-falante ($C030) do original, a partir de um estado do AppleWin: cada acesso com o
ciclo e o PC. Grava build/spk/NOME.pkl ([(ciclo relativo, pc)]), build/spk/NOME.wav (o som: o cone troca
de lado a cada acesso, 44,1 kHz) e mostra um resumo: por PC, quantos cliques e entre que segundos.

    spkclicks.py SNAP.yaml CICLOS NOME [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA] [-p ADDR=VAL]
"""
import os, pickle, sys, wave
from collections import defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import sfboot, dispkg
from sftaint import Ap
from a2boot import Mem
from py65.devices.mpu6502 import MPU

HZ = 1020484
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class Spk(Ap):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.clicks = []

    def io(self, addr):
        if addr & 0xFF == 0x30:
            self.clicks.append((self.mpu.processorCycles, self.mpu.pc))
        return super().io(addr)


def wav(clicks, n_cycles, path, rate=44100, amp=9000):
    """o cone em +amp/-amp, trocando a cada clique; média por amostra (filtro simples)"""
    n = int(n_cycles * rate / HZ) + 1
    out = bytearray()
    level, k = 1, 0
    for s in range(n):
        c0, c1 = s * HZ / rate, (s + 1) * HZ / rate
        acc, t = 0.0, c0
        while k < len(clicks) and clicks[k] < c1:
            acc += level * (clicks[k] - t)
            t = clicks[k]
            level = -level
            k += 1
        acc += level * (c1 - t)
        v = int(amp * acc / (c1 - c0))
        out += v.to_bytes(2, 'little', signed=True)
    w = wave.open(path, 'wb')
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(bytes(out)); w.close()


def main():
    a = sys.argv[1:]
    dsk = open(dispkg.DSK, 'rb').read()
    ao = Spk(dsk)
    m = MPU(memory=Mem(ao), pc=0)
    m.cycletime = list(m.cycletime); m.cycletime[0xCE] = 6
    ao.mpu = m; ao.fire_from = 1 << 62; ao.disk_cycles = 32
    sfboot.load_applewin(ao, a[0])
    t0 = m.processorCycles
    end = t0 + int(a[1])
    name = a[2]
    ev = []
    i = 3
    while i < len(a):
        if a[i] == '-p':
            x, _, v = a[i + 1].partition('=')
            ao.ram[int(x, 16)] = int(v, 16)
            i += 2; continue
        t, _, v = a[i + 1].partition(':')
        ev.append((t0 + int(float(t) * HZ), a[i], v)); i += 2
    ev.sort()
    while m.processorCycles < end:
        while ev and m.processorCycles >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ao.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ao.joy['xy'.index(k)] = int(n)
                    else: ao.btn[int(k[1])] = n != '0'
        m.step()
    clicks = [(c - t0, pc) for c, pc in ao.clicks]
    d = os.path.join(ROOT, 'build', 'spk')
    os.makedirs(d, exist_ok=True)
    pickle.dump(clicks, open(os.path.join(d, name + '.pkl'), 'wb'))
    wav([c for c, _ in clicks], end - t0, os.path.join(d, name + '.wav'))
    by = defaultdict(list)
    for c, pc in clicks:
        by[pc].append(c / HZ)
    print('%d cliques em %.1f s -> build/spk/%s.wav' % (len(clicks), (end - t0) / HZ, name))
    for pc, ts in sorted(by.items(), key=lambda kv: kv[1][0]):
        # trechos: cliques separados por menos de 0,2 s
        segs, s0, last = [], ts[0], ts[0]
        for t in ts[1:]:
            if t - last > 0.2:
                segs.append((s0, last)); s0 = t
            last = t
        segs.append((s0, last))
        print('  $%04X %6d cliques, %3d trechos: %s' % (pc, len(ts), len(segs),
              ' '.join('%.1f-%.1f' % s for s in segs[:12]) + (' ...' if len(segs) > 12 else '')))


if __name__ == '__main__':
    main()
