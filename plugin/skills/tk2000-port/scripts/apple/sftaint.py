#!/usr/bin/env python3
"""De onde vêm os bytes altos dos endereços que o Sky Fox monta em tempo de execução para
$4000-$5FFF e $A000-$BFFF? (as duas áreas que trocam de lugar no TK2000)

Adaptado do tools/taint.py do Kung Fu Master: parte de um estado salvo do AppleWin e acompanha, para
cada registrador e byte de memória, o conjunto de origens do valor: ('imm', endereço de um operando
imediato) ou ('data', endereço de um byte que o programa não escreveu desde o estado inicial: veio
do disco). Quando um acesso indireto ((zp),y, (zp,x), JMP (ind)), um operando absoluto reescrito pelo
próprio código (smc) ou um RTS cai nas duas áreas, conta as origens do byte alto. O que roda com o
motor do disco ligado (as cargas) não conta, e os bytes que a carga grava viram dados novos.

    sftaint.py DISK.dsk SNAP.yaml CICLOS OUT.txt [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA] [--lc1]

--lc1: vigia, em vez das duas áreas, as leituras do banco 1 do language card ($D000-$DFFF com o
banco 1 ligado): de onde vêm os ponteiros para as figuras do banco 1.
--cores: vigia as escritas de $D5/$AA/$2A/$55 (céu e chão) e de preto/branco com o bit 7 nas telas
da cabine e da abertura, fora dos buracos: de onde vêm os valores, marcados pela regra de
tools/sfcores.py: 'troca' / 'mantem' (céu e chão), 'bit7' / 'mbw' (moldura).

Saída: uma linha por origem: tipo, endereço, valor no fim, e quem usou (PC, modo, vezes).
"""
import os, sys
from collections import Counter, defaultdict
sys.path.insert(0, os.path.dirname(__file__))
import sfboot
from a2boot import Mem
from py65.devices.mpu6502 import MPU

WATCH = lambda a: 0x4000 <= a < 0x6000 or 0xA000 <= a < 0xC000   # noqa: E731
_jm = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'src', 'janela-mask.bin')
JANELA = open(_jm, 'rb').read() if os.path.exists(_jm) else bytes(0x2000)   # --cores: a janela da cabine
MAXSET = 12
E = frozenset()
OPS = MPU().disassemble


class Ap(sfboot.Study):
    def __init__(self, dsk):
        super().__init__(dsk)
        self.joy = [128, 128]
        self.btn = [False, False]

    def stick(self, n):
        return self.joy[n]

    def buttons(self, b):
        return self.btn[b] if b < 2 else False


