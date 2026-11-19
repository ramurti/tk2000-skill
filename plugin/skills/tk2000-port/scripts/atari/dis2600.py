#!/usr/bin/env python3
"""Desmonta o cartucho de 2K (reference/tennis.a26, em $F000) em fonte para o dasm.

Código = o que o simulador rodou (build/coverage.json, tools/reference/coverage.py) mais o que um
rastreamento estático alcança a partir dos vetores; o resto é dado (.byte). Rótulos: Lxxxx para
destinos de salto e de desvio e para endereços da ROM usados como operandos. Registradores da TIA
e do RIOT pelo nome (nomes de leitura para cargas e comparações, nomes de escrita para
gravações). Endereços da página zero usados com um modo absoluto ficam assim (.w), para o fonte
montar nos mesmos bytes (tools/check: build/ref).

Uso: dis2600.py saida.asm [--tk]

--tk: a versão que roda no TK2000 (src/main.s a inclui com .incbin em $4000): ORG $4000 e, em vez
de esperar o temporizador e desenhar a imagem (WaitVblank e o kernel), um salto para TK_FRAME
($4803, src/main.s), que desenha e volta para Overscan.
"""
import json
import os
import sys

from py65.devices.mpu6502 import MPU

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
ORG = 0xF000
TK = '--tk' in sys.argv
TK_ORG, TK_FRAME, TK_HOOK, TK_HOOK_END = 0x4000, 0x4803, 0xF051, 0xF056
rom = open(os.path.join(ROOT, 'reference', 'tennis.a26'), 'rb').read()
SIZE = len(rom)
OPS = MPU().disassemble
LEN = {'imp': 1, 'acc': 1, 'imm': 2, 'zpg': 2, 'zpx': 2, 'zpy': 2, 'inx': 2, 'iny': 2, 'rel': 2,
       'abs': 3, 'abx': 3, 'aby': 3, 'ind': 3}

TIA_W = ('VSYNC VBLANK WSYNC RSYNC NUSIZ0 NUSIZ1 COLUP0 COLUP1 COLUPF COLUBK CTRLPF REFP0 REFP1 '
         'PF0 PF1 PF2 RESP0 RESP1 RESM0 RESM1 RESBL AUDC0 AUDC1 AUDF0 AUDF1 AUDV0 AUDV1 GRP0 GRP1 '
         'ENAM0 ENAM1 ENABL HMP0 HMP1 HMM0 HMM1 HMBL VDELP0 VDELP1 VDELBL RESMP0 RESMP1 HMOVE '
         'HMCLR CXCLR').split()
TIA_R = 'CXM0P CXM1P CXP0FB CXP1FB CXM0FB CXM1FB CXBLPF CXPPMM INPT0 INPT1 INPT2 INPT3 INPT4 INPT5'.split()
RIOT = {0x280: 'SWCHA', 0x281: 'SWACNT', 0x282: 'SWCHB', 0x283: 'SWBCNT', 0x284: 'INTIM',
        0x285: 'TIMINT', 0x294: 'TIM1T', 0x295: 'TIM8T', 0x296: 'TIM64T', 0x297: 'T1024T'}
