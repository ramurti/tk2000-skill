#!/usr/bin/env python3
"""Um AY-3-8910 simples para ouvir os registros do sfmb.py: tons, ruído, mixer, volume e envelope.

    ay.py build/mb/NOME.pkl SAIDA.wav [-a SEG] [-b SEG] [-c 0|1] [-v A,B,C]

-a/-b: trecho (segundos); -c: só um dos dois AY (sem -c: AY 0 à esquerda, AY 1 à direita);
-v: só essas vozes (A,B,C). Também: regs(log, chip) -> a sequência dos estados (para tirar notas).
"""
import pickle, sys, wave

CLK = 1020484                          # o AY da Mockingboard anda no relógio do Apple
VOL = [0, 0.0137, 0.0205, 0.0291, 0.0423, 0.0618, 0.0847, 0.1369, 0.1691, 0.2647, 0.3527, 0.4499,
       0.5704, 0.6873, 0.8482, 1.0]


class AY:
    def __init__(self):
        self.r = [0] * 16
        self.ph = [0.0, 0.0, 0.0]
        self.out = [0, 0, 0]
        self.nph, self.lfsr, self.nout = 0.0, 1, 0
        self.eph, self.estep, self.ehold, self.edir = 0.0, 0, False, 1

    def set(self, reg, v):
        if reg < 0:
            self.__init__(); return
        self.r[reg] = v
        if reg == 13:
            self.estep, self.ehold, self.eph = 0, False, 0.0
            self.edir = 1 if v & 4 else -1

    def env(self):
        v = self.estep if self.edir > 0 else 15 - self.estep
        return v & 15

    def sample(self, dt, voices=(0, 1, 2)):
        """avança dt ciclos do relógio e devolve a saída (0..3)"""
        r = self.r
        for ch in range(3):
            tp = (r[ch * 2] | (r[ch * 2 + 1] & 15) << 8) or 1
            self.ph[ch] += dt / (8 * tp)        # meio período = 8 * TP ciclos
            while self.ph[ch] >= 1:
                self.ph[ch] -= 1
                self.out[ch] ^= 1
        npd = (r[6] & 31) or 1
        self.nph += dt / (16 * npd)
        while self.nph >= 1:
            self.nph -= 1
            bit = (self.lfsr ^ (self.lfsr >> 3)) & 1
            self.lfsr = (self.lfsr >> 1) | (bit << 16)
            self.nout = self.lfsr & 1
        ep = (r[11] | r[12] << 8) or 1
        if not self.ehold:
            self.eph += dt / (16 * ep)
            while self.eph >= 1 and not self.ehold:
                self.eph -= 1
                self.estep += 1
                if self.estep > 15:
                    sh = r[13]
                    if not sh & 8 or sh & 1:    # para
                        self.ehold = True
                        if not sh & 8:
                            self.estep, self.edir = 15, -1   # fica em 0
                        elif (sh & 2):
                            self.edir = -self.edir; self.estep = 15
                        else:
                            self.estep = 15
                    else:
                        self.estep = 0
                        if sh & 2:
                            self.edir = -self.edir
        mix = r[7]
        s = 0.0
        for ch in voices:
            ton = (mix >> ch) & 1 or self.out[ch]
            noi = (mix >> (ch + 3)) & 1 or self.nout
            if ton and noi:
                a = r[8 + ch]
                s += VOL[self.env() if a & 16 else a & 15]
        return s


def render(log, a, b, path, chips=(0, 1), voices=(0, 1, 2), rate=44100, hz=CLK):
    ays = [AY(), AY()]
    k = 0
    frames = bytearray()
    dt = hz / rate
    t = 0.0
    n = int((b - a) * rate)
    c0 = a * hz
    while k < len(log) and log[k][0] < c0:          # o estado até o começo do trecho
        _, ch, reg, v = log[k]; ays[ch].set(reg, v); k += 1
    for s in range(n):
        c = c0 + s * dt
        while k < len(log) and log[k][0] <= c:
            _, ch, reg, v = log[k]; ays[ch].set(reg, v); k += 1
        L = ays[0].sample(dt, voices) if 0 in chips else 0
        R = ays[1].sample(dt, voices) if 1 in chips else 0
        if len(chips) == 1:
            L = R = L + R
        frames += int(L / 3 * 20000).to_bytes(2, 'little', signed=True)
        frames += int(R / 3 * 20000).to_bytes(2, 'little', signed=True)
    w = wave.open(path, 'wb'); w.setnchannels(2); w.setsampwidth(2); w.setframerate(rate)
    w.writeframes(bytes(frames)); w.close()


def main():
    a = sys.argv[1:]
    d = pickle.load(open(a[0], 'rb'))
    log = d['ay']
    t0 = float(a[a.index('-a') + 1]) if '-a' in a else 0
    t1 = float(a[a.index('-b') + 1]) if '-b' in a else log[-1][0] / d['hz'] + 1
    chips = (int(a[a.index('-c') + 1]),) if '-c' in a else (0, 1)
    voices = tuple('ABC'.index(x) for x in a[a.index('-v') + 1].split(',')) if '-v' in a else (0, 1, 2)
    render(log, t0, t1, a[1], chips, voices, hz=d['hz'])
    print(a[1], '%.1f-%.1f s' % (t0, t1))


if __name__ == '__main__':
    main()
