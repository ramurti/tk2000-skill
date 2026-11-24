#!/usr/bin/env python3
"""O disco do Sky Fox para a interface de disco do TK2000 (build/skyfox-tk.dsk; boot: CALL 49408).

- As trilhas dos pacotes (tools/dispkg.py) ficam nos mesmos lugares, com a versão TK2000 deles
  (build/tk/tNN.bin, página n = setor DOS 15-n): o carregador do jogo as lê pelo número. A trilha 18
  (figuras do banco 1 do voo A) vai com as 12 páginas com dados juntas no começo (sfrelocs.fig_map).
- A memória do jogo logo depois da carga inicial (o estado do AppleWin aos 14 s, traduzido para o
  TK2000 como no lockstep, mais a camada do TK2000) é lida pelo src/boot.s: páginas zeradas, páginas
  iguais às dos pacotes (lidas das trilhas deles) e o resto nas trilhas livres (0-6, 26-28).

    mksfdisk.py [SNAP.yaml]          (padrão: build/aw/res/snap-14.yaml)
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import dispkg, sfboot, sfrelocs
import sflockstep as L
from sftaint import Ap
from a2boot import Mem
from py65.devices.mpu6502 import MPU

ROOT = dispkg.ROOT
B = os.path.join(ROOT, 'build')
P2D = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]   # setor físico -> setor DOS (no .dsk)
FREE = [0, 1, 2, 3, 4, 5, 6, 26, 27, 28]                         # trilhas que o jogo não lê depois da carga inicial
BOOT_SECTORS = 6


def compact18(tk):
    """a trilha 18 com as páginas com dados (0-6, 11-15) juntas no começo"""
    pages = [tk[n * 256:n * 256 + 256] for n in list(range(7)) + list(range(11, 16))]
    return b''.join(pages) + bytes(0x1000 - len(pages) * 256)


def main():
    snap = sys.argv[1] if len(sys.argv) > 1 else os.path.join(B, 'aw', 'res', 'snap-14.yaml')
    orig = open(dispkg.DSK, 'rb').read()
    U = L.Units(orig)
    dsk = bytearray(orig)

    def put_track(t, data):                     # página n -> setor DOS 15 - n
        for n in range(16):
            o = (t * 16 + 15 - n) * 256
            dsk[o:o + 256] = data[n * 256:n * 256 + 256]
    tracks = {}
    for nm, (t, base, region, runs) in dispkg.PKGS.items():
        if isinstance(t, tuple):
            continue
        data = compact18(U.tk[nm]) if nm == 't18' else U.tk[nm]
        if t in tracks and tracks[t] != data:
            sys.exit('trilha %d com duas versões' % t)
        tracks[t] = data
        put_track(t, data)

    # a imagem: o estado traduzido como no lockstep, mais a camada
    ao = Ap(orig)
    mo = MPU(memory=Mem(ao), pc=0)
    ao.mpu = mo
    sfboot.load_applewin(ao, snap)
    pt = L.Port(orig)
    pt.mpu = MPU(memory=Mem(pt), pc=0)
    L.build_port(ao, pt, U)
    for x, b in sfrelocs.LAYER.items():
        for k, v in enumerate(b):
            pt.write(x + k, v)
    img = {p: bytes(pt.ram[p * 256:p * 256 + 256]) for p in range(0xC0)}
    img.update({p: bytes(pt.hi[(p - 0xC0) * 256:(p - 0xC0) * 256 + 256]) for p in range(0xD0, 0x100)})

    where = {}                                  # conteúdo -> (trilha, setor físico) nas trilhas dos pacotes
    for t, data in tracks.items():
        for n in range(16):
            where.setdefault(data[n * 256:n * 256 + 256], (t, P2D.index(15 - n)))
    plan = {}                                   # trilha -> [página de destino por setor físico]
    zeros, free_pages = [], []
    for p, b in sorted(img.items()):
        dest = {0: 0xC8, 1: 0xC9}.get(p, p)     # página zero e pilha: para o buffer
        if p > 1 and not any(b):
            zeros.append(p)
        elif p > 1 and b in where:
            t, phys = where[b]
            plan.setdefault(t, [0] * 16)[phys] = dest
        else:
            free_pages.append((dest, b))
    slots = [(t, phys) for t in FREE for phys in range(16) if not (t == 0 and phys < BOOT_SECTORS)]
    if len(free_pages) > len(slots):
        sys.exit('%d páginas para %d setores livres' % (len(free_pages), len(slots)))
    for (dest, b), (t, phys) in zip(free_pages, slots):
        o = (t * 16 + P2D[phys]) * 256
        dsk[o:o + 256] = b
        plan.setdefault(t, [0] * 16)[phys] = dest
    order = sorted(plan)

    regs = dict(NT=len(order), NZ=len(zeros), HT_END=ao.ht, REG_PC=L.pcmap(mo.pc), REG_A=mo.a,
                REG_X=mo.x, REG_Y=mo.y, REG_P=mo.p, REG_S=mo.sp)
    open(os.path.join(B, 'plan.inc'), 'w').write(''.join('%-8s = $%X\n' % kv for kv in regs.items()))
    rows = ['TRACKS: .byte   ' + ','.join('%d' % t for t in order),
            'ZEROS:  .byte   ' + ','.join('$%02X' % p for p in zeros),
            'PLAN:']
    rows += ['        .byte   ' + ','.join('$%02X' % d for d in plan[t]) + '   ; trilha %d' % t for t in order]
    open(os.path.join(B, 'plantab.inc'), 'w').write('\n'.join(rows) + '\n')
    o, bb = os.path.join(B, 'boot.o'), os.path.join(B, 'boot.bin')
    subprocess.run(['ca65', '-I', B, os.path.join(ROOT, 'src', 'boot.s'), '-o', o,
                    '-l', os.path.join(B, 'boot.lst')], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'src', 'dis', 'raw.cfg'), o, '-o', bb], check=True)
    boot = open(bb, 'rb').read()
    assert len(boot) <= BOOT_SECTORS * 256 and boot[0] == BOOT_SECTORS
    boot += bytes(BOOT_SECTORS * 256 - len(boot))
    for p in range(BOOT_SECTORS):
        o = (0 * 16 + P2D[p]) * 256
        dsk[o:o + 256] = boot[p * 256:p * 256 + 256]
    out = os.path.join(B, 'skyfox-tk.dsk')
    open(out, 'wb').write(dsk)
    print('%s: carregador %d bytes; %d trilhas lidas no boot, %d páginas zeradas, %d nas trilhas dos '
          'pacotes, %d nas livres; o jogo começa em $%04X' % (
              out, len(boot), len(order), len(zeros), sum(1 for t in plan for d in plan[t] if d) - len(free_pages),
              len(free_pages), regs['REG_PC']))


if __name__ == '__main__':
    main()
