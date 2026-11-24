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
    't22': [0xA428, 0xA241],            # $A428: copia a página 2 para a página 1 (linha + $20); $A241: lda #$20 / sta $20
    't21': [0x742E, 0x757C],            # lda #$20 / sta $20: desenhar na página 2
    't25': [0xD05E],
    't29': [0xF57D, 0xF58F, 0xF8B1],    # $F8B1: linha + $20 (desenha nas duas páginas)
}

SMC_PG = [0xB3AD]                       # imediatos que o código reescreve com $20 (o deslocamento de
                                        # página): num estado salvo no meio do uso, $20 -> $80
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
    't21': [0x72A7, 0x72A8, 0x72AB, 0x72AC, 0x72AD, 0x72AE, 0x72AF,   # tabela de saltos $7296/$72A4 (JMP em $7285)
            0x747E, 0x7584],            # ldx #$A0 / ldy #$A5 / jsr $B229: a sequência de dados em $A5A0 (t20)
    't19': [0x71AB, 0x71AC, 0x71AF, 0x71B0, 0x71B1, 0x71B2, 0x71B5],   # tabela de saltos $719D/$71AA (JMP em $718D)
    't30': [0xFFFB, 0xFFFD, 0xFFFF],    # vetores NMI, RESET, IRQ/BRK -> $BFAA (um RTS do carregador)
    't29': [0xFFFB, 0xFFFD, 0xFFFF],
    't25': [0xD069, 0xD089,             # jsr $B51B + 8 bytes: o ponteiro da figura ($A3DF, no t33)
            0xD8F2, 0xD8F6, 0xD8FA],    # registros [x, y, endereço] de números na tela ($B1C1): variáveis nos buracos
}

import os as _os
_DSK = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'reference',
                     'Skyfox_1984_Electronic_Arts_cr_Black_Bag.dsk')


def _track(t):
    d = open(_DSK, 'rb').read()
    return b''.join(d[t * 4096 + (15 - n) * 256:t * 4096 + (16 - n) * 256] for n in range(16))


LAYER_AT = 0x6200                       # a camada do TK2000 (src/tklayer.s, tools/mklayer.py)
TKSEEK, TKDEST = 0x6200, 0x6203         # entradas fixas da camada
FIGX = 0x64A0                           # cópia da figura $DDF9 do t13 (atravessaria $DE00)
FIGCOPY = 0x64C0                        # a figura 17 do t14 aponta para $9E0C, dentro da própria tabela
PAGEIDX = 0x64FE                        # [$00, $40]: índice das listas por página
_lb = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'layer.bin')
LAYER = {LAYER_AT: open(_lb, 'rb').read()} if _os.path.exists(_lb) else {
    PAGEIDX: bytes([0x00, 0x40]), FIGCOPY: _track(14)[0xE0C:0xE2C], FIGX: _track(13)[0xDF9:0xE0A]}
FIGSPECIAL = {('t14', 0x9E0C): FIGCOPY, ('t9', 0xDDF9): FIGX}

CODE = {
    't8': {0x801B: (b'\x0A', b'\x4A')},  # asl a -> lsr a
    'r40': {0x53F9: (b'\xE9', b'\x99'), 0x5479: (b'\xE8', b'\x98')},   # motor ligado / desligado
    't7': {0x6C0B: (b'\xE9', b'\x99'), 0x6C34: (b'\xE8', b'\x98')},
    't32': {0xEA29: (b'\xE8', b'\x98'), 0xEBE1: (b'\xE9', b'\x99')},   # modelos do motor para os buracos
    't9': {0x9100: (b'\x0A', b'\x4A')},  # asl a -> lsr a
    'rB0': {
        0xB3D6: (b'\x0A', b'\x4A'),                     # asl a -> lsr a
        # o carregador: anota a trilha e desvia as figuras do banco 1 (src/tklayer.s)
        0xBF1C: (b'\x20\xD4\xBC', bytes([0x20, TKSEEK & 0xFF, TKSEEK >> 8])),
        0xBF43: (b'\x85\x45\xA9\x00\x85\x44', bytes([0x20, TKDEST & 0xFF, TKDEST >> 8, 0xEA, 0xEA, 0xEA])),
        # o drive: slot 6 do Apple ($C0E0-$C0EF) -> interface de disco do TK2000 ($C090-$C09F)
        **{a: (b'\xEC', b'\x9C') for a in (0xBC38, 0xBC42, 0xBC4C, 0xBC5B, 0xBC72, 0xBC88, 0xBC9C,
                                          0xBCB1, 0xBCC3, 0xBD2D, 0xBD37, 0xBD42, 0xBD4F, 0xBD57,
                                          0xBD69, 0xBD73)},
        0xBCFA: (b'\x80', b'\x30'),                     # lda $C080,y (y = $60 + fase) -> $C030,y
        0xBD0E: (b'\x81', b'\x31'),
        0xB7FF: (b'\x65\x20\x65\x20', bytes([0xEA, 0x7D, PAGEIDX & 0xFF, PAGEIDX >> 8])),  # adc $20 x2 -> nop / adc PAGEIDX,x
    },
}

