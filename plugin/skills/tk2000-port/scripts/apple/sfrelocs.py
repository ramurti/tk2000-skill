#!/usr/bin/env python3
"""O que muda nos bytes do Sky Fox para o mapa de memória do TK2000 (usado por dispkg.py --tk e
pelo lockstep).

O TK2000 mostra a página 2 de hi-res em $A000, o Apple em $4000: o porte troca as duas áreas de 8K
(reloc). Operandos de código acompanham os rótulos ao remontar; os bytes abaixo montam endereços em
tempo de execução (achados com tools/sftaint.py e conferidos com o lockstep):

PG: deslocamento da página de desenho. A variável $20 vale $00 (página 1) ou $20 (página 2) e é somada
    aos bytes altos da tabela de linhas; no TK2000 a página 2 está $80 acima: eor #$20 -> eor #$80.
HI: bytes altos de endereços dentro das duas áreas (imediatos, tabelas): XOR $E0.
CODE: trocas de instrução (endereço: (bytes originais, bytes novos)). A variável $20 também é
    usada como índice das listas por página ($0200/$0240): asl a dava $00/$40, com $80 lsr a dá o
    mesmo; e adc $20 / adc $20 (+$00/+$40) vira nop / adc PAGEIDX,x (X já é 0 ou 1 ali).
LAYER: bytes que o porte acrescenta (endereço no TK2000: bytes), na área da camada do TK2000.
HOLES: modelos do código dos buracos da tela (8 bytes cada: JSR/JMP para o próximo buraco...),
    copiados pelo jogo para os buracos da página 1; os operandos absolutos nas duas áreas: XOR $E0.
FIGTAB: tabelas de ponteiros de figuras (lo, hi). Figuras do banco 1 ($D000-$DFFF) vão para $C200
    e, na trilha 13, o resto para FIG_HI (fig_map, por trilha); figuras nas duas áreas: XOR $E0.
"""


def reloc(a):
    """O endereço no TK2000 de um endereço da RAM principal do Apple"""
    return a ^ 0xE000 if 0x4000 <= a < 0x6000 or 0xA000 <= a < 0xC000 else a


PG = {                                  # unidade: endereços de operandos $20 que viram $80
    'r40': [0x55FB],
    't22': [0xA428],                    # copia a página 2 para a página 1: linha + $20
    't29': [0xF57D, 0xF58F, 0xF8B1],    # $F8B1: linha + $20 (desenha nas duas páginas)
}

HI = {                                  # unidade: endereços de bytes altos (XOR $E0)
    't22': [0xA21B, 0xA21D],            # 2 ponteiros (lo, hi) para o próprio t22, copiados para operandos em $A34C/$A362
    'rB0': [0xB124],                    # lda #$B1 / sta $B116: JMP reescrito em $B114
    't20': [0xA17B,                     # lda #$AE / sta $A181 (operando de lda $AExx,y)
            0xA2CB, 0xA2DA, 0xA30D, 0xA31C, 0xA383, 0xA392, 0xA3E3, 0xA3F2, 0xA426, 0xA435,
            0xA542, 0xA63A, 0xA65D, 0xA6A0, 0xA6EF, 0xA717,   # lda #hi / sta $31: ponteiros $30/$31
            0xA729, 0xA730]             # ldy #hi / jsr $A952 (ponteiro em X/Y)
           + list(range(0xA81F, 0xA82E))   # tabela $A810 (lo) / $A81F (hi), 15 entradas
           + list(range(0xA90E, 0xA913))   # tabela $A909 / $A90E, 5 entradas
           + list(range(0xAA04, 0xAA0A))   # tabela $A9FE / $AA04, 6 entradas
           + list(range(0xAB80, 0xABAD, 4)),   # registros de 4 bytes: o 4o é o byte alto (página 2)
    't21': [0x72A7, 0x72A8, 0x72AB, 0x72AC, 0x72AD, 0x72AE, 0x72AF],   # tabela de saltos $7296/$72A4 (JMP em $7285)
}

import os as _os
_DSK = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'reference',
                     'Skyfox_1984_Electronic_Arts_cr_Black_Bag.dsk')


def _track(t):
    d = open(_DSK, 'rb').read()
    return b''.join(d[t * 4096 + (15 - n) * 256:t * 4096 + (16 - n) * 256] for n in range(16))


PAGEIDX = 0x64FE                        # provisório: a área da camada do TK2000 ainda não está fechada
FIGCOPY = 0x64C0                        # a figura 17 do t14 aponta para $9E0C, dentro da própria tabela
LAYER = {                               # de bytes altos: desenha os bytes originais dela
    PAGEIDX: bytes([0x00, 0x40]),       # índice das listas por página
    FIGCOPY: _track(14)[0xE0C:0xE2C],   # cópia dos 32 bytes originais de $9E0C
}
FIGSPECIAL = {('t14', 0x9E0C): FIGCOPY}

CODE = {
    't8': {0x801B: (b'\x0A', b'\x4A')},  # asl a -> lsr a
    't9': {0x9100: (b'\x0A', b'\x4A')},  # asl a -> lsr a
    'rB0': {
        0xB3D6: (b'\x0A', b'\x4A'),                     # asl a -> lsr a
        0xB7FF: (b'\x65\x20\x65\x20', bytes([0xEA, 0x7D, PAGEIDX & 0xFF, PAGEIDX >> 8])),  # adc $20 x2 -> nop / adc PAGEIDX,x
    },
}

