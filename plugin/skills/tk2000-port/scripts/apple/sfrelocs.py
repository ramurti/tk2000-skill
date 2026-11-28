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
    't32': [0xEAEB],                    # modelo do buraco $55F8 (troca de página), copiado para a página 2 no Restart
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
    't7': {0x6C0B: (b'\xE9', b'\x99'), 0x6C34: (b'\xE8', b'\x98'),
           # o JSR do efeito no alto-falante ($6BB8) aponta para si mesmo até o interpretador de sons,
           # que no Apple roda pela interrupção da Mockingboard, preenchê-lo; o TK2000 não tem essa
           # interrupção e o jogo entrava em recursão sem fim (Plane Training, no lançamento). Começa
           # com $6BD1, o valor mais comum nos estados do AppleWin (provisório: etapa de sons)
           0x6BB9: (b'\xB8\x6B', b'\xD1\x6B')},
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
KEY, BTN0, BTN1 = 0x6480, 0x6481, 0x6482
KCLR, PDL8, PDL25, PREAD = 0x6206, 0x6209, 0x620C, 0x620F
TKINV = 0x6221                          # a inversão dos anéis do tubo (ciano <-> verde)
TKKEY, TKB0B, TKB1B, TKL0, TKL1 = 0x6212, 0x6215, 0x6218, 0x621B, 0x621E
# a leitura (opcode, E/S do Apple) -> a rotina da camada que varre o teclado e devolve o mesmo
_ROUT = {(0xAD, 0xC000): TKKEY, (0x2C, 0xC061): TKB0B, (0x2C, 0xC062): TKB1B,
         (0xAD, 0xC061): TKL0, (0xAD, 0xC062): TKL1}
INPUT = {                               # unidade: [(endereço da instrução, E/S do Apple)]
    'r40': [(0x52F8, 0xC000)], 't32': [(0xEB60, 0xC000)],
    't7': [(0x6C65, 0xC000), (0x6C6A, 0xC061), (0x6C6F, 0xC062)],
    't21': [(0x7772, 0xC061), (0x7777, 0xC062)],
    't8': [(0x86A3, 0xC061), (0x86A8, 0xC062), (0x86BB, 0xC062)],
    't25': [(0xD3D4, 0xC061), (0xD3D9, 0xC062), (0xD3DD, 0xC061), (0xD3E2, 0xC062), (0xD7BA, 0xC000)],
}
_JSR = lambda a: bytes([0x20, a & 0xFF, a >> 8])   # noqa: E731
_JMP = lambda a: bytes([0x4C, a & 0xFF, a >> 8])   # noqa: E731
# os sons refeitos no alto-falante (src/tksom.s, tools/mksom.py): no lugar do tratador de interrupção da
# Mockingboard do t7 ($6A93-$6B19, nunca roda sem a placa); a turbina na tela "Prepare To Launch" do t21
# (opção B do dono do projeto): TURB0 no começo da tela, TURB no lugar das leituras do FIRE nos laços de espera
_ts = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tksom.bin')
if _os.path.exists(_ts):
    SOM = open(_ts, 'rb').read()
    TURB0, TURB = 0x6A93, 0x6AA0
    CODE['t7'][0x6A93] = (_track(7)[0xA93:0xA93 + len(SOM)], SOM)
    CODE['t21'] = {0x7516: (b'\xA9\x06\x85\x30', _JSR(TURB0) + b'\xEA'),   # lda #$06 / sta $30 -> jsr TURB0 / nop
                   0x7521: (_JSR(0x7772), _JSR(TURB)),                     # Prepare To Launch: as duas esperas
                   0x7533: (_JSR(0x7772), _JSR(TURB)),
                   0x7508: (_JSR(0x7772), _JSR(TURB)),                     # a escolha da altitude
                   # cada volta das esperas custa ~5,5 vezes mais que no Apple (a leitura do FIRE da camada, uma
                   # amostra da turbina por jsr AMOSTRA, os ganchos dos tiques e do desenho): as contagens 16 e 20
                   # viram 3 e 4, o texto pisca no tempo do Apple (~0,42 s; medido no emulador em 27/11/2026)
                   0x751E: (b'\x10', b'\x03'), 0x7530: (b'\x14', b'\x04')}
    # para o lockstep: as duas esperas atravessadas inteiras, até uma das saídas (o fim da contagem ou o FIRE)
    SPANS_SOM = {0x7521: ((0x752C, 0x7549), 'xy'), 0x7533: ((0x753E, 0x7546), 'xy')}   # X, Y: as contagens
else:
    SPANS_SOM = {}
