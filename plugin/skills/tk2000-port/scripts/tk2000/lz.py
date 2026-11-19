#!/usr/bin/env python3
"""Um formato LZ pequeno para os overlays guardados na RAM sob a ROM do TK2000 (src/tk.s, Unlz).

Um byte de flags anuncia os próximos 8 itens (bit 0 primeiro): 0 = um byte literal, 1 = uma
coincidência de dois bytes: os 8 bits baixos da distância, depois (4 bits altos da distância) << 4 |
(tamanho - 3). Distância de 1..4095 para trás a partir da saída, tamanho 3..18. Uma coincidência com
distância 0 encerra os dados.
"""

MAXOFF, MINLEN, MAXLEN = 4095, 3, 18


def compress(data):
    out = bytearray()
    items = []
    i, n = 0, len(data)
    heads = {}
    while i < n:
        best_len, best_off = 0, 0
        key = bytes(data[i:i + MINLEN])
        if len(key) == MINLEN:
            for j in reversed(heads.get(key, [])):
                if i - j > MAXOFF:
                    break
                ln = 0
                while ln < MAXLEN and i + ln < n and data[j + ln] == data[i + ln]:
                    ln += 1
                if ln > best_len:
                    best_len, best_off = ln, i - j
                    if ln == MAXLEN:
                        break
        step = best_len if best_len >= MINLEN else 1
        if best_len >= MINLEN:
            items.append((best_off, best_len))
        else:
            items.append(data[i])
        for k in range(i, i + step):
            heads.setdefault(bytes(data[k:k + MINLEN]), []).append(k)
        i += step
    items.append((0, MINLEN))                   # o fim
    for g in range(0, len(items), 8):
        group = items[g:g + 8]
        flags = 0
        body = bytearray()
        for b, it in enumerate(group):
            if isinstance(it, tuple):
                flags |= 1 << b
                off, ln = it
                body += bytes([off & 0xFF, (off >> 8) << 4 | (ln - MINLEN)])
            else:
                body.append(it)
        out.append(flags)
        out += body
    return bytes(out)


def decompress(comp):
    out = bytearray()
    i = 0
    while True:
        flags = comp[i]
        i += 1
        for b in range(8):
            if flags >> b & 1:
                lo, hi = comp[i], comp[i + 1]
                i += 2
                off = lo | (hi >> 4) << 8
                if off == 0:
                    return bytes(out)
                for _ in range((hi & 15) + MINLEN):
                    out.append(out[-off])
            else:
                out.append(comp[i])
                i += 1


if __name__ == '__main__':
    import sys
    for f in sys.argv[1:]:
        d = open(f, 'rb').read()
        c = compress(d)
        assert decompress(c) == d
        print('%-40s %6d -> %6d' % (f, len(d), len(c)))
