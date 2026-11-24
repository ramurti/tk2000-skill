#!/usr/bin/env python3
"""Dá boot numa imagem de disco Apple II em ordem DOS (.dsk) num Apple II pequeno (6502 do py65,
64K, language card, Disk II no slot 6 alimentado com nibbles 6-and-2 padrão) e registra o que o
carregador faz: os setores que lê, para onde a execução vai, as consultas ao teclado. Grava a
memória no fim.

    a2boot.py DISK.dsk [-c MAX_CYCLES] [-k CYCLE] [-o PREFIX]
      -k CYCLE[:KEY]: uma tecla (padrão: espaço) é apertada naquele ciclo; pode haver várias
          (KEY: um caractere, ou r = RETURN)
      -f CYCLE: daí em diante, o botão 0 é apertado de vez em quando (o joystick fica no centro)
      -j L|R: e anda para aquele lado (com pulos e agachadas)
      -p PC:ADDR:VALUE: faz poke de ADDR quando PC é atingido pela primeira vez (C $1F22, $04B3/$04B4: o andar)
      -o: grava PREFIX-start.bin ($0000-$BFFF quando o jogo começa em $AB00), PREFIX-ram.bin
          (no fim) e PREFIX-code.txt (os endereços executados)
A ROM do monitor não está incluída: $D000-$FFFF é lido como RTS ($60) quando a language card está
desligada, então chamadas à ROM (COUT, HOME, ...) retornam na hora.
"""
import os
import sys
from collections import Counter
from py65.devices.mpu6502 import MPU

P2D = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]   # setor físico -> setor DOS
WRITE_TABLE = [
    0x96, 0x97, 0x9A, 0x9B, 0x9D, 0x9E, 0x9F, 0xA6, 0xA7, 0xAB, 0xAC, 0xAD, 0xAE, 0xAF, 0xB2, 0xB3,
    0xB4, 0xB5, 0xB6, 0xB7, 0xB9, 0xBA, 0xBB, 0xBC, 0xBD, 0xBE, 0xBF, 0xCB, 0xCD, 0xCE, 0xCF, 0xD3,
    0xD6, 0xD7, 0xD9, 0xDA, 0xDB, 0xDC, 0xDD, 0xDE, 0xDF, 0xE5, 0xE6, 0xE7, 0xE9, 0xEA, 0xEB, 0xEC,
    0xED, 0xEE, 0xEF, 0xF2, 0xF3, 0xF4, 0xF5, 0xF6, 0xF7, 0xF9, 0xFA, 0xFB, 0xFC, 0xFD, 0xFE, 0xFF]


def four4(v):
    return [(v >> 1) | 0xAA, v | 0xAA]