# a música do título (src/tkmus.s, opção A do dono do projeto): no fim do t25 ($DD80, zeros no disco); a entrada
# $D006 (jmp $D15F, chamada uma vez por quadro da abertura) passa por MUS, que toca metade de cada quadro
_tm = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tkmus.bin')
if _os.path.exists(_tm):
    MUSB = open(_tm, 'rb').read()
    CODE.setdefault('t25', {})
    CODE['t25'][0xDD80] = (_track(25)[0xD80:0xD80 + len(MUSB)], MUSB)
    CODE['t25'][0xD006] = (_JMP(0xD15F), _JMP(0xDD80))
    SPANS_SOM[0xD006] = ((0xD15F,), 'xy')     # o lockstep atravessa a música (X e Y voltam como estavam)
# os estalinhos do voo (src/tkestalo.s, escolha do dono do projeto): no caminho da Mockingboard do t7 ($6A19-$6A8F,
# só roda com a placa); o tique do motor de som (r40 $45F8, jmp $6BA5) passa por TICK, que conta os tiques; os dois
# cliques do motor ($6BB0, $6BD5: bit $C030) viram jsr ESTAL: um estalo de 4 cliques no começo de cada rajada
_te = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tkestalo.bin')
if _os.path.exists(_te):
    ESTB = open(_te, 'rb').read()
    TICK, ESTAL = 0x6A19, 0x6A24          # conferir em build/tk/tkestalo.lst
    CODE['t7'][0x6A19] = (_track(7)[0xA19:0xA19 + len(ESTB)], ESTB)
    CODE['t7'][0x6BB0] = (b'\x2C\x30\xC0', _JSR(ESTAL))
    CODE['t7'][0x6BD5] = (b'\x2C\x30\xC0', _JSR(ESTAL))
    CODE['r40'][0x45F8] = (_JMP(0x6BA5), _JMP(TICK))
    SPANS_SOM.update({0x45F8: ((0x6BA5,), 'p'), 0x6BB0: (0x6BB3, 'p'), 0x6BD5: (0x6BD8, 'p')})
# o "zuuum" da corrida no tubo (src/tkzuum.s, opção C do dono do projeto): a espera de cada quadro da corrida
# (t22 jsr $A288) vira jsr ZUUM, no fim do t22 (zeros no disco; $4FB2 no TK2000), que toca durante a mesma espera;
# a volta do chiado (src/tkzuumr.s) no t7, depois dos estalinhos
_tz = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tkzuum.bin')
_tzr = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tkzuumr.bin')
if _os.path.exists(_tz) and _os.path.exists(_tzr):
    ZB, ZRB = open(_tz, 'rb').read(), open(_tzr, 'rb').read()
    CODE['t7'][0x6A53] = (_track(7)[0xA53:0xA53 + len(ZRB)], ZRB)
    CODE.setdefault('t22', {})[0xAFB2] = (_track(22)[0xFB2:0xFB2 + len(ZB)], ZB)
    CODE['t22'][0xA270] = (_JSR(0xA288), _JSR(0x4FB2))     # o endereço do TK2000: a troca vem depois da realocação
    SPANS_SOM[0xA270] = ((0xA273,), 'ap')     # A (o n antigo no original) e os flags acertados no fim da espera
# a turbina durante o desenho da imagem do tubo (src/tkdesenho.s, no fim do r1A: zeros que nenhuma medição usa): a
# chamada do desenho (t21 $7585) liga a marca; os dois laços do decodificador (rB0 $B26D, $B299) tocam uma amostra
# por byte com a marca ligada
_td = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'build', 'tk', 'tkdesenho.bin')
if _os.path.exists(_td):
    TDB = open(_td, 'rb').read()
    TDRAW, GANCHO1, GANCHO2 = 0x1EEC, 0x1EFF, 0x1F10     # conferidos com .assert em src/tkdesenho.s
    _res = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'reference', 'resident-14s.bin'), 'rb').read()
    CODE.setdefault('r1A', {})[0x1EEB] = (_res[0x1EEB:0x1EEB + len(TDB)], TDB)
    CODE['t21'][0x7585] = (_JSR(0xB229), _JSR(TDRAW))
    CODE.setdefault('rB0', {})[0xB26D] = (b'\xCA\xD0\xD3', _JMP(GANCHO1))   # dex / bne $B243
    CODE['rB0'][0xB299] = (b'\xCA\xF0\xF6', _JMP(GANCHO2))                   # dex / beq $B292
    SPANS_SOM.update({0x7585: ((0x7588,), 'ap'), 0xB26D: ((0xB243, 0xB270), 'p'), 0xB299: ((0xB29C, 0xB292), 'p')})


