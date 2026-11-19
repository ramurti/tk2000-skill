#!/usr/bin/env python3
"""Os registros de objetos do jogo (D $91EF lê um: a tabela de 106 registros em D $9329 (bytes
baixos) / $9393 (bytes altos), indexada por Y) e os endereços dentro deles.

Um registro: uma máscara de campos de 16 bits, um byte de flags, depois os campos cujo bit está ligado:
  bit 0-5: um byte cada        bit 6: ponteiro da lo-list, ponteiro da hi-list (quadros: os bytes
  bit 7: número de quadros - 1 ($A3)   baixos e altos dos gráficos de cada quadro)
  bit 8, 9: um byte cada       bit 10: dois bytes  bit 11: ponteiro do tratador (código)
  bit 12-14: um byte cada      bit 15: dois bytes
Registros em $AB00-$BAFF pertencem ao overlay carregado ali: são lidos em cada overlay.

No TK2000 os bytes altos dentro de $4000-$5FFF / $A000-$BFFF (bytes altos de ponteiros nos
registros, bytes altos de quadros nas hi-lists) precisam ser relocados: hi_bytes() os lista.

    records.py           (imprime os registros e o que o relocs.py ainda não tem)
"""
from disa2 import units

SIZES = [1, 1, 1, 1, 1, 1, 4, 1, 1, 1, 2, 2, 1, 1, 1, 2]
TAB_LO, TAB_HI, COUNT = 0x9329, 0x9393, 106


def moved(v):
    return 0x40 <= v < 0x60 or 0xA0 <= v < 0xC0


def file_at(u, name, a):
    base, data = u[name]
    return data[a - base] if base <= a < base + len(data) else None


# qual overlay contém os registros em $AB00-$BAFF (pelo código dos overlays e pelos andares)
OWNER = {}
for _f, _ks in (('G', range(33, 40)), ('J', [45, 48, 49, 50] + list(range(64, 71))),
                ('K', range(52, 59)), ('L', range(71, 91)), ('M', range(91, 106))):
    for _k in _ks:
        OWNER[_k] = _f


def parse(u, f, rec):
    """o registro em rec no arquivo f: (mask, {bit: field address}, fim)"""
    rd = lambda a: file_at(u, f, a)            # noqa: E731
    mask = rd(rec) | rd(rec + 1) << 8
    a = rec + 3
    fields = {}
    for bit in range(16):
        if mask >> bit & 1:
            fields[bit] = a
            a += SIZES[bit]
    return mask, fields, a


def records(u=None):
    """[(index, file, address, mask, fields)] dos registros reais (a tabela também aponta para
    bytes que não são registro: entrada 17 dentro do registro 16, entradas 103-105 depois dos registros de M)"""
    u = u or units()
    d0, d = u['D']
    out = []
    for k in range(COUNT):
        rec = d[TAB_LO - d0 + k] | d[TAB_HI - d0 + k] << 8
        if rec == 0 or k in (17, 103, 104, 105):
            continue
        f = 'D' if d0 <= rec < d0 + len(d) else OWNER[k]
        mask, fields, _ = parse(u, f, rec)
        out.append((k, f, rec, mask, fields))
    return out


def hi_bytes(u=None):
    """{file: {address: why}} dos bytes altos nos registros (e na tabela de registros)
    que estão dentro das áreas trocadas"""
    u = u or units()
    out = {}

    def add(f, a, why):
        v = file_at(u, f, a)
        assert v is not None, (f, hex(a), why)
        if moved(v):
            out.setdefault(f, {})[a] = why
    for k, f, rec, mask, fields in records(u):
        add('D', TAB_HI + k, 'entrada %d da tabela de registros' % k)
        rd = lambda a: file_at(u, f, a)        # noqa: E731
        if 6 in fields:
            p = fields[6]
            add(f, p + 1, 'registro %d ponteiro da lo-list de quadros' % k)
            add(f, p + 3, 'registro %d ponteiro da hi-list de quadros' % k)
            lo_ptr = rd(p) | rd(p + 1) << 8
            hi_ptr = rd(p + 2) | rd(p + 3) << 8
            n = rd(fields[7]) + 1 if 7 in fields else 1
            if 0 < hi_ptr - lo_ptr <= 16:       # a lo-list logo antes da hi-list: o tamanho
                n = max(n, hi_ptr - lo_ptr)     # dela (alguns números são definidos pelo código)
            g = f if file_at(u, f, hi_ptr) is not None else 'D'
            for j in range(n):
                add(g, hi_ptr + j, 'registro %d quadro %d byte alto dos gráficos' % (k, j))
        if 11 in fields:
            add(f, fields[11] + 1, 'registro %d ponteiro do tratador' % k)
    return out


if __name__ == '__main__':
    import relocs
    u = units()
    hb = hi_bytes(u)
    for f in sorted(hb):
        missing = sorted(a for a in hb[f] if a not in relocs.HI.get(f, []))
        known = len(hb[f]) - len(missing)
        print('%s: %d bytes altos, %d já no relocs.py, novos: %s' % (
            f, len(hb[f]), known, ' '.join('$%04X' % a for a in missing)))
    for f in sorted(relocs.HI):
        extra = [a for a in relocs.HI[f] if a not in hb.get(f, {})]
        print('%s: no relocs.py mas não vindos dos registros: %s' % (f, ' '.join('$%04X' % a for a in extra)))
