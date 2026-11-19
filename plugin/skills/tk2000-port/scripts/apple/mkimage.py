#!/usr/bin/env python3
"""Monta a imagem de memória do TK2000 e a fita dela.

1. Dá boot no disco original (tools/a2boot.py) até o jogo começar ($AB00): essa memória e
   os registradores são o ponto de partida da imagem, relocados (disa2.reloc).
2. Põe por cima a versão TK2000 do código (build/tk/*.bin: relocado, E/S do Apple
   corrigida; a calibração do joystick de G trocada pela carta, src/letter.s), a
   cópia da fonte de números aleatórios (relocs.RNG_*), src/tk.s em $5B00.
3. Compacta (tools/lz.py) na RAM sob a ROM ($C200-$FFFF; $C100-$C1FF mostra a ROM da
   interface de disco quando o cartucho dela está encaixado): os overlays e imagens
   que o jogo carrega do disco durante a partida, e a memória baixa ($0000-$07FF: o carregador
   da fita a usa, o Start a descompacta); depois deles os efeitos sonoros (src/sfx.s).

Grava build/kungfu.bin ($0800-$9FFF), build/high.bin ($C200-...), src/dir.inc, e com
a ferramenta de fita build/kungfu.ct2.

    mkimage.py
"""
import os
import subprocess
import sys

import a2boot
import lz
import relocs
from disa2 import reloc
from py65.devices.mpu6502 import MPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
B = os.path.join(ROOT, 'build')
HIGH = 0xC200
# arquivos que o jogo carrega durante a partida (N: o menu de opções; G: cada vida; I-M: os andares;
# F: o painel de placar). H nunca é carregado; O (os créditos, ctrl-J: 4,8K compactado) não cabe.
PACKED = ['N', 'G', 'I', 'J', 'K', 'L', 'M', 'F']


def boot():
    dsk = open(os.path.join(ROOT, 'reference', 'kung_fu_master.dsk'), 'rb').read()
    ap = a2boot.Apple(dsk)
    n = dsk[0]
    for p in range(n):
        ap.ram[0x800 + p * 256:0x900 + p * 256] = dsk[a2boot.P2D[p] * 256:a2boot.P2D[p] * 256 + 256]
    ap.ram[0x2B] = 0x60
    for k, v in enumerate(a2boot.WRITE_TABLE):
        ap.ram[0x02D6 + v] = k
    ap.ram[0x3D] = n
    mpu = MPU(memory=a2boot.Mem(ap), pc=0x0801)
    ap.mpu = mpu
    ap.fire_from = 1 << 62
    mpu.x = 0x60
    mpu.sp = 0xFF
    while mpu.pc != 0xAB00:
        if mpu.processorCycles >= 2_000_000 and ap.key == 0:
            ap.key = 0xA0                       # (a etapa do título espera uma tecla)
        mpu.step()
    return bytes(ap.ram[:0xC000]), {'A': mpu.a, 'X': mpu.x, 'Y': mpu.y, 'P': mpu.p, 'SP': mpu.sp}


LETTER_END = 0x4CDF            # a calibração de G e o texto dela terminam aqui (Apple $ACDF)


def tkbin(name):
    data = open(os.path.join(B, 'tk', name + '.bin'), 'rb').read()
    if name == 'G':                             # a entrada dele: a carta (src/letter.s)
        subprocess.run(['ca65', '-D', 'G_END=$%04X' % LETTER_END, '-o', os.path.join(B, 'letter.o'),
                        '-l', os.path.join(B, 'letter.lst'), os.path.join(ROOT, 'src', 'letter.s')], check=True)
        subprocess.run(['ld65', '-C', os.path.join(ROOT, 'cfg', 'raw.cfg'), '-o', os.path.join(B, 'letter.bin'),
                        os.path.join(B, 'letter.o')], check=True)
        letter = open(os.path.join(B, 'letter.bin'), 'rb').read()
        room = LETTER_END - 0x4B00
        assert data[room:room + 4] == bytes([0xA9, 0xDF, 0x95, 0xC3]), 'G: não é o código depois da calibração'
        data = letter + bytes(room - len(letter)) + data[room:]
    return data


