#!/usr/bin/env python3
"""Roda o original (com boot do disco) e o porte relocado (build/port/*.bin, mapa de memória
do TK2000, ainda com a E/S do Apple) lado a lado, instrução por instrução, a partir do
momento em que o jogo começa ($AB00), com as mesmas teclas e o mesmo joystick.

Confere depois de cada instrução que o porte está no mesmo lugar (pc = reloc(pc do original)),
e a cada CHECK instruções que a memória bate (porte[reloc(a)] = original[a]; os arquivos de
código ficam de fora, já que os bytes deles diferem onde o relocs.py os mudou). As cargas do disco
do original rodam até o fim; o porte recebe o mesmo arquivo (relocado) e as mesmas mudanças de
memória de uma vez.

    lockstep.py [-c MAX_CYCLES] [-k CYCLE[:KEY]]... [-f CYCLE] [-e CYCLE:ADDR:VALUE]...
    (tempos = ciclos do original; -e faz poke de ADDR nos dois naquele momento, por exemplo para
    escolher um andar; -p PC:ADDR:VALUE faz o poke quando o original chega pela primeira vez a PC
    (nos dois); -z: compara a página zero depois de cada instrução, mais lento; -w ADDR: mostra as
    escritas do porte em ADDR, um endereço do porte)
"""
import os
import sys
from collections import deque

import a2boot
import relocs
from disa2 import reloc
from py65.devices.mpu6502 import MPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
CHECK = 20000


def port_file(name, base):
    f = os.path.join(ROOT, 'build', 'port', name + '.bin')
    if not os.path.exists(f):                   # imagens: os mesmos bytes
        f = os.path.join(ROOT, 'build', 'files', '%s_%04X.bin' % (name, base))
    return open(f, 'rb').read()


def moved(vo, vp):
    """um byte alto que o porte relocou (também um depois do fim de uma área), ou um deslocamento de página"""
    return (0x40 <= vo <= 0x60 and vp == vo + 0x60) or (0xA0 <= vo <= 0xC0 and vp == vo - 0x60) \
        or (vo, vp) == (0x20, 0x80)