# A entrada (src/tklayer.s): o teclado e o joystick do Apple -> variáveis da camada
KEY, BTN0, BTN1 = 0x62E0, 0x62E1, 0x62E2
KCLR, PDL8, PDL25, PREAD = 0x6206, 0x6209, 0x620C, 0x620F
_OP = {0xC000: KEY, 0xC061: BTN0, 0xC062: BTN1}
INPUT = {                               # unidade: [(endereço da instrução, E/S do Apple)]
    'r40': [(0x52F8, 0xC000)], 't32': [(0xEB60, 0xC000)],
    't7': [(0x6C65, 0xC000), (0x6C6A, 0xC061), (0x6C6F, 0xC062)],
    't21': [(0x7772, 0xC061), (0x7777, 0xC062)],
    't8': [(0x86A3, 0xC061), (0x86A8, 0xC062), (0x86BB, 0xC062)],
    't25': [(0xD3D4, 0xC061), (0xD3D9, 0xC062), (0xD3DD, 0xC061), (0xD3E2, 0xC062), (0xD7BA, 0xC000)],
}
_JSR = lambda a: bytes([0x20, a & 0xFF, a >> 8])   # noqa: E731
_JMP = lambda a: bytes([0x4C, a & 0xFF, a >> 8])   # noqa: E731
INCODE = {                              # trocas de instrução da entrada
    'r40': {0x5378: (b'\x2C\x10\xC0', _JSR(KCLR))},   # bit $C010 -> jsr KCLR
    't32': {0xEBA0: (b'\x2C\x10\xC0', _JSR(KCLR))},
    't8': {0x894A: (b'\x2C\x70\xC0', _JMP(PDL8))},    # a leitura do joystick em laço
    't25': {0xD363: (b'\x2C\x70\xC0', _JMP(PDL25))},
    'rB0': {0xB020: (b'\x2C\x70\xC0', _JMP(PREAD))},  # a leitura simples
}
# para o lockstep: trechos trocados com outro fim (endereço do Apple) e os registradores a igualar
SPANS = {0x894A: (0x896A, 'xy'), 0xD363: (0xD383, 'xy'), 0xB020: (0xB030, 'ay')}

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
                # um vetor de saltos: mais um JMP/JSR logo depois continua (ex.: $59F8 jmp / $59FB jmp)
                if k < len(b) and b[k] in (0x4C, 0x20) and k + 3 <= len(b):
                    continue
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


# Trechos de código guardados como dados e copiados para outro lugar antes de rodar (t25: a passagem
# da abertura para a demonstração copia um deles para $67AE): (início, fim inclusive)
TEMPLATES = {
    't25': [(0xDBE5, 0xDBEA), (0xDBEB, 0xDC35), (0xDC36, 0xDCA4), (0xDCA5, 0xDCFF), (0xDD00, 0xDD50),
            (0xDD51, 0xDD6C), (0xDD6D, 0xDD7F)],
}


TEMPLATE_DEST = 0x67AE                  # para onde o jogo copia os trechos (t25 $D551: sta $67AE,y)


