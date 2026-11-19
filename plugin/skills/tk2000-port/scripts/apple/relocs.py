"""O que muda nos bytes do original para o mapa de memória do TK2000 (usado por disa2.py --tk).

O TK2000 mostra a página 2 de hi-res a partir de $A000, o Apple a partir de $4000. O porte troca
as duas áreas de 8K: a página 2 do Apple ($4000-$5FFF) vai para $A000-$BFFF, e o que o Apple guarda
em $A000-$BFFF (o fim do arquivo D, os overlays, o carregador do disco) vai para $4000-$5FFF
(disa2.reloc). Operandos de código acompanham os rótulos; os bytes abaixo são os que montam
endereços em tempo de execução, achados com tools/taint.py e conferidos com tools/lockstep.py:

PG: deslocamentos de página. O jogo desenha na página 1 ou 2 somando $20 a um endereço da página 1
    ($2000 -> $4000; $F4 = 0 ou $20); no TK2000 o deslocamento é $80 ($2000 -> $A000).
HI: bytes altos de endereços dentro das duas áreas (imediatos e tabelas de dados): XOR $E0.
    Também, do tools/records.py, os dos registros de objetos (gráficos de quadros, tratadores).
    Achados com tools/taint.py (em execução) e tools/immscan.py (padrões LDA #hi / STA).
"""

PG = {
    'C': [0x193A, 0x1B2E, 0x1B41],
    'D': [0x7304, 0x730D, 0x7401, 0x7557, 0x8033, 0x80E3, 0x8133, 0x817F, 0x81F2, 0x821D,
          0x82B4, 0x82CA, 0x831A, 0x833B, 0x8AD2],
}

HI = {
    'C': [0x1B78, 0x1F57, 0x1F8D],
    'D': [0x721D, 0x721E, 0x721F, 0x722C, 0x793B, 0x7947, 0x8375, 0x86ED,
          0x892D, 0x8977, 0x8987, 0x8A1C, 0x8A2C, 0x93B4, 0x93B5, 0x93B6, 0x93B7,
          0x93B8, 0x93B9, 0x93BA, 0x93C0, 0x93C3, 0x93C4, 0x93C5, 0x93EC, 0x93ED, 0x94B6,
          0x9510, 0x952C, 0x952D, 0x953E, 0x953F, 0x9551, 0x9567, 0x9583, 0x9584, 0x95B8,
          0x95B9, 0x95BA, 0x95CA, 0x95CB, 0x95CC, 0x95E6, 0x95FC, 0x9617, 0x9626, 0x962E,
          0x962F, 0x9645, 0x9646, 0x9654, 0x965B, 0x966D, 0x9675, 0x9676, 0x9686, 0x968C,
          0x969D, 0x96A5, 0x96A6, 0x96BC, 0x96D8, 0x96D9, 0x9726],
    'G': [0xAB01, 0xAB1E, 0xAB35, 0xACE4, 0xAD00, 0xAD21, 0xAD58, 0xAD69, 0xAD7A, 0xAD94,
          0xADB4, 0xADC5, 0xADF1, 0xAE28, 0xAE2A, 0xAE31, 0xAE3D, 0xAE3F, 0xAE49, 0xAE4A,
          0xAE51, 0xAE53, 0xAE61, 0xAE63, 0xAE6F, 0xAE71, 0xAE78, 0xAE81, 0xAE82, 0xAE83,
          0xAE84, 0xAE89, 0xAE8B, 0xAE92, 0xAE9B, 0xAE9C, 0xAE9D, 0xAE9E, 0xAEA5, 0xAEA7,
          0xAEB4],
    'I': [0xAB05, 0xAC00, 0xACA5],
    'J': [0xADAE, 0xADD5, 0xAF30, 0xAF32, 0xAF41, 0xAF42, 0xAF4D, 0xAF4F, 0xAF66, 0xAF68,
          0xAF75, 0xAF80, 0xAF82, 0xAF90, 0xB069, 0xB085, 0xB114, 0xB125, 0xB148, 0xB181,
          0xB1A7, 0xB1CE, 0xB1EF, 0xB267],
    'K': [0xAB05, 0xAB21, 0xAB44, 0xAB7B, 0xAB8E, 0xAB9F, 0xABB9, 0xABDB, 0xABEC, 0xAC18],
    'L': [0xAD2E, 0xADC0, 0xADE8, 0xAE0B, 0xAE1E, 0xAEC2, 0xAF8E, 0xAF9F, 0xAFBD, 0xAFCE,
          0xB01C, 0xB066, 0xB0C7, 0xB0F9, 0xB12D, 0xB166, 0xB92C, 0xB92E, 0xB935, 0xB93C,
          0xB941, 0xB943, 0xB94A, 0xB94F, 0xB950],
    'M': [0xAC88, 0xACA9, 0xACC8, 0xACF8],
    'N': [0xABA2, 0xABEE, 0xABF1, 0xACA9, 0xAD28, 0xAD73,
          0xAD77, 0xAD7B, 0xAD7F, 0xAD83, 0xAD87, 0xAD8B, 0xAD8F, 0xAD93, 0xAD97, 0xAD9B,
          0xAD9F, 0xAFC6, 0xAFE9, 0xAFF5, 0xB018, 0xB066, 0xB0C7, 0xB0F9]
    # os textos das opções (N $ABB4: Y = a opção, X = o valor dela): três tabelas de 4
    # ponteiros, bytes altos; só alguns apareceram em execução (SPACE no menu: os outros)
    + list(range(0xABFE, 0xAC02)) + list(range(0xAC06, 0xAC0A)) + list(range(0xAC0E, 0xAC12)),
}