# nomes da RAM (as variáveis do original, $80-$D5), tirados da leitura do código e de observá-las
# no simulador; '?' = ainda não é certo
RAM = {
    0x80: ('gameNum', 'número do jogo 0-3 (SELECT)'),
    0x81: ('twoPlay', 'gameNum & 1: 1 = dois jogadores (senão o computador joga de um lado)'),
    0x82: ('colEor', 'modo de demonstração: EOR das cores'),
    0x83: ('colMask', 'AND das cores (preto e branco / demonstração)'),
    0x84: ('frame', 'contador de quadros'),
    0x86: ('scoreA', 'placar mostrado à direita ($B0/$B2): índice na tabela de dígitos'),
    0x87: ('scoreB', 'placar mostrado à esquerda ($AC/$AE): índice na tabela de dígitos'),
    0x88: ('idle', 'temporizador de inatividade (bit 7: modo de demonstração)'),
    0x89: ('plr', 'lógica: o jogador sendo tratado (1, 0)'),
    0x8A: ('tmp0', ''),
    0x8B: ('tmp1', ''),
    0x8C: ('ballYLo', 'bola: frações de Y, X, Z'),
    0x8F: ('ballY', 'bola: profundidade (linha da sombra = ballY | 1; 185 - isso = linha da tela)'),
    0x90: ('ballX', 'bola: x (pixel da tela = ballX - 5)'),
    0x91: ('ballZ', 'bola: altura acima da quadra'),
    0x92: ('ballVY', 'bola: velocidade Y, X, Z (bytes altos)'),
    0x95: ('ballVYLo', 'bola: velocidade Y, X, Z (bytes baixos)'),
    0x98: ('plrY', 'jogadores: profundidade (0 = jogador de cima, 1 = de baixo)'),
    0x9A: ('plrX', 'jogadores: x'),
    0x9C: ('plrGfxA', 'jogadores: ponteiro dos gráficos (byte baixo), parte de cima'),
    0x9E: ('plrGfxB', 'jogadores: ponteiro dos gráficos (byte baixo), parte de baixo'),
    0xA0: ('serve', 'bit 7: esperando o saque'),
    0xA2: ('cpuWait', 'computador: espera antes de sacar?'),
    0xA3: ('selWait', 'espera de repetição do SELECT'),
    0xA4: ('kPtr', 'kernel: ponteiros dos gráficos do jogador sendo desenhado ($A4-$AB)'),
    0xAC: ('digPtr', 'kernel: ponteiros dos gráficos do placar / logotipo ($AC-$B3)'),
    0xB4: ('hitter', 'o jogador que bateu na bola por último'),
    0xB5: ('kPlrY', 'kernel: profundidade do jogador sendo desenhado'),
    0xB6: ('ballLine', 'kernel: linha da bola (ballY + ballZ, ímpar)'),
    0xB7: ('shadowLine', 'kernel: linha da sombra (ballY, ímpar)'),
    0xB8: ('plrRefl', 'jogadores: para onde olham (REFP)'),
    0xBA: ('kLine', 'kernel: contador de linhas'),
    0xBB: ('colCourt', 'cores: quadra (COLUBK)'),
    0xBC: ('colLines', 'cores: linhas e rede (COLUPF), bola'),
    0xBD: ('colPlr', 'cores: jogadores (trocadas quando os lados mudam)'),
    0xBF: ('colScore', 'cores: placares'),
    0xC1: ('swing', 'jogadores: passo do movimento da raquete'),
    0xC3: ('swingWait', 'jogadores: quadros por passo do movimento da raquete'),
    0xC5: ('points', 'pontos de cada jogador (0, 15, 30, 40...)'),
    0xC7: ('games', 'games de cada jogador'),
    0xC9: ('sndTime', 'som: volume / tempo restante'),
    0xCA: ('server', 'o jogador que saca'),
    0xCB: ('pointWait', 'depois de um ponto: quadros a esperar'),
    0xCC: ('bounces', 'quiques da bola?'),
    0xCD: ('step', 'movimento do jogador: passo da animação'),
    0xCE: ('moveY', 'movimento do jogador: joystick para cima/baixo (-1, 0, 1)'),
    0xCF: ('moveX', 'movimento do jogador: joystick para esquerda/direita (-1, 0, 1)'),
    0xD0: ('sides', 'os jogadores trocaram de lado'),
    0xD1: ('scoreMode', 'exibição de iguais / vantagem?'),
    0xD2: ('tieGames', 'games: regra de tie-break?'),
    0xD3: ('diff', 'chaves de dificuldade (raquete maior?)'),
    0xD5: ('diffIdx', ''),
}
# nomes das rotinas e uma linha de comentário para cada uma
NAMES = {
    0xF000: ('Start', 'ao ligar: limpa a RAM e a TIA, ponto novo'),
    0xF015: ('Frame', 'a cada quadro: posiciona as linhas laterais (M0, M1) e a bola, cores, ponteiros do placar'),
    0xF051: ('WaitVblank', ''),
    0xF087: ('KLine', 'kernel: uma linha da quadra (jogadores, bola, sombra, linhas laterais andando com HMOVE)'),
    0xF0C0: ('KLine2', ''),
    0xF0F6: ('KBaseline', 'kernel: as linhas de fundo (playfield)'),
    0xF110: ('KNet', 'kernel: a rede (playfield, 8 linhas), depois o outro jogador'),
    0xF149: ('KEnd', 'kernel: abaixo da quadra: o logotipo da Activision'),
    0xF168: ('Overscan', 'VSYNC, contador de quadros, temporizador de inatividade, chaves do console'),
    0xF1AB: ('Restart', ''),
    0xF1D8: ('Logic', 'lógica do jogo: depois de um ponto, depois cada jogador'),
    0xF1F4: ('PlayerLoop', 'por jogador: joystick ou computador, anda, mexe a raquete, bate na bola'),
    0xF40C: ('BallMove', 'bola: posição += velocidade, gravidade, quique, fora, ponto'),
    0xF47C: ('Sound', ''),
    0xF497: ('PosLow', ''),
    0xF4A1: ('PosPlayers', 'posiciona os dois jogadores em A'),
    0xF4A3: ('PosObject', 'posiciona o objeto X+1 (2: míssil 0, 3: míssil 1, 4: bola; -2: jogadores) em A'),
    0xF4EE: ('DrawLogo', ''),
    0xF4FC: ('DrawDigits', 'seis linhas de duas imagens de 8 pixels de largura por jogador (placares, logotipo)'),
    0xF53B: ('PointWon', 'um ponto: som, placar, games, lados'),
    0xF5E7: ('NewPoint', 'posições e velocidades da tabela em $F709, quem saca, lados'),
    0xF618: ('KPlayer', 'kernel: prepara o jogador X (cores, para onde olha, ponteiros, posição)'),
    0xF700: ('TabStep', ''),
    0xF704: ('TabSwing', ''),
    0xF709: ('TabInit', 'NewPoint: valores iniciais de $90-$B3'),
    0xF72D: ('TabDigLo', ''),
    0xF73F: ('TabDigHi', ''),
    0xF751: ('TabColors', 'cores: quadra, linhas, jogadores, placares'),
    0xF757: ('TabGray', 'cores: TV preto e branco'),
    0xF75D: ('TabSndFreq', ''),
}
READS = {'LDA', 'LDX', 'LDY', 'BIT', 'CMP', 'CPX', 'CPY', 'AND', 'ORA', 'EOR', 'ADC', 'SBC'}


