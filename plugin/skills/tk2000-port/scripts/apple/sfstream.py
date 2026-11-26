#!/usr/bin/env python3
"""As imagens em fluxo da rotina rB0 $B229 (sfrelocs.STREAMS): coluna 39 até 0, cada uma da linha
191 até 0; $FE, contagem (0 = 256), valor = repetição; outro byte = um ponto da tela.

decode(data, base, start) -> (tokens, fim): tokens = [(endereço, 'lit', [(linha, coluna)], valor) |
                                                    (endereço, 'run', [(linha, coluna)...], valor)]
recolor(tokens, fn) -> bytes: o fluxo de novo, com cada célula valendo fn(linha, coluna, valor); as
repetições que passam a ter valores diferentes são partidas (trechos curtos viram literais).
"""


def decode(data, base, start):
    cells = [(y, c) for c in range(39, -1, -1) for y in range(191, -1, -1)]
    i, p, toks = 0, start, []
    while i < len(cells):
        v = data[p - base]
        if v == 0xFE:
            n = data[p + 1 - base] or 256
            toks.append((p, 'run', cells[i:i + n], data[p + 2 - base]))
            i += n
            p += 3
        else:
            toks.append((p, 'lit', cells[i:i + 1], v))
            i += 1
            p += 1
    return toks, p


def recolor(toks, fn):
    out = bytearray()
    for p, kind, cl, v in toks:
        vals = [fn(y, c, v) for y, c in cl]
        if kind == 'lit':
            out.append(vals[0])
            continue
        k = 0
        while k < len(vals):                    # partes iguais seguidas
            j = k
            while j < len(vals) and vals[j] == vals[k]:
                j += 1
            n = j - k
            if n <= 3 and vals[k] != 0xFE:
                out += bytes(vals[k:j])
            else:
                while n > 0:
                    m = min(n, 256)
                    out += bytes([0xFE, m & 0xFF, vals[k]])
                    n -= m
            k = j
    return bytes(out)
