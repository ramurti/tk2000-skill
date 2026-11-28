#!/usr/bin/env python3
"""O Sky Fox com uma Mockingboard (slot 4) no Apple do py65: dá boot no disco (o disco girando no tempo
real) e registra cada escrita nos registradores dos dois AY-3-8910 (a música e os efeitos da placa).

    sfmb.py SEGUNDOS NOME [-k SEG:TECLA] [-j SEG:x=..,y=..,b0=..] [-s CADA_SEG] [-S SEG]

Grava build/mb/NOME.pkl: {'ay': [(ciclo, chip, reg, valor)], 'clicks': [(ciclo, pc)] do alto-falante, 'hz'} e, com -s, as
telas em build/mb/NOME-TTT.png. -S SEG: salva a máquina (pickle) em build/mb/NOME-SEG.pkl.state.

A placa (Mockingboard C): 6522 em $C400 (AY 0) e $C480 (AY 1); ORB bits 0-2 = BC1, BDIR, /RESET
(4 parado, 7 escolhe o registrador = ORA, 6 escreve ORA no registrador); o temporizador 1 gera a
interrupção (contínuo com ACR bit 6).
"""
import os, pickle, sys
sys.path.insert(0, os.path.dirname(__file__))
import sfboot, dispkg
from a2boot import Mem, P2D, WRITE_TABLE
from sftaint import Ap
from py65.devices.mpu6502 import MPU

HZ = 1020484
ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')


class Via:
    def __init__(self, mb, chip):
        self.mb, self.chip = mb, chip
        self.r = [0] * 16
        self.ifr = 0
        self.ier = 0
        self.latch = 0xFFFF
        self.fire = None            # ciclo do próximo estouro do temporizador 1
        self.addr = 0               # o registrador escolhido no AY

    def now(self):
        return self.mb.mpu.processorCycles

    def counter(self):
        if self.fire is None:               # parado: o contador do 6522 continua descendo (a detecção da placa
            return (0xFFFF - self.now()) & 0xFFFF   # lê duas vezes e espera a diferença)
        return max(0, self.fire - self.now()) & 0xFFFF

    def tick(self, c):
        """o temporizador até o ciclo c"""
        while self.fire is not None and c >= self.fire:
            self.ifr |= 0x40
            if self.r[0xB] & 0x40:          # contínuo: recarrega
                self.fire += self.latch + 2
            else:
                self.fire = None

    def read(self, a):
        a &= 0xF
        self.tick(self.now())
        if a == 4:
            self.ifr &= ~0x40
            return self.counter() & 0xFF
        if a == 5:
            return self.counter() >> 8
        if a == 6:
            return self.latch & 0xFF
        if a == 7:
            return self.latch >> 8
        if a == 0xD:
            f = self.ifr & 0x7F
            return f | (0x80 if f & self.ier else 0)
        if a == 0xE:
            return self.ier | 0x80
        return self.r[a]

    def write(self, a, v):
        a &= 0xF
        self.tick(self.now())
        if a == 4 or a == 6:
            self.latch = (self.latch & 0xFF00) | v
        elif a == 5:
            self.latch = (self.latch & 0xFF) | v << 8
            self.ifr &= ~0x40
            self.fire = self.now() + self.latch + 1
        elif a == 7:
            self.latch = (self.latch & 0xFF) | v << 8
            self.ifr &= ~0x40
        elif a == 0xD:
            self.ifr &= ~(v & 0x7F)
        elif a == 0xE:
            if v & 0x80:
                self.ier |= v & 0x7F
            else:
                self.ier &= ~v & 0x7F
        else:
            self.r[a] = v
            if a == 0:                      # ORB: o barramento do AY
                f = v & 7
                if f == 7:
                    self.addr = self.r[1] & 0x0F
                elif f == 6:
                    self.mb.ay.append((self.now(), self.chip, self.addr, self.r[1]))
                elif not f & 4:             # /RESET
                    self.mb.ay.append((self.now(), self.chip, -1, 0))

    def irq(self):
        return bool(self.ifr & self.ier & 0x7F)


