#!/usr/bin/env python3
"""Lockstep do Sky Fox: o original (Apple de 64K do py65) e o porte relocado (mapa de memória do
TK2000, ainda com a E/S do Apple) lado a lado, instrução por instrução, a partir de um estado salvo
do AppleWin, com as mesmas teclas e o mesmo joystick.

O porte: a memória do estado traduzida para o TK2000 (sfrelocs.reloc na RAM principal; o banco do
language card em uso na fase em $D000; as figuras do banco 1 do voo em $C200 + 2 páginas; $E000-$FFFF
igual) e, em cada unidade carregada (tools/dispkg.py), os bytes em que a versão do TK2000
(build/tk/NAME.bin) difere do original. $C100-$FFFF é RAM simples, sem bancos.

Confere depois de cada instrução que o porte está no mesmo lugar (pc = pcmap(pc do original)) e, a
cada CHECK instruções, que a memória bate (bytes de código relocados ficam de fora; um byte alto
relocado ou o deslocamento de página $20 -> $80 contam como iguais). As cargas do disco rodam só no
original; o porte recebe o que elas escreveram, traduzido, e as unidades carregadas na versão TK2000.

    sflockstep.py SNAP.yaml CICLOS [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA] [-z] [-w ADDR]

-w ADDR: mostra as escritas em ADDR (um endereço do Apple) nos dois, com o PC e o valor.
"""
import os, sys
from collections import deque
sys.path.insert(0, os.path.dirname(__file__))
import sfboot, dispkg
from sfrelocs import reloc
from sftaint import Ap
from a2boot import Mem
from py65.devices.mpu6502 import MPU

ROOT = dispkg.ROOT
CHECK = 20000
from sfrelocs import FIG_HI, FIGSPLIT, fig_map
FIGS = {'t18', 't13'}


class Port(Ap):
    """O TK2000 de 64K com a RAM ligada: $C100-$FFFF é RAM simples (E/S do Apple em $C000-$C0FF)."""
    def __init__(self, dsk):
        super().__init__(dsk)
        self.hi = bytearray(0x4000)

    def read(self, addr):
        if 0xC000 <= addr < 0xC100:
            return self.io(addr)
        if addr >= 0xC100:
            return self.hi[addr - 0xC000]
        return self.ram[addr]

    def write(self, addr, v):
        if 0xC000 <= addr < 0xC100:
            self.io(addr)
        elif addr >= 0xC100:
            self.hi[addr - 0xC000] = v
        else:
            self.ram[addr] = v


def moved(vo, vp):
    return (0x40 <= vo < 0x60 and vp == vo + 0x60) or (0xA0 <= vo < 0xC0 and vp == vo - 0x60) \
        or (vo, vp) == (0x20, 0x80)


def pcmap(pc):
    return reloc(pc) if pc < 0xC000 else pc


def fig_addr(k, unit):
    """o endereço no TK2000 do byte k ($000-$FFF) das figuras do banco 1 (None: página vazia)"""
    return fig_map(0xD000 + k, unit)


def put_figs(pt, data, unit):
    for k in range(0x1000):
        x = fig_addr(k, unit)
        if x is not None:
            pt.write(x, data[k])


class Units:
    """os bytes originais e os da versão TK2000 de cada unidade"""
    def __init__(self, dsk):
        self.src, self.tk = {}, {}
        for nm, (t, base, region, runs) in dispkg.PKGS.items():
            self.src[nm] = dispkg.source(dsk, t, base)
            f = os.path.join(ROOT, 'build', 'tk', nm + '.bin')
            self.tk[nm] = open(f, 'rb').read() if os.path.exists(f) else self.src[nm]

    def which(self, region, base, mem):
        """a unidade de PKGS nessa região e endereço que mais se parece com mem (4K ou o tamanho dela)"""
        best, score = None, 0.5
        for nm, (t, b, r, runs) in dispkg.PKGS.items():
            if r != region or b != base:
                continue
            s = self.src[nm]
            m = sum(1 for k in range(0, len(s), 4) if mem[k] == s[k]) / (len(s) / 4)
            if m > score:
                best, score = nm, m
        return best