HOLES = {
    't32': (0xEC00, 0xF000),            # voo A usa $EC00-$EDFF, voo B $EE00-$EFFF
}
LEN = {'imp': 1, 'acc': 1, 'imm': 2, 'zpg': 2, 'zpx': 2, 'zpy': 2, 'inx': 2, 'iny': 2, 'rel': 2,
       'abs': 3, 'abx': 3, 'aby': 3, 'ind': 3}


def snippet(b):
    """os bytes de um trecho de código de buraco (8 bytes) com os operandos absolutos nas duas áreas
    relocados. O código pode começar depois de 1 ou 2 bytes de dados: vale o primeiro deslocamento
    (0, 1, 2) em que as instruções decodificam sem erro até um JMP ou RTS"""
    from py65.devices.mpu6502 import MPU
    ops = getattr(snippet, 'ops', None) or MPU().disassemble
    snippet.ops = ops

    def parse(start):
        k, ins = start, []
        while k < len(b):
            mn, mode = ops[b[k]]
            n = LEN[mode]
            if mn == '???' or k + n > len(b):
                return None
            ins.append((k, n))
            k += n
            if mn in ('JMP', 'RTS', 'RTI'):
                return ins
        return None
    for start in (0, 1, 2):
        ins = parse(start)
        if ins:
            break
    else:
        return bytes(b)
    out = bytearray(b)
    for i, (k, n) in enumerate(ins):
        if n == 2 and b[k] == 0xA9 and i + 1 < len(ins) and b[ins[i + 1][0]:ins[i + 1][0] + 2] == b'\x85\x31' \
                and (0x40 <= b[k + 1] < 0x60 or 0xA0 <= b[k + 1] < 0xC0):
            out[k + 1] ^= 0xE0                      # lda #hi / sta $31: o ponteiro $30/$31 ($ECF9 no t32)
        if n == 3:
            v = b[k + 1] | b[k + 2] << 8
            if 0x4000 <= v < 0x6000 or 0xA000 <= v < 0xC000:
                out[k + 2] ^= 0xE0
    return bytes(out)


FIG_HI = 0x6000                         # o resto das figuras da trilha 13 (provisório)
FIGSPLIT = 0xDDF9                       # t13: começo de uma figura; nenhuma atravessa


def fig_map(a, unit='t13'):
    """o endereço no TK2000 de um byte $D000-$DFFF das figuras do banco 1 do voo.
    t13 (voo B, 16 páginas): até FIGSPLIT em $C200, o resto em FIG_HI.
    t18 (voo A, 12 páginas com dados): $D000-$D6FF -> $C200-$C8FF, $DB00-$DFFF -> $C900-$CDFF
    (as páginas $D7-$DA são vazias)."""
    if unit == 't18':
        return 0xC200 + a - 0xD000 if a < 0xD700 else 0xC900 + a - 0xDB00 if a >= 0xDB00 else None
    return 0xC200 + a - 0xD000 if a < FIGSPLIT else FIG_HI + a - FIGSPLIT


# tabelas de ponteiros de figuras: unidade -> [(lo, hi, entradas, trilha das figuras do banco 1)]
FIGTAB = {
    't9': [(0x9C00, 0x9C80, 128, 't13'), (0x9E00, 0x9E80, 128, 't13'), (0x9F00, 0x9F80, 128, 't13')],
    't14': [(0x9DD2, 0x9E06, 52, 't18')],   # lidas pela rotina residente ($F0/$F2 -> $E0/$E1 -> $B3B2)
}


def patches(nm, base, data):
    out = {}
    for a, (old, new) in CODE.get(nm, {}).items():
        assert data[a - base:a - base + len(old)] == old, (nm, hex(a))
        for k, v in enumerate(new):
            out[a + k] = v
    for a in PG.get(nm, []):
        assert data[a - base] == 0x20, (nm, hex(a))
        out[a] = 0x80
    if nm in HOLES:
        lo, hi = HOLES[nm]
        for a in range(lo, hi, 8):
            new = snippet(data[a - base:a - base + 8])
            for k in range(8):
                if new[k] != data[a - base + k]:
                    out[a + k] = new[k]
    for lo, hi, n, unit in FIGTAB.get(nm, []):
        for x in range(n):
            v = data[lo - base + x] | data[hi - base + x] << 8
            if (nm, v) in FIGSPECIAL:
                w = FIGSPECIAL[(nm, v)]
            elif 0xD000 <= v < 0xE000:
                w = fig_map(v, unit)
                assert w is not None, (nm, hex(v))
            elif 0x4000 <= v < 0x6000 or 0xA000 <= v < 0xC000:
                w = reloc(v)
            else:
                continue
            out[lo + x], out[hi + x] = w & 0xFF, w >> 8
    for a in HI.get(nm, []):
        v = data[a - base]
        assert 0x40 <= v < 0x60 or 0xA0 <= v < 0xC0, (nm, hex(a), hex(v))
        out[a] = v ^ 0xE0
    return out