class MB(Ap):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.ay = []
        self.clicks = []
        self.via = [Via(self, 0), Via(self, 1)]

    def io(self, addr):
        if addr & 0xFF == 0x30:             # o alto-falante também
            self.clicks.append((self.mpu.processorCycles, self.mpu.pc))
        return super().io(addr)

    def read(self, addr):
        if 0xC400 <= addr < 0xC500:
            return self.via[(addr >> 7) & 1].read(addr)
        return super().read(addr)

    def write(self, addr, v):
        if 0xC400 <= addr < 0xC500:
            self.via[(addr >> 7) & 1].write(addr, v)
            return
        super().write(addr, v)


def boot(dsk):
    ap = MB(dsk)
    ap.disk_cycles = 32
    n = dsk[0]
    for p in range(n):
        ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[P2D[p] * 256:P2D[p] * 256 + 256]
    ap.ram[0x2B] = 0x60
    for k, v in enumerate(WRITE_TABLE):
        ap.ram[0x02D6 + v] = k
    ap.ram[0x3D] = n
    m = MPU(memory=Mem(ap), pc=0x0801)
    m.cycletime = list(m.cycletime); m.cycletime[0xCE] = 6
    m.x = 0x60; m.sp = 0xFF
    ap.mpu = m
    ap.fire_from = 1 << 62
    return ap, m


def main():
    a = sys.argv[1:]
    secs, name = float(a[0]), a[1]
    dsk = open(dispkg.DSK, 'rb').read()
    if os.path.exists(a[0]):                # continuar de um estado salvo: sfmb.py ESTADO SEGUNDOS NOME
        ap = pickle.load(open(a[0], 'rb')); m = ap.mpu
        secs, name, a = float(a[1]), a[2], a[1:]
    else:
        ap, m = boot(dsk)
    t0 = m.processorCycles
    end = t0 + int(secs * HZ)
    ev, every, saves = [], 0, []
    i = 2
    while i < len(a):
        if a[i] == '-s':
            every = float(a[i + 1])
        elif a[i] == '-S':
            saves.append(t0 + int(float(a[i + 1]) * HZ))
        else:
            t, _, v = a[i + 1].partition(':')
            ev.append((t0 + int(float(t) * HZ), a[i], v))
        i += 2
    ev.sort()
    d = os.path.join(ROOT, 'build', 'mb')
    os.makedirs(d, exist_ok=True)
    nxt = t0 + int(every * HZ) if every else None
    via = ap.via
    while m.processorCycles < end:
        c = m.processorCycles
        while ev and c >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ap.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ap.joy['xy'.index(k)] = int(n)
                    else: ap.btn[int(k[1])] = n != '0'
        for vv in via:
            if vv.fire is not None and c >= vv.fire:
                vv.tick(c)
        if (via[0].ifr & via[0].ier & 0x7F or via[1].ifr & via[1].ier & 0x7F) and not m.p & m.INTERRUPT:
            m.irq()
        m.step()
        if nxt and m.processorCycles >= nxt:
            sfboot.shot(ap, os.path.join(d, '%s-%03d.png' % (name, round((nxt - t0) / HZ))))
            nxt += int(every * HZ)
        if saves and m.processorCycles >= saves[0]:
            st = os.path.join(d, '%s-%g.state' % (name, (saves.pop(0) - t0) / HZ))
            pickle.dump(ap, open(st, 'wb'))
            print('estado', st, flush=True)
    pickle.dump({'ay': [(c - t0, ch, r, v) for c, ch, r, v in ap.ay], 'hz': HZ,
                 'clicks': [(c - t0, pc) for c, pc in ap.clicks]},
                open(os.path.join(d, name + '.pkl'), 'wb'))
    print('%d escritas no AY em %.1f s -> build/mb/%s.pkl' % (len(ap.ay), secs, name))


if __name__ == '__main__':
    main()