def template_code(data, base, lo, hi):
    """as instruções de um trecho, seguindo o fluxo a partir do começo dentro de [lo, hi]; um ramo que
    chega a um byte inválido ou a outro alinhamento só termina (não invalida o resto)"""
    from py65.devices.mpu6502 import MPU
    ops = getattr(snippet, 'ops', None) or MPU().disassemble
    snippet.ops = ops
    first = lo                                  # os RTS do começo são entradas curtas; o código
    while first < hi and data[first - base] == 0x60:   # de verdade começa depois deles
        first += 1
    ins, used, work = {}, set(), [first, lo]
    if data[lo - base] == 0x4C:                 # começa com JMP: o que vem depois é outra entrada
        work.append(lo + 3)
    while work:
        a = work.pop()
        while lo <= a <= hi and a not in ins:
            mn, mode = ops[data[a - base]]
            n = LEN[mode]
            if mn == '???' or a + n - 1 > hi or any(b in used for b in range(a, a + n)):
                break
            ins[a] = (mn, mode, n)
            used.update(range(a, a + n))
            if mode == 'rel':
                off = data[a - base + 1]
                work.append(a + 2 + (off - 256 if off >= 128 else off))
            if mn in ('JMP', 'JSR') and mode == 'abs':      # para dentro do bloco já copiado
                v = data[a - base + 1] | data[a - base + 2] << 8
                if TEMPLATE_DEST <= v <= TEMPLATE_DEST + (hi - lo):
                    work.append(lo + v - TEMPLATE_DEST)
            if mn in ('RTS', 'RTI', 'JMP'):
                break
            a += n
    return ins


FIG_HI = 0x6000                         # o resto das figuras da trilha 13 (provisório)
FIGSPLIT = 0xDE00                       # t13: páginas $D0-$DD em $C200, $DE-$DF em $6000 (a figura
                                        # $DDF9, que atravessaria, vai inteira para FIGX)


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


HOLESCAN = ['t32', 't15', 't10']                      # unidades só de dados com código de buraco embutido em imagens
                                        # (a rotina de figuras copia linhas inteiras, buracos inclusive)


def hole_snippets(data, base):
    """(início, fim) de cada trecho que decodifica limpo até um JMP para um buraco da tela"""
    from py65.devices.mpu6502 import MPU
    ops = getattr(snippet, 'ops', None) or MPU().disassemble
    snippet.ops = ops
    out = []
    hole = lambda v: 0x2000 <= v < 0x6000 and (v & 0x7F) >= 0x78 or v == 0xBFAA   # noqa: E731
    # (o último buraco da cadeia termina com jmp $BFAA: um RTS no fim do carregador)
    for i in range(len(data) - 2):
        if data[i] == 0x4C and hole(data[i + 1] | data[i + 2] << 8):
            for st in range(max(0, i - 5), i + 1):
                k = st
                while k < i and ops[data[k]][0] != '???':
                    k += LEN[ops[data[k]][1]]
                if k == i:
                    out.append((base + st, base + i + 2))
                    break
    return out


def patches(nm, base, data):
    out = {}
    if nm in ('r20', 'r40'):                    # cada buraco da tela, como os que o jogo instala
        for h in range(base, base + len(data), 0x80):
            hb = h + 0x78
            new = snippet(data[hb - base:hb - base + 8])
            for k in range(8):
                if new[k] != data[hb - base + k]:
                    out[hb + k] = new[k]
    if nm in HOLESCAN:
        for st, en in hole_snippets(data, base):
            b = snippet(data[st - base:en - base + 1])
            for k, v in enumerate(b):
                if v != data[st - base + k]:
                    out[st + k] = v
    for a, io in INPUT.get(nm, []):
        assert data[a - base + 1] | data[a - base + 2] << 8 == io, (nm, hex(a))
        out[a + 1], out[a + 2] = _OP[io] & 0xFF, _OP[io] >> 8
    for a, (old, new) in list(CODE.get(nm, {}).items()) + list(INCODE.get(nm, {}).items()):
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
    for lo, hi in TEMPLATES.get(nm, []):
        for a, (mn, mode, n) in template_code(data, base, lo, hi).items():
            if n == 3:
                v = data[a - base + 1] | data[a - base + 2] << 8
                if 0x4000 <= v < 0x6000 or 0xA000 <= v < 0xC000:
                    out[a + 2] = (v >> 8) ^ 0xE0
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