def main():
    args = sys.argv[1:]
    dsk = open(os.path.join(ROOT, 'reference', 'kung_fu_master.dsk'), 'rb').read()
    max_cycles, keys, fire_from, pokes = 300_000_000, [], 1 << 62, []
    zcheck = False
    walk = None
    watch = set()
    pcpokes = []
    i = 0
    while i < len(args):
        if args[i] == '-c':
            max_cycles = int(args[i + 1]); i += 2
        elif args[i] == '-k':
            c, _, k = args[i + 1].partition(':')
            keys.append((int(c), (0x0D if k == 'r' else ord(k or ' ')) | 0x80)); i += 2
        elif args[i] == '-f':
            fire_from = int(args[i + 1]); i += 2
        elif args[i] == '-p':                                  # PC:ADDR:VALUE: poke quando o
            pc, a, v = args[i + 1].split(':')               # original chega a PC
            pcpokes.append([int(pc, 16), int(a, 16), int(v, 16)]); i += 2
        elif args[i] == '-w':                                  # mostra as escritas do porte ali
            watch.add(int(args[i + 1], 16)); i += 2
        elif args[i] == '-j':                                  # anda para L ou R (a2boot)
            walk = args[i + 1]; i += 2
        elif args[i] == '-z':                                  # página zero a cada instrução
            zcheck = True; i += 1
        elif args[i] == '-e':
            c, a, v = args[i + 1].split(':')
            pokes.append((int(c), int(a, 16), int(v, 16))); i += 2
        else:
            sys.exit('desconhecido: ' + args[i])
    keys.sort()
    pokes.sort()
    files = a2boot.catalog(dsk)

    # o original, com boot até o começo do jogo
    ao = a2boot.Apple(dsk)
    n = dsk[0]
    for p in range(n):
        ao.ram[0x800 + p * 256:0x900 + p * 256] = dsk[a2boot.P2D[p] * 256:a2boot.P2D[p] * 256 + 256]
    ao.ram[0x2B] = 0x60
    for k, v in enumerate(a2boot.WRITE_TABLE):
        ao.ram[0x02D6 + v] = k
    ao.ram[0x3D] = n
    mo = MPU(memory=a2boot.Mem(ao), pc=0x0801)
    ao.mpu = mo
    ao.fire_from = fire_from
    ao.walk = walk
    mo.x = 0x60
    mo.sp = 0xFF
    while mo.pc != 0xAB00:
        if keys and mo.processorCycles >= keys[0][0]:
            ao.key = keys.pop(0)[1]
        mo.step()
    print('começo do jogo no ciclo', mo.processorCycles)

    # o porte: a mesma memória, relocada, com o código do porte
    ap = a2boot.Apple(dsk)
    for a in range(0xC000):
        ap.ram[reloc(a)] = ao.ram[a]
    if ap.ram[0xF4] == 0x20:                    # a página sendo desenhada (relocs.PG), definida no boot
        ap.ram[0xF4] = 0x80
    loaded = {'C': 0x0400, 'D': 0x6000, 'G': 0xAB00}

    def put(name, base):
        d = port_file(name, base)
        if name == 'D':
            ap.ram[0x6000:0xA000] = d[:0x4000]
            ap.ram[0x4000:0x4000 + len(d) - 0x4000] = d[0x4000:]
        else:
            ap.ram[reloc(base):reloc(base) + len(d)] = d
    for nm, b in loaded.items():
        put(nm, b)
    d_orig = open(os.path.join(ROOT, 'build', 'files', 'D_6000.bin'), 'rb').read()
    ap.ram[relocs.RNG_TO:relocs.RNG_TO + relocs.RNG_LEN] = relocs.rng_copy(d_orig)
    mp = MPU(memory=a2boot.Mem(ap), pc=reloc(mo.pc))
    ap.mpu = mp
    ap.fire_from = fire_from
    ap.walk = walk
    for r in ('a', 'x', 'y', 'sp', 'p'):
        setattr(mp, r, getattr(mo, r))
    mp.processorCycles = mo.processorCycles
    # os botões do porte seguem o relógio do original
    ap.buttons = lambda b: ao.buttons(b)

    owner = {}                                  # bytes de código (fora da conferência de memória)

    def mark(name, base, ln):           # (endereços do Apple)
        for a in range(base, base + ln):
            owner[a] = name
    for nm, b in loaded.items():
        mark(nm, b, len(port_file(nm, b)))
    mark('RNG', relocs.RNG_TO ^ 0xE000, relocs.RNG_LEN)

    if watch:
        w1 = ap.write

        def wwatch(a, v):
            if a in watch:
                print('%10d porte $%04X <- $%02X em $%04X (original: $%02X)' % (
                    mo.processorCycles, a, v, mp.pc, ao.ram[a ^ 0xE000 if reloc(a) != a else a]))
            w1(a, v)
        ap.write = wwatch
    hist = deque(maxlen=40)
    seen = set()
    steps = 0
    while mo.processorCycles < max_cycles:
        if keys and mo.processorCycles >= keys[0][0]:
            k = keys.pop(0)[1]
            ao.key = ap.key = k
            print('%10d tecla %s' % (mo.processorCycles, chr(k & 0x7F)))
        while pokes and mo.processorCycles >= pokes[0][0]:
            _, a, v = pokes.pop(0)
            ao.write(a, v)
            ap.write(reloc(a), v)
            print('%10d poke $%04X = $%02X' % (mo.processorCycles, a, v))
        for pp in pcpokes:
            if mo.pc == pp[0]:
                ao.write(pp[1], pp[2])
                ap.write(reloc(pp[1]), pp[2])
                print('%10d em $%04X: poke $%04X = $%02X' % (mo.processorCycles, mo.pc, pp[1], pp[2]))
        pcpokes = [pp for pp in pcpokes if pp[0] != mo.pc]
        if mo.pc == 0xBB00:                     # uma carga do disco: o original a roda até o fim
            name = chr(mo.a & 0x7F)
            ret_sp = (mo.sp + 2) & 0xFF
            writes = {}
            w0 = ao.write

            def wtrace(a, v):
                if a not in writes and a < 0xC000:
                    writes[a] = ao.ram[a]       # (o valor antes da carga)
                w0(a, v)
            ao.write = wtrace
            while not (mo.sp == ret_sp and mo.pc < 0xBB00):
                mo.step()
            ao.write = w0
            a0, ln = files[name]
            for a, before in writes.items():    # o que a carga mudou (não os bytes do próprio
                v = ao.ram[a]                   # carregador)
                if not a0 <= a < a0 + ln and a < 0xBB00 and v != before:
                    ap.ram[reloc(a)] = v
            put(name, a0)
            mark(name, a0, ln)
            for r in ('a', 'x', 'y', 'sp', 'p'):
                setattr(mp, r, getattr(mo, r))
            mp.pc = reloc(mo.pc)
            mp.processorCycles = mo.processorCycles
            print('%10d carga %s' % (mo.processorCycles, name))
            continue
        hist.append((mo.pc, mp.pc))
        mo.step()
        mp.step()
        steps += 1
        if mp.pc != reloc(mo.pc):
            print('DIVERGIU no ciclo %d: original $%04X, porte $%04X (esperado $%04X)' % (
                mo.processorCycles, mo.pc, mp.pc, reloc(mo.pc)))
            for o, p in list(hist)[-12:]:
                print('   orig $%04X  porte $%04X' % (o, p))
            print('   agora A %02X/%02X X %02X/%02X Y %02X/%02X' % (mo.a, mp.a, mo.x, mp.x, mo.y, mp.y))
            return 1
        if zcheck:
            for a in range(0x100):
                vo, vp = ao.ram[a], ap.ram[a]
                if vo != vp and not moved(vo, vp) and a not in seen:
                    seen.add(a)
                    print('%10d página zero $%02X: %02X/%02X depois de $%04X' % (mo.processorCycles, a, vo, vp, hist[-1][0]))
        if steps % CHECK == 0:
            diffs = []
            for a in range(0xC000):
                if a in owner or 0x0100 <= a < 0x0200:
                    continue
                vo, vp = ao.ram[a], ap.ram[reloc(a)]
                if vo != vp and not moved(vo, vp):
                    diffs.append((a, vo, vp))
            new = [d for d in diffs if d[0] not in seen]
            if new:
                seen.update(d[0] for d in new)
                print('%10d memória: %d diferenças, novas: %s' % (mo.processorCycles, len(diffs), ' '.join(
                    '$%04X:%02X/%02X' % d for d in new[:24])))
    print('nenhuma divergência até o ciclo', mo.processorCycles)
    return 0


if __name__ == '__main__':
    sys.exit(main())