def build_port(ao, pt, U):
    for a in range(0xC000):
        pt.ram[reloc(a)] = ao.ram[a]
    if pt.ram[0x20] == 0x20:
        pt.ram[0x20] = 0x80
    import sfrelocs, dispkg as dk
    res = dk.source(None, ('res', 0x10000), 0)       # a memória depois da carga inicial
    for p in range(0x20, 0x60):                     # código instalado nos buracos depois da carga
        for h in (0x78, 0xF8):
            x = p * 256 + h
            cur = bytes(ao.ram[x:x + 8])
            if cur != res[x:x + 8]:
                pt.ram[reloc(x):reloc(x) + 8] = sfrelocs.snippet(cur)
    sp = ao.mpu.sp                  # endereços de retorno na pilha: um JSR antes do endereço apontado
    for s in range(0x101 + sp, 0x1FF):
        ret = ao.ram[s] | ao.ram[s + 1] << 8
        if (0x4000 <= ret < 0x6000 or 0xA000 <= ret < 0xC000) and ao.ram[(ret - 2) & 0xFFFF] == 0x20:
            pt.ram[s + 1] = reloc(ret) >> 8
    lc1 = U.which('lc1', 0xD000, ao.lc[0])
    lc2 = U.which('lc2', 0xD000, ao.lc[1])
    if lc1 in FIGS:
        put_figs(pt, ao.lc[0], lc1)
        pt.hi[0x1000:0x2000] = ao.lc[1]
        dset = lc2
    elif lc1 == 't25' and lc2 != 't23':
        pt.hi[0x1000:0x2000] = ao.lc[0]
        dset = lc1
    else:
        pt.hi[0x1000:0x2000] = ao.lc[1]
        dset = lc2
    pt.hi[0x2000:0x4000] = ao.lc_hi
    hi1 = U.which('lchi', 0xE000, ao.lc_hi[:0x1000])
    hi2 = U.which('lchi', 0xF000, ao.lc_hi[0x1000:])
    loaded = {}
    for nm, (t, base, region, runs) in dispkg.PKGS.items():   # t7: residente (metade são variáveis)
        if region == 'main':
            n = len(U.src[nm])
            if isinstance(t, tuple) or nm == 't7' or U.which('main', base, ao.ram[base:base + n]) == nm:
                loaded[nm] = base
    for nm in (dset, hi1, hi2):
        if nm:
            loaded[nm] = dispkg.PKGS[nm][1]
    code = set()                    # endereços do Apple (RAM principal) de bytes relocados
    for nm, base in loaded.items():
        s, t = U.src[nm], U.tk[nm]
        for k in range(len(s)):
            if s[k] != t[k]:
                a = base + k
                cur = ao.ram[a] if a < 0xC000 else pt.read(a)
                if a < 0xC000 and cur == s[k]:
                    pt.ram[reloc(a)] = t[k]
                elif a < 0xC000 and s[k] ^ t[k] == 0xE0 and (0x40 <= cur < 0x60 or 0xA0 <= cur < 0xC0) \
                        and not (0x2000 <= a < 0x6000 and (a & 0x7F) >= 0x78):   # buracos: já traduzidos
                    pt.ram[reloc(a)] = cur ^ 0xE0          # um operando reescrito antes do estado salvo
                elif a >= 0xD000:
                    pt.write(a, t[k])
                code.add(a)
    return loaded, code, lc1