def byte(a):
    return rom[(a - ORG) % SIZE]


def operand(a, mode):
    if LEN[mode] == 2:
        return byte(a + 1)
    if LEN[mode] == 3:
        return byte(a + 1) | byte(a + 2) << 8
    return None


def target(a, mode, val):
    if mode == 'rel':
        return (a + 2 + (val - 256 if val >= 128 else val)) & 0xFFFF
    return val


cov = json.load(open(os.path.join(ROOT, 'build', 'coverage.json')))
starts = {ORG + o for o in cov['code']}
# rastreamento estático a partir dos vetores (reset, BRK/IRQ) e de cada instrução que o simulador rodou
todo = [byte(ORG + 0x7FC) | byte(ORG + 0x7FD) << 8, byte(ORG + 0x7FE) | byte(ORG + 0x7FF) << 8]
todo += sorted(starts)
seen = set()
while todo:
    a = todo.pop()
    while ORG <= a < ORG + SIZE and a not in seen:
        mn, mode = OPS[byte(a)]
        if mn == '???':
            break
        seen.add(a)
        val = operand(a, mode)
        if mode == 'rel' or (mn in ('JSR', 'JMP') and mode == 'abs'):
            todo.append(target(a, mode, val))
        if mn in ('JMP', 'RTS', 'RTI', 'BRK'):
            break
        a += LEN[mode]
starts |= seen
# instruções não podem se sobrepor: ficam em ordem de endereço, a primeira vence
code, owner = {}, {}
for a in sorted(starts):
    if a in owner:
        continue
    n = LEN[OPS[byte(a)][1]]
    if a + n > ORG + SIZE or any(a + i in owner for i in range(n)):
        continue
    code[a] = n
    for i in range(n):
        owner[a + i] = a

labels = {}
for a, n in code.items():
    mn, mode = OPS[byte(a)]
    val = operand(a, mode)
    if mode == 'rel' or (mode in ('abs', 'abx', 'aby', 'ind') and val >= ORG):
        t = target(a, mode, val)
        labels[t] = 'L%04X' % t
for t, (n, _) in NAMES.items():
    labels[t] = n
# vetores
for v in range(ORG + 0x7FA, ORG + 0x800, 2):
    t = byte(v) | byte(v + 1) << 8
    if ORG <= t < ORG + SIZE:
        labels.setdefault(t, 'L%04X' % t)


