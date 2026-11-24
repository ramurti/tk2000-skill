#!/usr/bin/env python3
"""As instruções que o original executa, por unidade (tools/dispkg.py), a partir de um estado do
AppleWin: depois de cada carga de disco descobre de novo que pacote está em cada área (como o
lockstep), então uma medição pode atravessar fases sem misturar o código de pacotes diferentes no
mesmo endereço. Grava build/use/exec-NOME.pkl ({unidade: set(PCs)}); o dispkg.py usa os PCs como
pontos de entrada (SEEDS).

    execpcs.py SNAP.yaml CICLOS NOME [-j SEG:x=..,y=..,b0=..] [-k SEG:TECLA]
"""
import os, pickle, sys
sys.path.insert(0, os.path.dirname(__file__))
import sfboot, dispkg
import sflockstep as L
from sftaint import Ap
from a2boot import Mem
from py65.devices.mpu6502 import MPU


def residency(ao, U):
    """unidade -> (base, tamanho, região) das unidades na memória agora"""
    out = {}
    for nm, (t, base, region, runs) in dispkg.PKGS.items():
        n = len(U.src[nm])
        if region == 'main':
            if isinstance(t, tuple) or nm == 't7' or U.which('main', base, ao.ram[base:base + n]) == nm:
                out[nm] = (base, n, region)
    for region, mem, base in (('lc1', ao.lc[0], 0xD000), ('lc2', ao.lc[1], 0xD000),
                              ('lchi', ao.lc_hi[:0x1000], 0xE000), ('lchi', ao.lc_hi[0x1000:], 0xF000)):
        nm = U.which(region, base, mem)
        if nm:
            out[nm] = (base, 0x1000, region)
    return out


def main():
    a = sys.argv[1:]
    dsk = open(dispkg.DSK, 'rb').read()
    U = L.Units(dsk)
    ao = Ap(dsk)
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
        t, _, v = a[i + 1].partition(':')
        ev.append((t0 + int(float(t) * 1020484), a[i], v)); i += 2
    ev.sort()
    res = residency(ao, U)
    # endereço -> unidade, por região: na RAM principal pelo endereço; em $D000 pelo banco ligado
    def owner(pc):
        if pc < 0xC000:
            for nm, (b, n, r) in res.items():
                if r == 'main' and b <= pc < b + n:
                    return nm
        elif pc >= 0xE000:
            for nm, (b, n, r) in res.items():
                if r == 'lchi' and b <= pc < b + n:
                    return nm
        elif pc >= 0xD000:
            want = 'lc%d' % ao.lc_bank
            for nm, (b, n, r) in res.items():
                if r == want:
                    return nm
        return None
    pcs = {}
    loading = False
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
        if ao.motor:
            loading = True
        elif loading:                               # uma carga acabou: o que está onde agora
            loading = False
            res = residency(ao, U)
        else:
            nm = owner(m.pc)
            if nm:
                pcs.setdefault(nm, set()).add(m.pc)
        m.step()
    out = os.path.join(dispkg.USE, 'exec-%s.pkl' % name)
    pickle.dump(pcs, open(out, 'wb'))
    print(out, ' '.join('%s:%d' % (k, len(v)) for k, v in sorted(pcs.items())))


if __name__ == '__main__':
    main()
