#!/usr/bin/env python3
"""De onde vêm os ponteiros do jogo para $4000-$5FFF e $A000-$BFFF?

No TK2000 a página 2 de hi-res fica em $A000, não em $4000: o porte troca as duas áreas de 8K (a
página 2 do Apple vai para $A000, o código e os overlays em $A000-$BFFF vão para $4000). Operandos
de código acompanham os rótulos ao remontar; ponteiros montados em tempo de execução, não. Este
script roda o jogo como o tools/a2boot.py e acompanha, para cada registrador e byte de memória, o
conjunto de origens do valor dele: ('imm', endereço de um operando imediato) ou ('data', endereço
de um byte que o programa nunca escreveu, ou seja, vindo dos arquivos do disco). Sempre que um
acesso indireto, JMP (ind) ou RTS cai nas duas áreas, as origens do byte alto do endereço são contadas.

    taint.py DISK.dsk [a2boot options] > build/taint.txt
"""
import sys
from collections import Counter, defaultdict

import a2boot
from py65.devices.mpu6502 import MPU

WATCH = lambda a: 0x4000 <= a < 0x6000 or 0xA000 <= a < 0xC000   # noqa: E731
MAXSET = 12
E = frozenset()

LEN = {'imp': 1, 'acc': 1, 'imm': 2, 'zpg': 2, 'zpx': 2, 'zpy': 2, 'inx': 2, 'iny': 2, 'rel': 2,
       'abs': 3, 'abx': 3, 'aby': 3, 'ind': 3}
OPS = MPU().disassemble