def ram_name(val):
    """Um endereço da RAM pelo nome (ou nome+n dentro de uma tabela)."""
    for base in range(val, 0x7F, -1):
        if base in RAM:
            n = val - base
            if n == 0:
                return RAM[base][0]
            return '%s+%d' % (RAM[base][0], n) if n < 6 else None
    return None


def name(a, mn, mode, val):
    """O texto do operando."""
    if mode in ('imp', 'acc'):
        return ''
    if mode == 'imm':
        return '#$%02X' % val
    if mode == 'rel':
        return labels[target(a, mode, val)]
    if mode in ('abs', 'abx', 'aby', 'ind') and val in labels:
        txt = labels[val]
    elif 0x80 <= val < 0x100 and ram_name(val):
        txt = ram_name(val)
    elif val < 0x80 and mode != 'ind' and not (val == 0 and mode in ('zpx', 'abx')):
        if mn in READS:
            txt = TIA_R[val & 0x0F] if (val & 0x0F) < len(TIA_R) and val < 0x10 else '$%02X' % val
        else:
            txt = TIA_W[val] if val < len(TIA_W) else '$%02X' % val
    elif val in RIOT:
        txt = RIOT[val]
    elif LEN[mode] == 3:
        txt = '$%04X' % val
    else:
        txt = '$%02X' % val
    suffix = {'zpx': ',X', 'abx': ',X', 'zpy': ',Y', 'aby': ',Y'}.get(mode, '')
    if mode == 'ind':
        return '(%s)' % txt
    if mode == 'inx':
        return '(%s,X)' % txt
    if mode == 'iny':
        return '(%s),Y' % txt
    return txt + suffix


out = ['; Tennis (Activision, 1981), desmontado por tools/dis2600.py a partir de reference/tennis.a26',
       '; (build/coverage.json: o que o simulador rodou). Monta nos mesmos 2048 bytes.', '',
       '        processor 6502', '']
for i, n in enumerate(TIA_W):
    out.append('%-15s = $%02X' % (n, i))
for i, n in enumerate(TIA_R):
    out.append('%-15s = $%02X' % (n, i))
for a, n in sorted(RIOT.items()):
    out.append('%-15s = $%04X' % (n, a))
out.append('')
for a, (n, c) in sorted(RAM.items()):
    out.append('%-15s = $%02X%s' % (n, a, '   ; ' + c if c else ''))
out.append('')
# rótulos que caem dentro de uma instrução: equates
for t, l in sorted(labels.items()):
    if not (ORG <= t < ORG + SIZE) or (t in owner and owner[t] != t):
        out.append('%-15s = $%04X' % (l, t))
if TK:
    out.append('%-15s = $%04X   ; src/main.s: desenha o quadro, depois JMP Overscan' % ('TK_FRAME', TK_FRAME))
out += ['', '        ORG $%04X' % (TK_ORG if TK else ORG), '']
a = ORG
data = []


def flush():
    while data:
        chunk = data[:8]
        del data[:8]
        out.append('        .byte ' + ','.join('$%02X' % byte(x) for x in chunk) +
                   ' ' * (40 - 6 * len(chunk)) + '; %04X' % chunk[0])


while a < ORG + SIZE:
    if a in labels:
        flush()
        if a in NAMES and NAMES[a][1]:
            out += ['', '; ' + NAMES[a][1]]
        out.append(labels[a])
    if TK and a == TK_HOOK:
        out.append('        JMP    TK_FRAME                 ; (TK2000: em vez da espera do temporizador e do kernel)')
        a = TK_HOOK_END
        continue
    if a in code:
        flush()
        mn, mode = OPS[byte(a)]
        val = operand(a, mode)
        op = name(a, mn, mode, val)
        if LEN[mode] == 3 and val < 0x100:
            mn += '.w'
        text = '        %-6s %s' % (mn, op)
        raw = ' '.join('%02X' % byte(a + i) for i in range(code[a]))
        out.append('%-40s; %04X  %s' % (text.rstrip(), a, raw))
        a += code[a]
    else:
        data.append(a)
        if len(data) == 8 or a + 1 in labels or a + 1 in code:
            flush()
        a += 1
flush()
open(sys.argv[1], 'w').write('\n'.join(out) + '\n')
print('%d instruções, %d bytes de dados, %d rótulos' % (len(code), SIZE - len(owner), len(labels)))