# Os números aleatórios (C $187B) são bytes de D lidos em $6600-$677E, onde o código do porte
# é diferente (operandos relocados): o porte lê em vez disso uma cópia dos bytes originais em $5E00
# (a área do carregador de disco do Apple, desnecessária no TK2000).
RNG_FROM, RNG_TO, RNG_LEN = 0x6600, 0x5E00, 0x200
OTHER = {
    'C': {0x18A3: 0x60 - ((RNG_FROM - RNG_TO) >> 8)},
}


def rng_copy(d_bytes):
    """a cópia dos bytes de D que os números aleatórios leem (entra: os bytes do arquivo D original)"""
    return d_bytes[RNG_FROM - 0x6000:RNG_FROM - 0x6000 + RNG_LEN]


# A E/S do Apple que o TK2000 não tem, no código de C, D e G (padrões de bytes: achados também
# em código que o desassemblador deixou como dados): para a tabela de saltos do src/tk.s em $5B00, ou nada.
TK = 0x5B00
IO = {
    (0xAD, 0x00): (0x20, 0x03),     # LDA KBD -> JSR KbdRead
    (0xAD, 0x10): (0x20, 0x06),     # LDA KBDSTRB -> JSR KbdStrobe
    (0x8D, 0x10): (0x20, 0x06),     # STA KBDSTRB -> JSR KbdStrobe (preserva A e as flags)
    (0xAD, 0x61): (0xAD, 0x0C),     # LDA BUTN0 -> LDA btn0
    (0xAD, 0x62): (0xAD, 0x0D),     # LDA BUTN1 -> LDA btn1
    (0x0D, 0x62): (0x0D, 0x0D),     # ORA BUTN1 -> ORA btn1
    (0xAD, 0x70): (0xAD, 0x0C),     # LDA PTRIG -> LDA btn0 (nada)
}
SWITCH = (0x50, 0x51, 0x52, 0x57)   # TXTCLR, TXTSET, MIXCLR, HIRES (TK2000: cor, mono, fita)
                                    # -> NOPs: o src/tk.s define cor/mono (LoadFile, Start)
PADDLES = 0x1CA8                    # C: a leitura do paddle -> JMP Paddles
KEYBOARD = 0x1BDB                   # C: CMP #$01 (o controle do jogador, $0201: 0 joystick,
                                    # 1 teclado, 2 computador) -> CMP #$03: o KEYBOARD do menu
                                    # joga como JOYSTICK (o joystick do TK2000 são as setas dele)
SKILL_RET = 0xAF7E                  # N: RETURN na habilidade (LDY $14 / CPY #1 / BEQ: só
                                    # depois de um dígito) -> JMP SkillReturn: RETURN sozinho mantém
                                    # o nível
HIT = 0x6FBB                        # D: CPX $04A2 (o ataque do jogador atingiu o inimigo X) ->
                                    # JSR HitSound (um som curto, depois o CPX)
DEATH = 0x8044                      # D: LDA #0 / STA $047D (o jogador morre: energia 0,
                                    # a queda) -> JSR DeathSound (um som, depois o mesmo) / NOPs
BOSS = 0x815E                       # D: LDA #$FF / STA $04A2 (a energia do chefe é 0: acabou o
                                    # chefe) -> JSR BossSound (uma fanfarra, depois o mesmo) / NOPs
THUD = 0x7FFB                       # D: JSR $8009 (um golpe de inimigo tira energia do jogador;
                                    # não o fim do andar, onde a energia restante vira pontos)
                                    # -> JSR ThudSound (um som, depois $8009)
TIME_UP = 0x7D44                    # D: JSR $8044 (o tempo acabou: morte) -> JSR TimeUp
                                    # (não com nunca morrer, CTRL-N)
HELP_LINE = 0xAEA1                  # N: a ajuda das teclas de função, "<CTRL-S> - SWITCH SOUND
                                    # ON/OFF" (sem CTRL-S no porte) -> CTRL-N, nunca morrer
HELP_TEXT = ' <CTRL-N> - NEVER DIE ON/OFF  '
NEXT_FLOOR = 0x851F                 # D: JSR $1EF3 (o fim do andar: o próximo andar) ->
                                    # JSR FloorMusic (a música no andar novo, depois $1EF3)
MAIN_LOOP = 0x04D5                  # C: LDA $04AF (o topo do laço principal, a cada quadro) ->
                                    # JSR MusicCheck (a música do título na primeira tela
                                    # da demo, depois o mesmo)