def main():
    snap, regs = boot()
    mem = bytearray(0x10000)
    for a in range(0xC000):
        mem[reloc(a)] = snap[a]
    if mem[0xF4] == 0x20:
        mem[0xF4] = 0x80                        # a página sendo desenhada (relocs.PG)
    # o ponteiro do alto-falante do som: o original o define ($C030, D $8820) quando uma partida começa,
    # então a demo antes da primeira partida ficaria sem os efeitos sonoros (src/tk.s)
    mem[0xF9:0xFB] = b'\x30\xC0'
    # os limites do joystick (x $02A4-$02A7, y $02A8-$02AB: a calibração de G, pontos médios das
    # leituras do centro e dos cantos): uma tecla na tela de calibração a pula e os deixa em 0,
    # então nenhuma direção funciona; definidos aqui para as setas do src/tk.s (0, 45, 127)
    mem[0x02A4:0x02AC] = bytes([22, 45, 86, 0xFF, 22, 45, 86, 0xFF])
    mem[0x0400:0x2000] = tkbin('C')
    d = tkbin('D')
    mem[0x6000:0xA000] = d[:0x4000]
    mem[0x4000:0x4000 + len(d) - 0x4000] = d[0x4000:]
    mem[0x4B00:0x4B00 + len(tkbin('G'))] = tkbin('G')
    d_orig = open(os.path.join(B, 'files', 'D_6000.bin'), 'rb').read()
    mem[relocs.RNG_TO:relocs.RNG_TO + relocs.RNG_LEN] = relocs.rng_copy(d_orig)

    # os arquivos compactados
    import glob
    blob = bytearray()
    names, srcs, dsts = [], [], []
    low = lz.compress(bytes(mem[0:0x0800]))
    low_at = HIGH
    blob += low
    for nm in PACKED:
        f = glob.glob(os.path.join(B, 'files', nm + '_*.bin'))[0]
        base = int(f.split('_')[-1][:4], 16)
        data = tkbin(nm) if os.path.exists(os.path.join(B, 'tk', nm + '.bin')) else open(f, 'rb').read()
        packed = lz.compress(data)
        assert lz.decompress(packed) == data
        names.append(ord(nm))
        srcs.append(HIGH + len(blob))
        dsts.append(reloc(base))
        blob += packed
        print('%s: $%04X, %5d bytes compactados em %5d' % (nm, reloc(base), len(data), len(packed)))
    # os efeitos sonoros (src/sfx.s), logo depois dos arquivos compactados
    sfx_at = HIGH + len(blob)
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'midi2tk.py'),
                    os.path.join(ROOT, 'reference', 'music.mid'), os.path.join(ROOT, 'src', 'music.inc'),
                    '12'], check=True)
    subprocess.run([sys.executable, os.path.join(ROOT, 'tools', 'mkstairs.py'),
                    os.path.join(ROOT, 'src', 'stairs.inc')], check=True)
    subprocess.run(['ca65', '-D', 'SFX_AT=$%04X' % sfx_at, '-o', os.path.join(B, 'sfx.o'),
                    '-l', os.path.join(B, 'sfx.lst'), os.path.join(ROOT, 'src', 'sfx.s')], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'cfg', 'raw.cfg'), '-o', os.path.join(B, 'sfx.bin'),
                    os.path.join(B, 'sfx.o')], check=True)
    blob += open(os.path.join(B, 'sfx.bin'), 'rb').read()
    end = HIGH + len(blob)
    print('src/sfx.s: $%04X-$%04X' % (sfx_at, end - 1))
    print('RAM sob a ROM: $%04X-$%04X (%d bytes livres)' % (HIGH, end - 1, 0x10000 - end))
    assert end <= 0x10000, 'os arquivos compactados não cabem'
    with open(os.path.join(ROOT, 'src', 'dir.inc'), 'w') as o:
        o.write('; gerado por tools/mkimage.py\n')
        o.write('DIR_COUNT   = %d\n' % len(names))
        o.write('.define DIR_NAMES %s\n' % ', '.join('$%02X' % n for n in names))
        o.write('.define DIR_SRC %s\n' % ', '.join('$%04X' % a for a in srcs))
        o.write('.define DIR_DST %s\n' % ', '.join('$%04X' % a for a in dsts))
        o.write('LOW_PACKED  = $%04X\n' % low_at)
        o.write('SFX_AT      = $%04X\n' % sfx_at)
        for r, v in regs.items():
            o.write('START_%-4s = $%02X\n' % (r, v))
    subprocess.run(['ca65', '-o', os.path.join(B, 'tk.o'), '-l', os.path.join(B, 'tk.lst'),
                    os.path.join(ROOT, 'src', 'tk.s')], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'cfg', 'raw.cfg'), '-o', os.path.join(B, 'tk.bin'),
                    os.path.join(B, 'tk.o')], check=True)
    tk = open(os.path.join(B, 'tk.bin'), 'rb').read()
    assert 0x5B00 + len(tk) <= relocs.RNG_TO, 'src/tk.s tem %d bytes, passa de $%04X' % (len(tk), relocs.RNG_TO)
    print('src/tk.s: $5B00-$%04X' % (0x5B00 + len(tk) - 1))
    mem[0x5B00:0x5B00 + len(tk)] = tk
    mem[HIGH:end] = blob
    open(os.path.join(B, 'kungfu.bin'), 'wb').write(mem[0x0800:0xA000])
    open(os.path.join(B, 'high.bin'), 'wb').write(mem[HIGH:end])
    open(os.path.join(B, 'image.bin'), 'wb').write(mem)


if __name__ == '__main__':
    sys.exit(main())