INCODE = {                              # trocas de instrução da entrada
    'r40': {0x5378: (b'\x2C\x10\xC0', _JSR(KCLR))},   # bit $C010 -> jsr KCLR
    't32': {0xEBA0: (b'\x2C\x10\xC0', _JSR(KCLR))},
    't8': {0x894A: (b'\x2C\x70\xC0', _JMP(PDL8))},    # a leitura do joystick em laço
    't25': {0xD363: (b'\x2C\x70\xC0', _JMP(PDL25))},
    'rB0': {0xB020: (b'\x2C\x70\xC0', _JMP(PREAD))},  # a leitura simples
    # os anéis das paredes do tubo de lançamento: no Apple a inversão dos pontos troca violeta e verde (e
    # preto e branco); no TK2000 as paredes são ciano e verde, os mesmos pontos com outra paleta (TKINV)
    't22': {0xA356: (b'\x49\xFF\x29\x7F', _JSR(TKINV) + b'\xEA')},   # eor #$FF / and #$7F -> jsr TKINV / nop
}
# para o lockstep: trechos trocados com outro fim (endereço do Apple) e os registradores a igualar
SPANS = {0x894A: (0x896A, 'xy'), 0xD363: (0xD383, 'xy'), 0xB020: (0xB030, 'ay')}
SPANS.update({a: (a + 3, 'ap') for d in INPUT.values() for a, io in d})   # as leituras viradas jsr
SPANS.update(SPANS_SOM)

HOLES = {
    't32': (0xEA00, 0xF000),            # $EA00-$EBFF: os 64 buracos da página 2, copiados de volta no Restart
                                        # do fim de jogo; voo A usa $EC00-$EDFF, voo B $EE00-$EFFF
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


# Cores (escolha do dono do projeto, 25/11/2026): no voo, chão verde e céu azul. Os padrões de
# preenchimento do Apple (céu azul $D5/$AA, chão verde $2A/$55) saem ciano e azul no TK2000; com
# os bytes do verde do Apple o TK2000 mostra azul, e com os do violeta ($55/$2A), verde (a mesma
# paleta: sem franja no horizonte). Os imediatos dos padrões, nas rotinas que pintam o céu e o chão:
COLOR_MAP = {0xD5: 0x2A, 0xAA: 0x55, 0x2A: 0x55, 0x55: 0x2A}
COLORS = {
    't16': [0x70F5, 0x7103, 0x7111, 0x711C, 0x71CF, 0x71D3, 0x71D7, 0x71E5, 0x734C, 0x735A, 0x7368,
            0x7373, 0x73FC, 0x7400, 0x7404, 0x7412, 0x746B, 0x7470, 0x74AE, 0x74B3, 0x7557, 0x755C,
            0x7561, 0x7566, 0x7592, 0x7597, 0x75DD, 0x75E2, 0x75E7, 0x75EC, 0x75F5, 0x75FA, 0x75FF,
            0x7604, 0x7677, 0x767C, 0x76A0, 0x76A5, 0x76AA, 0x76AF, 0x76D6, 0x76DB, 0x7720, 0x7725,
            0x772E, 0x7733, 0x775C, 0x7761, 0x777E, 0x7783, 0x77AF, 0x77B4, 0x77EF, 0x77F4],
    't19': [0x7389, 0x7392, 0x73D6, 0x74E5, 0x74FE, 0x751F],
}


_cj = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'src', 'cores.json')
_cd = __import__('json').load(open(_cj)) if _os.path.exists(_cj) else {}
COLORDATA = _cd.get('troca', {})       # padrões de céu e chão: COLOR_MAP
BIT7DATA = _cd.get('bit7', {})         # preto/branco da moldura: bit 7 desligado
CONFLITO = _cd.get('conflito', {})     # pintam céu/chão e outra cor: ficam como estão
PARIDADE = {k: {int(a): p for a, p in v.items()} for k, v in _cd.get('paridade', {}).items()}
VALOR = {k: {int(a): x for a, x in v.items()} for k, v in _cd.get('valor', {}).items()}   # os nomes da abertura


# as imagens em fluxo da rotina rB0 $B229 (ldx/ldy # antes do jsr): coluna por coluna, de baixo
# para cima; $FE, contagem, valor = repetição. As marcas e as contagens não são cores.
STREAMS = [0xA5A0, 0x79DD]


def stream_ctl(base, data):
    """os endereços das marcas $FE e das contagens dos fluxos que começam nesta unidade"""
    ctl = set()
    for st in STREAMS:
        if not base <= st < base + len(data):
            continue
        p, cells = st, 40 * 192
        while cells > 0 and base <= p < base + len(data) - 2:
            if data[p - base] == 0xFE:
                ctl.update((p, p + 1))
                cells -= data[p + 1 - base] or 256
                p += 3
            else:
                cells -= 1
                p += 1
    return ctl