NEW_GAME = 0x04EF                   # C: LDA #$C7 / JSR $8689 (depois do menu de opções: G
                                    # carregado, a partida começa) -> JSR NewGame / NOPs (G carregado,
                                    # depois a carta do fliperama, src/letter.s)


TEXT_CODES = {' ': 0x23, '-': 0x2B, '/': 0x30, '<': 0x34, '>': 0x35}     # os caracteres do jogo
                                    # (dígitos 0-9, letras a partir de 10)


def improvements(name, base, data):
    """as mudanças do porte no próprio jogo (não E/S)"""
    out = {}
    if name == 'C':
        assert bytes(data[MAIN_LOOP - base:MAIN_LOOP - base + 3]) == bytes([0xAD, 0xAF, 0x04])
        for k, v in enumerate((0x20, 0x20, TK >> 8)):
            out[MAIN_LOOP + k] = v
        assert bytes(data[NEW_GAME - base:NEW_GAME - base + 5]) == bytes([0xA9, 0xC7, 0x20, 0x89, 0x86])
        for k, v in enumerate((0x20, 0x29, TK >> 8, 0xEA, 0xEA)):
            out[NEW_GAME + k] = v
    if name == 'N':
        assert data[HELP_LINE - base - 1] == 0xFF and data[HELP_LINE - base + len(HELP_TEXT)] == 0xFF
        for k, c in enumerate(HELP_TEXT):
            out[HELP_LINE + k] = TEXT_CODES.get(c) if c in TEXT_CODES else (
                int(c) if c.isdigit() else ord(c) - 55)
        assert bytes(data[SKILL_RET - base:SKILL_RET - base + 6]) == bytes([0xA4, 0x14, 0xC0, 0x01, 0xF0, 0x21])
        for k, v in enumerate((0x4C, 0x11, TK >> 8, 0xEA, 0xEA, 0xEA)):
            out[SKILL_RET + k] = v
    if name == 'D':
        assert bytes(data[TIME_UP - base:TIME_UP - base + 3]) == bytes([0x20, 0x44, 0x80])
        for k, v in enumerate((0x20, 0x23, TK >> 8)):
            out[TIME_UP + k] = v
        assert bytes(data[HIT - base:HIT - base + 3]) == bytes([0xEC, 0xA2, 0x04])
        for k, v in enumerate((0x20, 0x14, TK >> 8)):
            out[HIT + k] = v
        assert bytes(data[DEATH - base:DEATH - base + 5]) == bytes([0xA9, 0x00, 0x8D, 0x7D, 0x04])
        for k, v in enumerate((0x20, 0x17, TK >> 8, 0xEA, 0xEA)):
            out[DEATH + k] = v
        assert bytes(data[BOSS - base:BOSS - base + 5]) == bytes([0xA9, 0xFF, 0x8D, 0xA2, 0x04])
        for k, v in enumerate((0x20, 0x1A, TK >> 8, 0xEA, 0xEA)):
            out[BOSS + k] = v
        assert bytes(data[NEXT_FLOOR - base:NEXT_FLOOR - base + 3]) == bytes([0x20, 0xF3, 0x1E])
        for k, v in enumerate((0x20, 0x26, TK >> 8)):
            out[NEXT_FLOOR + k] = v
        assert bytes(data[THUD - base:THUD - base + 3]) == bytes([0x20, 0x09, 0x80])
        for k, v in enumerate((0x20, 0x1D, TK >> 8)):
            out[THUD + k] = v
    return out


def io_patches(name, base, data):
    out = improvements(name, base, data)
    if name not in ('C', 'D', 'G'):
        return out
    for i in range(len(data) - 2):
        if data[i + 2] != 0xC0:
            continue
        key = (data[i], data[i + 1])
        if key in IO:
            op, lo = IO[key]
            out[base + i] = op
            out[base + i + 1] = lo
            out[base + i + 2] = TK >> 8
        elif data[i] == 0xAD and data[i + 1] in SWITCH:
            for k in range(3):
                out[base + i + k] = 0xEA
    if name == 'C':
        for k, v in enumerate((0x4C, 0x09, TK >> 8)):
            out[PADDLES + k] = v
        assert data[KEYBOARD - base] == 0x01
        out[KEYBOARD] = 0x03
    return out


def patches(name, base, data, io=False):
    """{address: new byte} para um arquivo (io: também a E/S do TK2000)"""
    import records
    out = {}
    his = set(HI.get(name, [])) | set(records.hi_bytes().get(name, {}))
    for a in PG.get(name, []):
        v = data[a - base]
        assert v == 0x20, '%s $%04X: $%02X não é um deslocamento de página' % (name, a, v)
        out[a] = 0x80
    for a in sorted(his):
        v = data[a - base]
        assert 0x40 <= v < 0x60 or 0xA0 <= v < 0xC0, '%s $%04X: $%02X não é um byte alto ali' % (name, a, v)
        out[a] = v ^ 0xE0
    out.update(OTHER.get(name, {}))
    if io:
        out.update(io_patches(name, base, data))
    return out
