#!/usr/bin/env python3
"""Prévias de som: os efeitos do original (a TIA, como no soundcmp.py do Pole Position: o
TIASound de Ron Fries) e versões para o TK2000 (um alto-falante de 1 bit: uma onda quadrada),
como WAVs em build/.

Os efeitos do original (canal 0, medidos no simulador; volume = sndTime, um por quadro):
  quique  AUDC 2 AUDF 2, volume 2, 1          (uma pancada de ruído, 2 quadros)
  batida  AUDC 2 AUDF 2, volume 3, 2, 1       (3 quadros)
  ponto   AUDC $D AUDF 6 ou 12 (quem o ganhou), volume 13 descendo até 1   (um bipe, 13 quadros)
  game    o mesmo, volume 15 descendo até 1, três vezes (set: seis vezes)

Uso: sndprev.py point
"""
import math
import os
import struct
import sys
import wave

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
TIA, SR, TICK = 31440.0, 44100, 1 / 59.92


def polys():
    def lfsr(bits, taps):
        s, out = (1 << bits) - 1, []
        for _ in range((1 << bits) - 1):
            out.append(s & 1)
            fb = 0
            for t in taps:
                fb ^= s >> t & 1
            s = (s >> 1) | (fb << (bits - 1))
        return out
    return lfsr(4, (0, 1)), lfsr(5, (0, 2))


BIT4, BIT5 = polys()
DIV31 = [1 if i in (0, 13) else 0 for i in range(31)]


def tia(frames):
    """frames: (AUDC, AUDF, AUDV) por quadro -> amostras em SR (-1..1, acoplamento AC)."""
    n = int(len(frames) * TICK * TIA)
    cnt = p4 = p5 = vol = 0
    raw = []
    for i in range(n):
        c, f, v = frames[min(int(i / TIA / TICK), len(frames) - 1)]
        mx = (f + 1) * (3 if c & 0x0C == 0x0C else 1)
        cnt += 1
        if cnt >= mx:
            cnt = 0
            p5 = (p5 + 1) % 31
            if (c & 2) == 0 or (c & 1 == 0 and DIV31[p5]) or (c & 1 and BIT5[p5]):
                if c & 4:
                    vol ^= 1
                else:
                    p4 = (p4 + 1) % 15
                    vol = BIT4[p4]
        raw.append(vol * v / 15)
    return resample(raw, TIA)


def resample(raw, rate):
    out, y, xp = [], 0.0, 0.0
    for j in range(int(len(raw) / rate * SR)):
        x = raw[min(int(j / SR * rate), len(raw) - 1)]
        y = 0.995 * (y + x - xp)
        xp = x
        out.append(y)
    return out


def square(freq, secs, duty=lambda t: 0.5):
    """O alto-falante do TK2000: uma onda quadrada, ciclo de trabalho duty(t)."""
    raw, t, rate = [], 0.0, 1022727 / 8
    for i in range(int(secs * rate)):
        t = i / rate
        ph = (t * freq) % 1
        raw.append(1.0 if ph < duty(t) else 0.0)
    return resample(raw, rate)


def save(name, parts, gap=0.4):
    data = []
    for p in parts:
        data += p + [0.0] * int(gap * SR)
    path = os.path.join(ROOT, 'build', name)
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(struct.pack('<%dh' % len(data), *(int(max(-1, min(1, x * 0.6)) * 32000) for x in data)))
    w.close()
    print(path)


def tone(f):
    """O tom puro da TIA com AUDC $D (div 6) e AUDF f, em Hz."""
    return TIA / ((f + 1) * 3) / 2


if sys.argv[1] == 'point':
    beeps = [[(0xD, f, v) for v in range(13, 0, -1)] + [(0xD, f, 0)] * 2 for f in (6, 12)]
    save('snd-point-2600.wav', [tia(b) for b in beeps])
    secs = 13 * TICK
    save('snd-point-tk-a.wav', [square(tone(f), secs) for f in (6, 12)])
    fade = lambda t: 0.5 * (1 - t / secs) + 0.04   # noqa: E731
    save('snd-point-tk-b.wav', [square(tone(f), secs, fade) for f in (6, 12)])
    print('tons: %.0f Hz, %.0f Hz' % (tone(6), tone(12)))


def thump_edges(vols):
    """A pancada do 2600 (AUDC 2, AUDF 2) como instantes de troca do alto-falante (s): as trocas do
    bit de saída enquanto o volume está ligado (quadros de vols)."""
    edges, cnt, p4, p5, out, prev = [], 0, 0, 0, 0, 0
    n = int(len(vols) * TICK * TIA)
    for i in range(n):
        cnt += 1
        if cnt >= 3:
            cnt = 0
            p5 = (p5 + 1) % 31
            if DIV31[p5]:
                p4 = (p4 + 1) % 15
                out = BIT4[p4]
        if out != prev:
            edges.append(i / TIA)
            prev = out
    return edges


def from_edges(edges, secs, jitter=0.0):
    import random
    rnd = random.Random(1)
    rate = 1022727 / 8
    ts = sorted(t + rnd.uniform(-jitter, jitter) for t in edges)
    raw, lvl, j = [], 0.0, 0
    for i in range(int(secs * rate)):
        t = i / rate
        while j < len(ts) and ts[j] <= t:
            lvl, j = 1.0 - lvl, j + 1
        raw.append(lvl)
    return resample(raw, rate)


if sys.argv[1] == 'thump':
    seq = [('quique', [2, 1]), ('batida', [3, 2, 1])]
    save('snd-thump-2600.wav', [tia([(2, 2, v) for v in vols] + [(2, 2, 0)] * 3) for _, vols in seq] * 3, 0.25)
    secs = 0.12
    edges = {name: thump_edges(vols) for name, vols in seq}
    for name, e in edges.items():
        print(name, len(e), 'trocas:', ' '.join('%.1f' % (t * 1000) for t in e), 'ms')
    save('snd-thump-tk-a.wav', [from_edges(edges[n], secs) for n, _ in seq] * 3, 0.25)
    save('snd-thump-tk-b.wav', [from_edges(edges[n], secs, 0.001) for n, _ in seq] * 3, 0.25)
    click = [0.0, 0.0006, 0.0012, 0.0018]
    save('snd-thump-tk-c.wav', [from_edges(click, secs) for n, _ in seq] * 3, 0.25)