def main():
    args = sys.argv[1:]
    dsk = open(args[0], 'rb').read()
    max_cycles, keys, fire_from = 200_000_000, [], 1 << 62
    pcpokes = []
    i = 1
    while i < len(args):
        if args[i] == '-c':
            max_cycles = int(args[i + 1]); i += 2
        elif args[i] == '-k':
            c, _, k = args[i + 1].partition(':')
            keys.append((int(c), (0x0D if k == 'r' else ord(k or ' ')) | 0x80)); i += 2
        elif args[i] == '-f':
            fire_from = int(args[i + 1]); i += 2
        elif args[i] == '-p':                   # PC:ADDR:VALUE: poke quando o PC é atingido
            pc_, a_, v_ = args[i + 1].split(':')
            pcpokes.append((int(pc_, 16), int(a_, 16), int(v_, 16))); i += 2
        else:
            sys.exit('desconhecido: ' + args[i])
    ap = a2boot.Apple(dsk)
    n = dsk[0]
    for p in range(n):
        ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[a2boot.P2D[p] * 256:a2boot.P2D[p] * 256 + 256]
    ap.ram[0x2B] = 0x60
    for k, v in enumerate(a2boot.WRITE_TABLE):
        ap.ram[0x02D6 + v] = k
    ap.ram[0x3D] = n
    files = a2boot.catalog(dsk)
    owner = ['boot'] * 0x10000
    mpu = MPU(memory=a2boot.Mem(ap), pc=0x0801)
    mpu.cycletime = list(mpu.cycletime)
    mpu.cycletime[0xCE] = 6
    ap.mpu = mpu
    ap.fire_from = fire_from
    mpu.x = 0x60
    mpu.sp = 0xFF
    keys.sort()

    mt = {}                                     # taint da memória: endereço -> frozenset
    rt = {'a': E, 'x': E, 'y': E}
    hits = defaultdict(Counter)                 # origem -> Counter de (owner, pc, kind)
    loading = False

    def mtaint(a):
        t = mt.get(a)
        if t is None:
            return frozenset({('data', owner[a], a)})
        return t

    def u(*s):
        r = frozenset().union(*s)
        if len(r) > MAXSET:
            r = frozenset(sorted(r, key=lambda o: (o[0] != 'imm', o))[:MAXSET])
        return r

    def rd(a):
        return ap.read(a) if not 0xC000 <= a < 0xC100 else 0

    while mpu.processorCycles < max_cycles:
        if keys and mpu.processorCycles >= keys[0][0]:
            ap.key = keys[0][1]
            keys.pop(0)
        pc = mpu.pc
        if pcpokes and any(pp[0] == pc for pp in pcpokes):
            for pp in [pp for pp in pcpokes if pp[0] == pc]:
                ap.write(pp[1], pp[2])
            pcpokes = [pp for pp in pcpokes if pp[0] != pc]
        if pc == 0xBB00:                        # cargas do disco: os bytes dos arquivos são dados novos
            name = chr(mpu.a & 0x7F)
            if name in files:
                a0, ln = files[name]
                owner[a0:a0 + ln] = [name] * ln
                for a in range(a0, a0 + ln):
                    mt.pop(a, None)
            print('carga', name, file=sys.stderr)
        loading = 0xB800 <= pc < 0xC000 or pc < 0x0D00 and pc >= 0x0800 and owner[pc] == 'boot'
        op = rd(pc)
        mn, mode = OPS[op]
        b1, b2 = rd(pc + 1), rd(pc + 2)
        ea, ptr = None, None
        x, y = mpu.x, mpu.y
        if mode == 'zpg':
            ea = b1
        elif mode == 'zpx':
            ea = (b1 + x) & 0xFF
        elif mode == 'zpy':
            ea = (b1 + y) & 0xFF
        elif mode == 'abs':
            ea = b1 | b2 << 8
        elif mode == 'abx':
            ea = ((b1 | b2 << 8) + x) & 0xFFFF
        elif mode == 'aby':
            ea = ((b1 | b2 << 8) + y) & 0xFFFF
        elif mode == 'inx':
            ptr = (b1 + x) & 0xFF
            ea = rd(ptr) | rd((ptr + 1) & 0xFF) << 8
        elif mode == 'iny':
            ptr = b1
            ea = ((rd(ptr) | rd((ptr + 1) & 0xFF) << 8) + y) & 0xFFFF
        elif mode == 'ind':
            ptr = b1 | b2 << 8
            ea = rd(ptr) | rd((ptr & 0xFF00) | ((ptr + 1) & 0xFF)) << 8
        if not loading and ea is not None and WATCH(ea):
            if ptr is not None:
                hi = (ptr + 1) & 0xFF if ptr < 0x100 else ((ptr & 0xFF00) | ((ptr + 1) & 0xFF))
                for o in mtaint(hi):
                    hits[o][(owner[pc], pc, mn + ' ind')] += 1
            elif mode in ('abs', 'abx', 'aby'):
                t = mt.get(pc + 2)              # um operando modificado
                if t is not None:
                    for o in t:
                        hits[o][(owner[pc], pc, mn + ' smc')] += 1
        if mn == 'RTS' and not loading:
            hi_a = 0x100 + ((mpu.sp + 2) & 0xFF)
            ret = (rd(0x100 + ((mpu.sp + 1) & 0xFF)) | rd(hi_a) << 8) + 1
            if WATCH(ret) and mt.get(hi_a) is not None:
                for o in mt[hi_a]:
                    if o[0] == 'imm' or (o[0] == 'data'):
                        hits[o][(owner[pc], pc, 'RTS')] += 1
        # propaga
        opnd = (frozenset({('imm', owner[pc], pc + 1)}) if mode == 'imm'
                else (mtaint(ea) if ea is not None and mode != 'rel' and mn not in ('JMP', 'JSR') else E))
        if mn in ('LDA',):
            rt['a'] = opnd
        elif mn == 'LDX':
            rt['x'] = opnd
        elif mn == 'LDY':
            rt['y'] = opnd
        elif mn in ('ADC', 'SBC', 'AND', 'ORA', 'EOR'):
            rt['a'] = u(rt['a'], opnd)
        elif loading and mn in ('STA', 'STX', 'STY'):
            mt.pop(ea, None)                    # os bytes do carregador: dados novos
        elif mn == 'STA':
            mt[ea] = rt['a']
        elif mn == 'STX':
            mt[ea] = rt['x']
        elif mn == 'STY':
            mt[ea] = rt['y']
        elif mn == 'TAX':
            rt['x'] = rt['a']
        elif mn == 'TAY':
            rt['y'] = rt['a']
        elif mn == 'TXA':
            rt['a'] = rt['x']
        elif mn == 'TYA':
            rt['a'] = rt['y']
        elif mn == 'PHA':
            mt[0x100 + mpu.sp] = rt['a']
        elif mn == 'PLA':
            rt['a'] = mtaint(0x100 + ((mpu.sp + 1) & 0xFF))
        elif mn == 'JSR':
            mt[0x100 + mpu.sp] = E
            mt[0x100 + ((mpu.sp - 1) & 0xFF)] = E
        mpu.step()
    print('ciclos', mpu.processorCycles, file=sys.stderr)
    for o in sorted(hits):
        c = hits[o]
        users = ', '.join('%s:$%04X %s x%d' % (f, p, k, m) for (f, p, k), m in c.most_common(6))
        print('%-4s %-5s $%04X  valor $%02X  <- %s' % (o[0], o[1], o[2], rd(o[2]), users))


if __name__ == '__main__':
    main()