def main():
    a = sys.argv[1:]
    dsk = open(a[0], 'rb').read()
    ap = Ap(dsk)
    m = MPU(memory=Mem(ap), pc=0)
    m.cycletime = list(m.cycletime); m.cycletime[0xCE] = 6
    ap.mpu = m; ap.fire_from = 1 << 62; ap.disk_cycles = 32
    sfboot.load_applewin(ap, a[1])
    if '--cores' in sys.argv:
        import sfcores, execpcs, dispkg
        from sflockstep import Units
        dfr = sfcores.Deferred(ap)
        UN = Units(dsk)
        res = [execpcs.residency(ap, UN)]           # que unidade está em cada área (refeito depois das cargas)

        def unit(x):
            for nm, (b, n, reg) in res[0].items():
                if reg == 'main' and x < 0xC000 and b <= x < b + n:
                    return nm
                if reg == 'lchi' and x >= 0xE000 and b <= x < b + n:
                    return nm
                if reg == 'lc%d' % ap.lc_bank and 0xD000 <= x < 0xE000:
                    return nm
            return None

        def judge(x, v, payload, w):            # 'troca'/'bit7': muda; senão o mesmo valor fica
            if dfr.sc.of(x) is None:
                return
            pc_, orgs = payload
            c = sfcores.col(x & 0x1FFF)
            if w == 'troca':
                w = 'troca%d' % (c & 1)          # a coluna decide a cor: guarda a paridade
            w = w or ('mantem' if v in sfcores.FILL or sfcores.swapbyte(v, c) != v else 'mbw')
            for org, un, val in orgs:           # a origem com a unidade e o valor da hora da escrita
                hits[(org[0], org[1], un, val)][(pc_, w)] += 1
    t0 = m.processorCycles
    end = t0 + int(a[2])
    out = a[3]
    lc1 = '--lc1' in a
    cores = '--cores' in a
    ninst = [0]
    was_loading = [False]
    a = [x for x in a if x not in ('--lc1', '--cores')]
    if lc1:
        global WATCH
        WATCH = lambda x: 0xD000 <= x < 0xE000 and ap.lc_read and ap.lc_bank == 1   # noqa: E731
    ev = []
    i = 4
    while i < len(a):
        t, _, v = a[i + 1].partition(':')
        ev.append((t0 + int(float(t) * 1020484), a[i], v)); i += 2
    ev.sort()

    mt = {}                                     # taint da memória: endereço -> frozenset
    rt = {'a': E, 'x': E, 'y': E}
    hits = defaultdict(Counter)                 # origem -> Counter de (pc, modo)

    def mtaint(x):
        t = mt.get(x)
        return frozenset({('data', x)}) if t is None else t

    def u(*s):
        r = frozenset().union(*s)
        if len(r) > MAXSET:
            r = frozenset(sorted(r, key=lambda o: (o[0] != 'imm', o))[:MAXSET])
        return r

    def rd(x):
        return 0 if 0xC000 <= x < 0xC100 else ap.read(x)

    while m.processorCycles < end:
        while ev and m.processorCycles >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ap.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ap.joy['xy'.index(k)] = int(n)
                    else: ap.btn[int(k[1])] = n != '0'
        loading = ap.motor
        pc = m.pc
        op = rd(pc)
        mn, mode = OPS[op]
        b1, b2 = rd((pc + 1) & 0xFFFF), rd((pc + 2) & 0xFFFF)
        ea, ptr = None, None
        x, y = m.x, m.y
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
                    hits[o][(pc, mn + ' ind')] += 1
            elif mode in ('abs', 'abx', 'aby') and mn not in ('JSR', 'JMP') or mn in ('JSR', 'JMP') and mode == 'abs':
                t = mt.get((pc + 2) & 0xFFFF)   # um operando reescrito pelo próprio código
                if t is not None:
                    for o in t:
                        hits[o][(pc, mn + ' smc')] += 1
        if cores and not loading and mn in ('STA', 'STX', 'STY') and ea is not None and 0x2000 <= ea < 0x6000 \
                and (ea & 0x7F) < 0x78:
            v = {'STA': m.a, 'STX': m.x, 'STY': m.y}[mn]
            if v in sfcores.FILL or sfcores.bw(v) or sfcores.swapbyte(v, sfcores.col(ea & 0x1FFF)) != v:
                orgs = {'STA': rt['a'], 'STX': rt['x'], 'STY': rt['y']}[mn]   # a unidade de cada origem
                dfr.put(ea, v, (pc, [(o, unit(o[1]), rd(o[1])) for o in orgs]))   # agora, não na hora de julgar
        if cores and loading:
            was_loading[0] = True
        elif cores and was_loading[0]:
            was_loading[0] = False
            dfr.settle(judge)
            res[0] = execpcs.residency(ap, UN)
        if cores and ninst[0] % 5000 == 0:
            dfr.settle(judge)
        ninst[0] += 1
        if mn == 'RTS' and not loading:
            hi_a = 0x100 + ((m.sp + 2) & 0xFF)
            ret = (rd(0x100 + ((m.sp + 1) & 0xFF)) | rd(hi_a) << 8) + 1
            if WATCH(ret) and mt.get(hi_a):
                for o in mt[hi_a]:
                    hits[o][(pc, 'RTS')] += 1
        opnd = (frozenset({('imm', (pc + 1) & 0xFFFF)}) if mode == 'imm'
                else (mtaint(ea) if ea is not None and mode != 'rel' and mn not in ('JMP', 'JSR') else E))
        if mn == 'LDA':
            rt['a'] = opnd
        elif mn == 'LDX':
            rt['x'] = opnd
        elif mn == 'LDY':
            rt['y'] = opnd
        elif mn in ('ADC', 'SBC', 'AND', 'ORA', 'EOR'):
            rt['a'] = u(rt['a'], opnd)
        elif mn in ('INC', 'DEC', 'ASL', 'LSR', 'ROL', 'ROR') and ea is not None and not loading:
            pass                                # o valor muda, as origens ficam
        elif loading and mn in ('STA', 'STX', 'STY'):
            mt.pop(ea, None)                    # bytes gravados pela carga: dados novos
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
            mt[0x100 + m.sp] = rt['a']
        elif mn == 'PLA':
            rt['a'] = mtaint(0x100 + ((m.sp + 1) & 0xFF))
        elif mn == 'JSR':
            mt[0x100 + m.sp] = E
            mt[0x100 + ((m.sp - 1) & 0xFF)] = E
        m.step()
    with open(out, 'w') as f:
        for o in sorted(hits):
            c = hits[o]
            users = ', '.join('$%04X %s x%d' % (p, k, n) for (p, k), n in c.most_common(6))
            if len(o) == 4:                     # --cores: a unidade e o valor quando foi usada
                f.write('%-4s $%04X  valor $%02X  <- %s  @%s\n' % (o[0], o[1], o[3], users, o[2]))
            else:
                f.write('%-4s $%04X  valor $%02X  <- %s\n' % (o[0], o[1], rd(o[1]), users))
    print('%d origens -> %s' % (len(hits), out))


if __name__ == '__main__':
    main()