def main():
    a = sys.argv[1:]
    dsk = open(dispkg.DSK, 'rb').read()
    U = Units(dsk)
    ao = Ap(dsk)
    mo = MPU(memory=Mem(ao), pc=0)
    mo.cycletime = list(mo.cycletime); mo.cycletime[0xCE] = 6
    ao.mpu = mo; ao.fire_from = 1 << 62; ao.disk_cycles = 32
    sfboot.load_applewin(ao, a[0])
    t0 = mo.processorCycles
    end = t0 + int(a[1])
    zcheck = '-z' in a
    watch = {int(a[k + 1], 16) for k in range(len(a)) if a[k] == '-w'}
    ev = []
    i = 2
    while i < len(a):
        if a[i] in ('-k', '-j'):
            t, _, v = a[i + 1].partition(':')
            ev.append((t0 + int(float(t) * 1020484), a[i], v)); i += 2
        else:
            i += 1
    ev.sort()

    pt = Port(dsk)
    mp = MPU(memory=Mem(pt), pc=pcmap(mo.pc))
    mp.cycletime = mo.cycletime
    pt.mpu = mp; pt.fire_from = 1 << 62
    for r in ('a', 'x', 'y', 'sp', 'p', 'processorCycles'):
        setattr(mp, r, getattr(mo, r))
    pt.key = ao.key
    loaded, code, lc1 = build_port(ao, pt, U)
    import sfrelocs
    owned = set()                                       # bytes que o porte acrescenta: fora da conferência
    for x, b in sfrelocs.LAYER.items():
        for k, v in enumerate(b):
            pt.write(x + k, v)
            owned.add(x + k)
    spans = {a: a + len(old) for nm, d in sfrelocs.CODE.items() for a, (old, new) in d.items()
             if len(old) > 1}                           # trechos trocados com outras fronteiras de instrução
    print('unidades carregadas:', ' '.join(sorted(loaded)), '| banco 1:', lc1)
    pt.joy, pt.btn = ao.joy, ao.btn                     # o mesmo joystick

    if watch:
        wo, wp = ao.write, pt.write
        wpt = {reloc(x) if x < 0xC000 else x: x for x in watch}

        def wwo(x, v):
            if x in watch:
                print('%10d original $%04X <- $%02X em $%04X' % (mo.processorCycles, x, v, mo.pc))
            wo(x, v)

        def wwp(x, v):
            if x in wpt:
                print('%10d porte    $%04X <- $%02X em $%04X' % (mp.processorCycles, x, v, mp.pc))
            wp(x, v)
        ao.write, pt.write = wwo, wwp
    hist = deque(maxlen=40)
    seen = set()
    steps = 0
    while mo.processorCycles < end:
        while ev and mo.processorCycles >= ev[0][0]:
            _, kind, v = ev.pop(0)
            if kind == '-k':
                ao.key = pt.key = ({'r': 0x0D, 'sp': 0x20, 'esc': 0x1B}.get(v, ord(v[0]))) | 0x80
            else:
                for kv in v.split(','):
                    k, _, n = kv.partition('=')
                    if k in ('x', 'y'): ao.joy['xy'.index(k)] = int(n)
                    else: ao.btn[int(k[1])] = n != '0'
            print('%10d %s %s' % (mo.processorCycles, kind, v))
        if ao.motor:                                    # uma carga: só no original, até o motor parar
            writes = []
            w0 = ao.write

            def wtrace(x, v):
                if x < 0xC000:
                    writes.append(('main', x))
                elif x >= 0xD000 and ao.lc_write:
                    writes.append(('lc%d' % ao.lc_bank if x < 0xE000 else 'lchi', x))
                w0(x, v)
            ao.write = wtrace
            while ao.motor:
                mo.step()
            ao.write = w0
            blocks = set()
            for region, x in writes:
                if region == 'main':
                    pt.ram[reloc(x)] = ao.ram[x]
                    blocks.add(('main', x & 0xF000))
                elif region == 'lc1':
                    v = ao.lc[0][x - 0xD000]
                    blocks.add(('lc1', 0xD000))
                elif region == 'lc2':
                    pt.write(x, ao.lc[1][x - 0xD000])
                    blocks.add(('lc2', 0xD000))
                else:
                    pt.write(x, ao.lc_hi[x - 0xE000])
                    blocks.add(('lchi', x & 0xF000))
            names = []
            for region, base in sorted(blocks):
                mem = ao.ram[base:base + 0x1000] if region == 'main' else (
                    ao.lc[0] if region == 'lc1' else ao.lc[1] if region == 'lc2' else
                    ao.lc_hi[base - 0xE000:base - 0xD000])
                nm = U.which(region, base, mem)
                if region == 'lc1':
                    if nm in FIGS:
                        put_figs(pt, ao.lc[0], nm)
                    else:
                        pt.hi[0x1000:0x2000] = ao.lc[0]
                    lc1 = nm
                if nm:
                    names.append(nm)
                    s, t = U.src[nm], U.tk[nm]
                    for k in range(len(s)):
                        x = base + k
                        if s[k] != t[k]:
                            code.add(x)
                            if region == 'main':
                                pt.ram[reloc(x)] = t[k]
                            elif region != 'lc1' or nm not in FIGS:
                                pt.write(x, t[k])
            for r in ('a', 'x', 'y', 'sp', 'p', 'processorCycles'):
                setattr(mp, r, getattr(mo, r))
            mp.pc = pcmap(mo.pc)
            print('%10d carga: %s (trilhas %s)' % (mo.processorCycles, ' '.join(names) or '?',
                                                   ','.join(str(t) for c, t in ao.track_log[-12:])))
            continue
        hist.append((mo.pc, mp.pc))
        if mo.pc in spans:                              # atravessa o trecho trocado nos dois
            e = spans[mo.pc]
            while mo.pc != e:
                mo.step()
            while mp.pc != pcmap(e):
                mp.step()
        else:
            mo.step()
            mp.step()
        steps += 1
        if mp.pc != pcmap(mo.pc) or mp.sp != mo.sp:
            print('DIVERGIU no ciclo %d (%.2f s): original $%04X, porte $%04X (esperado $%04X)' % (
                mo.processorCycles, (mo.processorCycles - t0) / 1020484, mo.pc, mp.pc, pcmap(mo.pc)))
            for o, p in list(hist)[-14:]:
                print('   orig $%04X  porte $%04X' % (o, p))
            print('   agora A %02X/%02X X %02X/%02X Y %02X/%02X S %02X/%02X' % (mo.a, mp.a, mo.x, mp.x, mo.y, mp.y, mo.sp, mp.sp))
            print('   pilha original', ' '.join('%02X' % ao.ram[0x100 + ((mo.sp - 2 + k) & 0xFF)] for k in range(10)))
            print('   pilha porte   ', ' '.join('%02X' % pt.ram[0x100 + ((mp.sp - 2 + k) & 0xFF)] for k in range(10)))
            return 1
        if zcheck:
            for x in range(0x100):
                vo, vp = ao.ram[x], pt.ram[x]
                if vo != vp and not moved(vo, vp) and x not in seen:
                    seen.add(x)
                    print('%10d página zero $%02X: %02X/%02X depois de $%04X' % (mo.processorCycles, x, vo, vp, hist[-1][0]))
        if steps % CHECK == 0:
            diffs = []
            for x in range(0xC000):
                if x in code or x in owned or 0x0100 <= x < 0x0200 or (lc1 == "t13" and FIG_HI <= x < FIG_HI + 0xE000 - FIGSPLIT):
                    continue
                vo, vp = ao.ram[x], pt.ram[reloc(x)]
                if vo != vp and not moved(vo, vp):
                    diffs.append((x, vo, vp))
            for x in range(0xE000, 0x10000):
                if x in code:
                    continue
                vo, vp = ao.lc_hi[x - 0xE000], pt.hi[x - 0xC000]
                if vo != vp and not moved(vo, vp):
                    diffs.append((x, vo, vp))
            new = [d for d in diffs if d[0] not in seen]
            if new:
                seen.update(d[0] for d in new)
                print('%10d (%.2f s) memória: %d diferenças, novas: %s' % (
                    mo.processorCycles, (mo.processorCycles - t0) / 1020484, len(diffs),
                    ' '.join('$%04X:%02X/%02X' % d for d in new[:20])))
    print('nenhuma divergência até o ciclo %d (%.1f s)' % (mo.processorCycles, (mo.processorCycles - t0) / 1020484))
    return 0


if __name__ == '__main__':
    sys.exit(main())