_tq = _os.path.join(_os.path.dirname(_os.path.abspath(__file__)), '..', 'src', 'tanque.json')
FIGCOR = {'t32': {int(a, 16): v for a, v in __import__('json').load(open(_tq))['bytes'].items()}} \
    if _os.path.exists(_tq) else {}     # figuras recoloridas ponto a ponto (o tanque do menu, opção B)
STREAM_CABINE = {'t22': 0xA5A0}        # a imagem da pista (dentro da cabine): refeita com as cores


def _cabine(y, c, v):
    import sfcores as C
    o = C.row(y) + c
    if C.JANELA[o] and (v, c & 1) in C.SWAP:
        return C.SWAP[(v, c & 1)]
    if C.bw(v) and not C.JANELA[o] and C.JANELA[(o + 1) & 0x1FFF]:
        return v & 0x7F
    return v


TUBO_Y = 152                            # as paredes do tubo vão até a linha 151; abaixo, o painel (fica como está)


def _tubo(toks):
    """a imagem da pista: a regra da cabine, e as faixas violeta das paredes do tubo de lançamento viram
    ciano (bit 7; escolha do dono do projeto, 26/11/2026). Dentro da janela; uma repetição decide de uma
    vez (pela maioria das células), para o fluxo não crescer nem se partir"""
    import sfcores as C
    dentro = {}
    for _, kind, cl, _ in toks:
        if kind == 'run':
            d = 2 * sum(C.JANELA[C.row(y) + c] for y, c in cl) > len(cl)
            dentro.update((yc, d) for yc in cl)

    def fn(y, c, v):
        if y < TUBO_Y and C.violeta(v, c) and dentro.get((y, c), C.JANELA[C.row(y) + c]):
            return v | 0x80
        return _cabine(y, c, v)
    return fn


def patches(nm, base, data):
    out = {}
    ctl = stream_ctl(base, data)
    import disa2                                # as cores nunca mexem em bytes de instrução (só nos
    ctl |= disa2.INSTR.get(nm, set())          # operandos dos imediatos): o jogo também lê alguns como
                                                # dados (dispkg.py desmonta antes e preenche INSTR)
    for a, v in FIGCOR.get(nm, {}).items():     # figuras recoloridas: no lugar das listas de cores
        if data[a - base] != v:
            out[a] = v
        ctl.add(a)
    if nm in STREAM_CABINE:                     # a imagem inteira, pela regra da cabine (sfcores)
        import sfstream
        st = STREAM_CABINE[nm]
        toks, end = sfstream.decode(data, base, st)
        new = sfstream.recolor(toks, _tubo(toks))
        room = end
        while room < base + len(data) and data[room - base] == 0:
            room += 1
        assert st + len(new) <= room, 'a imagem refeita não cabe'
        for k, v in enumerate(new):
            if data[st - base + k] != v:
                out[st + k] = v
        ctl |= set(range(st, end))              # as listas do rastreio não mexem nela
    for a in (set(COLORS.get(nm, [])) - set(CONFLITO.get(nm, [])) | set(COLORDATA.get(nm, []))) - ctl:
        p = PARIDADE.get(nm, {}).get(a)
        if p is not None:                       # ponto a ponto, na paridade da coluna (sfcores.swapbyte)
            import sfcores
            nv = sfcores.swapbyte(data[a - base], p)
            if nv != data[a - base]:
                out[a] = nv
        elif data[a - base] in COLOR_MAP:
            out[a] = COLOR_MAP[data[a - base]]
    for a, v in VALOR.get(nm, {}).items():      # os nomes da abertura redesenhada no Restart: o byte do
        if a not in ctl and data[a - base] != v:   # TK2000 (letras brancas sobre o verde, sfcores.texto)
            out[a] = v
    troca = set(COLORS.get(nm, [])) | set(COLORDATA.get(nm, []))
    for a in BIT7DATA.get(nm, []):
        v = data[a - base]
        bw = v & 0x80 and all(((v >> k) & 1) == 0 or (k > 0 and (v >> (k - 1)) & 1) or
                              (k < 6 and (v >> (k + 1)) & 1) for k in range(7))
        if bw and a not in troca and a not in ctl:   # só preto/branco de verdade (o rastreio junta origens)
            out[a] = v & 0x7F
    if nm in ('r20', 'r40'):                    # a tela do título com as cores do TK2000 (sfcores, opção C)
        import sfcores
        for k, v in enumerate(sfcores.abertura(data)):
            if v != data[k]:
                out[base + k] = v
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
    for a, io in INPUT.get(nm, []):              # leitura de teclado/botão -> jsr para a camada
        assert data[a - base + 1] | data[a - base + 2] << 8 == io, (nm, hex(a))
        r = _ROUT[(data[a - base], io)]
        out[a], out[a + 1], out[a + 2] = 0x20, r & 0xFF, r >> 8
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
