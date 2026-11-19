#!/usr/bin/env python3
"""Um disco de jogo para a interface de disco do TK2000 (140K, ordem de setores do DOS 3.3, como o
.dsk do Apple), do porte de Kung Fu Master. Trilha 0, setores físicos 0-3: src/boot.s (o carregador
de boot); a partir da trilha 1, uma página por setor (em ordem de setor físico): o programa, depois
a segunda parte opcional para a RAM sob a ROM. Dê boot com CALL 49408.

    mkdsk.py OUT.dsk PROGRAM.bin@ADDR START [HIGH.bin@ADDR]

ADDR (hex, alinhado em página) é onde cada parte é carregada, START para onde o carregador salta.
"""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
B = os.path.join(ROOT, 'build')
P2D = [0, 7, 14, 6, 13, 5, 12, 4, 11, 3, 10, 2, 9, 1, 8, 15]     # setor físico -> no arquivo


def pages(data):
    data += bytes(-len(data) % 256)
    return [data[i:i + 256] for i in range(0, len(data), 256)]


def part(arg):
    path, addr = arg.rsplit('@', 1)
    addr = int(addr, 16)
    assert addr & 0xFF == 0, '%s: o endereço precisa ser alinhado em página' % arg
    return pages(open(path, 'rb').read()), addr >> 8


def main():
    if len(sys.argv) not in (4, 5):
        sys.exit(__doc__)
    out = sys.argv[1]
    low, low_first = part(sys.argv[2])
    start = int(sys.argv[3], 16)
    high, high_first = part(sys.argv[4]) if len(sys.argv) == 5 else ([], 0)
    assert low_first >= 0x08 and low_first + len(low) <= 0xC0, 'o programa: $0800-$BFFF'
    assert not high or (high_first >= 0xC2 and high_first + len(high) <= 0x100), \
        'a segunda parte: $C200-$FFFF ($C100-$C1FF é a ROM da interface)'
    data = low + high
    assert len(data) <= 34 * 16, 'mais de 34 trilhas'
    subprocess.run(['ca65', '-D', 'LOW_FIRST=$%02X' % low_first, '-D', 'LOW_PAGES=%d' % len(low),
                    '-D', 'HIGH_FIRST=$%02X' % high_first, '-D', 'HIGH_PAGES=%d' % len(high),
                    '-D', 'START=$%04X' % start,
                    '-o', os.path.join(B, 'boot.o'), '-l', os.path.join(B, 'boot.lst'),
                    os.path.join(ROOT, 'src', 'boot.s')], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'cfg', 'raw.cfg'), '-o', os.path.join(B, 'boot.bin'),
                    os.path.join(B, 'boot.o')], check=True)
    boot = open(os.path.join(B, 'boot.bin'), 'rb').read()
    assert len(boot) <= 4 * 256
    dsk = bytearray(35 * 16 * 256)

    def put(track, phys, page):
        off = (track * 16 + P2D[phys]) * 256
        dsk[off:off + len(page)] = page
    for p, page in enumerate(pages(bytes(boot))):
        put(0, p, page)
    for k, page in enumerate(data):
        put(1 + k // 16, k % 16, page)
    open(out, 'wb').write(dsk)
    print('%s: carregador de boot %d bytes, %d páginas nas trilhas 1-%d' % (out, len(boot), len(data), (len(data) + 15) // 16))


if __name__ == '__main__':
    main()
