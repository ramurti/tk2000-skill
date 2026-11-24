#!/usr/bin/env python3
"""Monta a camada do TK2000 (src/tklayer.s, $6200-$64FF) em build/tk/layer.bin e preenche as cópias
de figuras com os bytes originais do disco (FIGX = t13 $DDF9-$DE09, FIGCOPY = t14 $9E0C-$9E2B).

    mklayer.py
"""
import os, subprocess, sys
sys.path.insert(0, os.path.dirname(__file__))
import dispkg

ROOT = dispkg.ROOT
BASE = 0x6200


def main():
    out = os.path.join(ROOT, 'build', 'tk')
    os.makedirs(out, exist_ok=True)
    o, b = os.path.join(out, 'layer.o'), os.path.join(out, 'layer.bin')
    subprocess.run(['ca65', os.path.join(ROOT, 'src', 'tklayer.s'), '-o', o,
                    '-l', os.path.join(out, 'layer.lst')], check=True)
    subprocess.run(['ld65', '-C', os.path.join(ROOT, 'src', 'dis', 'raw.cfg'), o, '-o', b], check=True)
    d = bytearray(open(b, 'rb').read())
    assert len(d) == 0x300, hex(len(d))
    dsk = open(dispkg.DSK, 'rb').read()
    t13, t14 = dispkg.package(dsk, 13), dispkg.package(dsk, 14)
    d[0x64A0 - BASE:0x64A0 - BASE + 17] = t13[0xDF9:0xE0A]
    d[0x64C0 - BASE:0x64C0 - BASE + 32] = t14[0xE0C:0xE2C]
    open(b, 'wb').write(d)
    print('camada: %d bytes em $%04X-$%04X -> %s' % (len(d), BASE, BASE + len(d) - 1, b))


if __name__ == '__main__':
    main()
