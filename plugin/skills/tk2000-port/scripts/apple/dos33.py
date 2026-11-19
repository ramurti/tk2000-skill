#!/usr/bin/env python3
"""Lista o catálogo de uma imagem de disco DOS 3.3 e extrai os arquivos dela (arquivos binários: o
cabeçalho de 4 bytes dá o endereço de carga e o tamanho) para um diretório.
    dos33.py DISK.dsk OUTDIR"""
import os
import sys

d = open(sys.argv[1], 'rb').read()
out = sys.argv[2]
os.makedirs(out, exist_ok=True)


def sec(t, s):
    return d[(t * 16 + s) * 256:(t * 16 + s + 1) * 256]


def file_data(t, s):
    data = b''
    while t:
        ts = sec(t, s)
        for k in range(122):
            ft, fs = ts[12 + 2 * k], ts[13 + 2 * k]
            data += sec(ft, fs) if ft or fs else bytes(256)
        t, s = ts[1], ts[2]
    return data


TYPES = {0: 'T', 1: 'I', 2: 'A', 4: 'B'}
v = sec(17, 0)
t, s = v[1], v[2]
while t:
    c = sec(t, s)
    for e in range(7):
        x = c[11 + e * 35:46 + e * 35]
        if x[0] in (0, 0xFF):
            continue
        name = bytes(b & 0x7F for b in x[3:33]).decode().rstrip()
        typ = TYPES.get(x[2] & 0x7F, '?')
        data = file_data(x[0], x[1])
        if typ == 'B':
            addr, n = data[0] | data[1] << 8, data[2] | data[3] << 8
            body = data[4:4 + n]
            print('%-4s B  $%04X-$%04X  %5d bytes  (%d sectors)' % (name, addr, addr + n - 1, n, x[33]))
            open(os.path.join(out, '%s_%04X.bin' % (name, addr)), 'wb').write(body)
        else:
            n = data[0] | data[1] << 8
            print('%-4s %s  %d bytes' % (name, typ, n))
            open(os.path.join(out, name + '.' + typ), 'wb').write(data[2:2 + n] if typ == 'A' else data)
    t, s = c[1], c[2]
