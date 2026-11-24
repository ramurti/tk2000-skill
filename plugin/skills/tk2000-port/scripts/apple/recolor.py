#!/usr/bin/env python3
"""Demonstração: reescreve os bytes de uma tela do Apple para que o TK2000 mostre cores parecidas
(verde -> verde, azul -> azul, laranja -> vermelho, violeta -> VIOLETA_TK, branco -> branco).

    recolor.py IN.bin BASE_HEX OUT.bin [violeta=red|cyan|blue]
"""
import sys
sys.path.insert(0, __import__('os').path.dirname(__file__))
from tkview import rows

AP = {(0, 0): 'v', (0, 1): 'g', (1, 0): 'b', (1, 1): 'o'}   # (paleta, x ímpar) -> cor do Apple
TKC = {'g': (0, (1, 0)), 'b': (0, (0, 1)), 'o': (1, (0, 1)), 'c': (1, (1, 0)), 'r': (1, (0, 1))}


def main():
    mem = bytearray(open(sys.argv[1], 'rb').read())
    base = int(sys.argv[2], 16)
    viol = {'red': 'r', 'cyan': 'c', 'blue': 'b'}[sys.argv[4] if len(sys.argv) > 4 else 'red']
    for y, line in rows(mem, base):
        bits, pal = [], []
        for b in line:
            for k in range(7):
                bits.append((b >> k) & 1); pal.append(b >> 7)
        col = []
        for x in range(280):
            if not bits[x]:
                col.append(None)
            elif (x and bits[x - 1]) or (x < 279 and bits[x + 1]):
                col.append('w')
            else:
                c = AP[(pal[x], x & 1)]
                col.append(viol if c == 'v' else c)
        nb, votes = [0] * 280, [[0, 0] for _ in range(40)]
        pairs = []
        for x in range(0, 280, 2):
            cs = [c for c in col[x:x + 2] if c]
            if not cs:
                pairs.append(None); continue
            c = 'w' if 'w' in cs else cs[0]
            pairs.append(c)
            if c != 'w':
                votes[x // 7][TKC[c][0]] += 1
        p7 = [1 if v[1] > v[0] else 0 for v in votes]
        for i, c in enumerate(pairs):
            x = 2 * i
            if c is None:
                continue
            if c == 'w':
                nb[x] = nb[x + 1] = 1; continue
            want_pal, pat = TKC[c]
            if p7[x // 7] != want_pal:   # conflito de paleta no grupo: troca pela cor da mesma posição
                pass
            nb[x], nb[x + 1] = pat
        a0 = base + (y & 7) * 0x400 + ((y >> 3) & 7) * 0x80 + (y >> 6) * 0x28
        for i in range(40):
            mem[a0 + i] = sum(nb[i * 7 + k] << k for k in range(7)) | (p7[i] << 7)
    open(sys.argv[3], 'wb').write(mem)


if __name__ == '__main__':
    main()
