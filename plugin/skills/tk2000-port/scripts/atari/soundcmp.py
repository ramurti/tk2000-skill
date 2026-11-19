#!/usr/bin/env python3
"""O som comparado com o do original: roda o programa inteiro no py65 a partir de Start (teclas
simuladas como em engfit.py), registra os registradores de som do original depois de cada tique
(página zero $15-$1A, as escritas dele na TIA) e as trocas do alto-falante. Grava dois WAVs da
mesma pilotagem (22.050 Hz):
  build/snd-2600.wav  a TIA (o TIASound de Ron Fries: os dois canais, AUDC/AUDF/AUDV) tocando os
                      registradores registrados nos 59,92 tiques/s do 2600
  build/snd-tk.wav    o alto-falante do programa
e um trecho de cada efeito na primeira vez em que aparece (build/snd-<efeito>-2600.wav, -tk.wav).
    .venv/bin/python tools/reference/soundcmp.py [segundos]"""
import os
import struct
import sys
import wave
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..')
sys.path.insert(0, HERE)
import engfit  # noqa: E402
from tkcheck import TK  # noqa: E402

CPU, TIA, SR, TICK = engfit.CPU, 31440.0, 22050, 1 / 59.92
OUT = os.path.join(ROOT, 'build')


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
    return lfsr(4, (0, 1)), lfsr(5, (0, 2)), lfsr(9, (0, 4))


BIT4, BIT5, BIT9 = polys()
DIV31 = [1 if i in (0, 13) else 0 for i in range(31)]


def tia(regs, length):
    """regs: por tique (AUDC0, AUDC1, AUDF0, AUDF1, AUDV0, AUDV1) -> amostras na taxa da TIA (0..30)."""
    n = int(length * TIA)
    out = [0] * n
    cnt, p4, p5, p9, vol = [0, 0], [0, 0], [0, 0], [0, 0], [0, 0]
    for i in range(n):
        k = min(int(i / TIA / TICK), len(regs) - 1)
        r = regs[k]
        s = 0
        for ch in (0, 1):
            c, f, v = r[ch] & 15, r[2 + ch] & 31, r[4 + ch] & 15
            mx = (f + 1) * (3 if c & 0x0C == 0x0C else 1)
            cnt[ch] += 1
            if cnt[ch] >= mx:
                cnt[ch] = 0
                p5[ch] = (p5[ch] + 1) % 31
                if (c & 2) == 0 or (c & 1 == 0 and DIV31[p5[ch]]) or (c & 1 and BIT5[p5[ch]]):
                    if c & 4:
                        vol[ch] = 0 if vol[ch] else 1
                    elif c & 8:
                        if c == 8:
                            p9[ch] = (p9[ch] + 1) % 511
                            vol[ch] = BIT9[p9[ch]]
                        else:
                            vol[ch] = BIT5[p5[ch]]
                    else:
                        p4[ch] = (p4[ch] + 1) % 15
                        vol[ch] = BIT4[p4[ch]]
            if c not in (0, 0x0B):
                s += vol[ch] * v
        out[i] = s
    return out


def write(path, samples, rate, t0, t1, scale):
    """amostras na taxa rate, o trecho de t0..t1 s, como um WAV de 16 bits em SR (acoplamento AC)."""
    res, y, xp = [], 0.0, 0.0
    for j in range(int(t0 * SR), int(t1 * SR)):
        i = int(j / SR * rate)
        x = samples[i] * scale if 0 <= i < len(samples) else 0.0
        y = 0.995 * (y + x - xp)
        xp = x
        res.append(int(max(-1, min(1, y * 0.5)) * 32000))
    w = wave.open(path, 'wb')
    w.setnchannels(1)
    w.setsampwidth(2)
    w.setframerate(SR)
    w.writeframes(struct.pack('<%dh' % len(res), *res))
    w.close()


def speaker(toggles, length, rate=TIA):
    n, out, lvl, j = int(length * rate), [], -1, 0
    for i in range(n):
        t = i / rate
        while j < len(toggles) and toggles[j] <= t:
            lvl, j = -lvl, j + 1
        out.append(lvl)
    return out


def effects(regs, start):
    """efeito -> primeiro tique, duração em tiques."""
    found = {}

    def first(name, cond, after=start, length=150):
        for k in range(after, len(regs)):
            if cond(regs[k]):
                found[name] = (k, length)
                return
    first('start', lambda r: r[4] & 15 and r[0] & 15 == 4, start - 5, 250)
    first('passing', lambda r: r[5] & 15 and r[1] & 15 == 3)
    first('skid', lambda r: r[4] & 15 and r[0] & 15 == 4, start + 260)
    first('extended', lambda r: r[5] & 15 and r[1] & 15 == 13, start + 260, 200)
    first('crash', lambda r: r[4] & 15 and r[0] & 15 == 8, start, 200)
    return found


def main():
    secs = float(sys.argv[1]) if len(sys.argv) > 1 else 100
    tk = TK()
    tk.mem.cx = None
    keys = engfit.Keys(tk.mem)
    m = tk.mpu
    keys.mpu = m
    lab = tk.lab
    m.pc = lab['Start']
    GEAR, te = tk.lab_orig('GEAR'), lab['TkTickEnd']
    regs, times, start = [], [], None
    keys.down = {'space'}
    while m.processorCycles < secs * CPU:
        if m.pc == te:
            regs.append(tuple(tk.mem[a] for a in (0x15, 0x16, 0x17, 0x18, 0x19, 0x1A)))
            times.append(m.processorCycles / CPU)
            if start is None and not tk.mem[GEAR] & 0x20:
                start = len(regs) - 1
            if start is not None and tk.mem[0x55] > 2:
                per = tk.mem[0x8A] - 256 if tk.mem[0x8A] >= 128 else tk.mem[0x8A]
                keys.down = {'down'} | ({'left'} if per > 8 else {'right'} if per < -8 else set())
        m.step()
    tg = [c / CPU for c in keys.toggles]
    length = len(regs) * TICK
    ref = tia(regs, length)
    spk = speaker(tg, secs)
    write(os.path.join(OUT, 'snd-2600.wav'), ref, TIA, 0, length, 1 / 30)
    write(os.path.join(OUT, 'snd-tk.wav'), spk, TIA, times[0], secs, 1)
    print('%d tiques (%.1f s), %d trocas' % (len(regs), length, len(tg)))
    for name, (k, n) in effects(regs, start).items():
        t2600, ttk = k * TICK, times[k] - times[0]
        write(os.path.join(OUT, 'snd-%s-2600.wav' % name), ref, TIA, max(0, t2600 - 0.3),
              t2600 + n * TICK + 0.3, 1 / 30)
        write(os.path.join(OUT, 'snd-%s-tk.wav' % name), spk, TIA, max(0, times[k] - 0.3),
              times[k] + n * TICK + 0.5, 1)
        print('  %-9s tique %5d: 2600 %.1f s, TK2000 %.1f s' % (name, k, t2600, ttk))


if __name__ == '__main__':
    main()