def encode62(data):
    aux = [0] * 86
    for i, b in enumerate(data):
        bits = ((b & 1) << 1) | ((b >> 1) & 1)
        aux[i % 86] |= bits << (2 * (i // 86))
    buf = aux + [b >> 2 for b in data]
    out, prev = [], 0
    for v in buf:
        out.append(WRITE_TABLE[v ^ prev])
        prev = v
    out.append(WRITE_TABLE[prev])
    return out


def nib_track(dsk, t, vol=254):
    nibs = [0xFF] * 48
    for p in range(16):
        nibs += [0xD5, 0xAA, 0x96] + four4(vol) + four4(t) + four4(p) + four4(vol ^ t ^ p)
        nibs += [0xDE, 0xAA, 0xEB] + [0xFF] * 6
        off = (t * 16 + P2D[p]) * 256
        nibs += [0xD5, 0xAA, 0xAD] + encode62(dsk[off:off + 256]) + [0xDE, 0xAA, 0xEB]
        nibs += [0xFF] * 20
    return nibs


class Apple:
    def __init__(self, dsk):
        self.dsk = dsk
        self.tracks = [nib_track(dsk, t) for t in range(35)]
        self.ram = bytearray(0x10000)
        self.lc = [bytearray(0x1000), bytearray(0x1000)]      # bancos 1, 2 de $D000
        self.lc_hi = bytearray(0x2000)                         # $E000-$FFFF
        self.lc_read = False
        self.lc_write = False
        self.lc_bank = 1
        self.ht = 0                                            # meia trilha
        self.pos = 0
        self.motor = False
        self.key = 0
        self.keys = []
        self.log = []
        self.cycles = 0
        self.io_count = Counter()
        self.ptrig = 0
        self.paddle = [128, 128]                               # joystick: no centro
        self.mpu = None
        self.walk = None

    def stick(self, n):
        """paddle n (0 = x, 1 = y), 0-255: no centro, ou andando (self.walk 'L' / 'R': 3 de cada 4
        janelas de dois segundos para aquele lado; de vez em quando um pulo ou uma agachada)"""
        c = self.mpu.processorCycles
        if not self.walk or c < self.fire_from:
            return self.paddle[n]
        w = c >> 21
        if n == 0:
            return self.paddle[0] if w % 4 == 3 else (0 if self.walk == 'L' else 255)
        k = (c >> 18) % 16
        return 0 if k == 5 else (255 if k == 11 else self.paddle[1])

    def buttons(self, b):
        """Botão b apertado? (botão 0 apertado de vez em quando, para o jogo ver o tiro)"""
        return b == 0 and self.fire_from <= self.mpu.processorCycles and \
            (self.mpu.processorCycles // 400000) % 4 == 0

    # language card
    def lc_switch(self, a):
        a &= 0x0F
        self.lc_bank = 1 if a & 8 else 2
        self.lc_read = (a & 3) in (0, 3)
        self.lc_write = bool(a & 1)

    def read(self, addr):
        if 0xC000 <= addr < 0xC100:
            return self.io(addr)
        if addr >= 0xD000:
            if not self.lc_read:
                return 0x60
            if addr < 0xE000:
                return self.lc[self.lc_bank - 1][addr - 0xD000]
            return self.lc_hi[addr - 0xE000]
        if addr >= 0xC100:
            return 0x60
        return self.ram[addr]

    def write(self, addr, v):
        if 0xC000 <= addr < 0xC100:
            self.io(addr)
            return
        if addr >= 0xD000:
            if self.lc_write:
                if addr < 0xE000:
                    self.lc[self.lc_bank - 1][addr - 0xD000] = v
                else:
                    self.lc_hi[addr - 0xE000] = v
            return
        if addr < 0xC000:
            self.ram[addr] = v

    def io(self, addr):
        a = addr & 0xFF
        self.io_count[addr] += 1
        if a == 0x00:
            return self.key
        if a == 0x10:
            self.key &= 0x7F
            return 0
        if a == 0x70:                                          # os temporizadores dos paddles começam
            self.ptrig = self.mpu.processorCycles
            return 0
        if 0x64 <= a < 0x68:                                   # paddle n: 11 ciclos por unidade
            v = self.stick(a & 1)
            return 0x80 if self.mpu.processorCycles - self.ptrig < v * 11 else 0
        if 0x61 <= a < 0x64:                                   # botões 0-2
            b = a - 0x61
            return 0x80 if self.buttons(b) else 0
        if 0x80 <= a < 0x90:
            self.lc_switch(a)
            return 0
        if 0xE0 <= a < 0xE8:                                   # fases do motor de passo
            if a & 1:
                p = (a - 0xE0) >> 1
                d = (p - self.ht % 4) % 4
                if d == 1:
                    self.ht = min(69, self.ht + 1)
                elif d == 3:
                    self.ht = max(0, self.ht - 1)
            return 0
        if a == 0xE8:
            self.motor = False
        elif a == 0xE9:
            self.motor = True
        elif a == 0xEC:                                        # latch de leitura: o próximo nibble
            tr = self.tracks[self.ht // 2]
            v = tr[self.pos % len(tr)]
            self.pos = (self.pos + 1) % len(tr)
            return v
        elif a == 0xEE or a == 0xED:
            return 0
        return 0


def catalog(dsk):
    """arquivos binários do DOS 3.3: nome -> (endereço de carga, tamanho)"""
    def sec(t, s):
        return dsk[(t * 16 + s) * 256:(t * 16 + s + 1) * 256]
    files = {}
    v = sec(17, 0)
    t, s = v[1], v[2]
    while t:
        c = sec(t, s)
        for e in range(7):
            x = c[11 + e * 35:46 + e * 35]
            if x[0] in (0, 0xFF) or x[2] & 0x7F != 4:
                continue
            first = sec(*sec(x[0], x[1])[12:14])
            name = bytes(b & 0x7F for b in x[3:33]).decode().rstrip()
            files[name] = (first[0] | first[1] << 8, first[2] | first[3] << 8)
        t, s = c[1], c[2]
    return files


class Mem:
    def __init__(self, a):
        self.a = a

    def __len__(self):
        return 0x10000

    def __getitem__(self, addr):
        if isinstance(addr, slice):
            return [self.a.read(i) for i in range(*addr.indices(0x10000))]
        return self.a.read(addr)

    def __setitem__(self, addr, v):
        self.a.write(addr, v & 0xFF)


def main():
    args = sys.argv[1:]
    dsk = open(args[0], 'rb').read()
    max_cycles, keys, prefix, fire_from = 200_000_000, [], None, 1 << 62
    walk, pcpokes = None, []
    i = 1
    while i < len(args):
        if args[i] == '-c':
            max_cycles = int(args[i + 1]); i += 2
        elif args[i] == '-k':                                  # CYCLE[:KEY], KEY um caractere
            c, _, k = args[i + 1].partition(':')
            keys.append((int(c), (0x0D if k == 'r' else ord(k or ' ')) | 0x80)); i += 2
        elif args[i] == '-f':                                  # botão 0 apertado de vez em quando
            fire_from = int(args[i + 1]); i += 2
        elif args[i] == '-o':
            prefix = args[i + 1]; i += 2
        elif args[i] == '-j':                                  # anda: L ou R (com -f)
            walk = args[i + 1]; i += 2
        elif args[i] == '-p':                                  # PC:ADDR:VALUE: poke quando o
            pc_, a_, v_ = args[i + 1].split(':')            # programa chega a PC pela 1a vez
            pcpokes.append((int(pc_, 16), int(a_, 16), int(v_, 16))); i += 2
        else:
            sys.exit('desconhecido: ' + args[i])
    ap = Apple(dsk)
    n = dsk[0]                                                 # a ROM de boot: setores 0..n-1
    for p in range(n):
        ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[P2D[p] * 256:P2D[p] * 256 + 256]
    ap.ram[0x2B] = 0x60
    for i, v in enumerate(WRITE_TABLE):                        # a tabela de decodificação da ROM de boot
        ap.ram[0x02D6 + v] = i                                 # ($036C-$03D5), mantida pelos carregadores
    ap.ram[0x3D] = n
    mpu = MPU(memory=Mem(ap), pc=0x0801)
    ap.mpu = mpu
    ap.fire_from = fire_from
    ap.walk = walk
    mpu.x = 0x60
    mpu.sp = 0xFF
    keys.sort()
    try:
        files = catalog(dsk)
    except (IndexError, ValueError):                           # disco sem catálogo DOS 3.3 (carregador próprio): veja sfboot.py
        files = {}
    owner = ['boot'] * 0x10000                                 # de que arquivo veio cada endereço
    code = set()                                               # executados (arquivo, endereço)
    while mpu.processorCycles < max_cycles:
        if keys and mpu.processorCycles >= keys[0][0]:
            ap.key = keys[0][1]
            print('%10d tecla %s' % (mpu.processorCycles, chr(keys[0][1] & 0x7F)))
            keys.pop(0)
        pc = mpu.pc
        if pcpokes and any(pp[0] == pc for pp in pcpokes):
            for pp in [pp for pp in pcpokes if pp[0] == pc]:
                ap.write(pp[1], pp[2])
            pcpokes = [pp for pp in pcpokes if pp[0] != pc]
        code.add((owner[pc], pc))
        if pc == 0xBB00:                                       # o carregador de arquivos: A = nome, Y = página
            name = chr(mpu.a & 0x7F)
            if name in files:
                a0, n = files[name]
                owner[a0:a0 + n] = [name] * n
            print('%10d carga do arquivo %s (catálogo em $%02X00, depois %s)' % (
                mpu.processorCycles, chr(mpu.a & 0x7F), mpu.y, 'salta' if mpu.x else 'retorna'))
        elif pc == 0xAB00 and prefix and not os.path.exists(prefix + '-start.bin'):
            open(prefix + '-start.bin', 'wb').write(bytes(ap.ram[:0xC000]))
            print('%10d começo do jogo $AB00: memória gravada' % mpu.processorCycles)
        mpu.step()
        if mpu.pc == pc and ap.read(pc) == 0x4C:               # JMP para si mesmo: parado
            print('parado em $%04X' % pc)
            break
    print('ciclos', mpu.processorCycles, 'pc $%04X' % mpu.pc)
    print('E/S usada:', ' '.join('$%04X:%d' % (a, k) for a, k in sorted(ap.io_count.items())))
    if prefix:
        open(prefix + '-ram.bin', 'wb').write(bytes(ap.ram[:0xC000]))
        open(prefix + '-code.txt', 'w').write(''.join('%s %04X\n' % c for c in sorted(code)))


if __name__ == '__main__':
    main()
