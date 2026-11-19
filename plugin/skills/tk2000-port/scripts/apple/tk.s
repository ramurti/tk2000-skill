; Kung Fu Master no TK2000: o que substitui o hardware do Apple II que o original usa.
; Em $5B00 (o endereço no TK2000 do carregador de disco do Apple em $BB00, cuja entrada o jogo chama):
;   - LoadFile: os overlays e as imagens, compactados (tools/lz.py) na RAM sob a ROM
;   - o teclado: o latch ASCII do Apple ($C000/$C010) a partir da matriz de teclas do TK2000
;   - o joystick: paddles e botões a partir das setas e de duas teclas
;   - Start: descompacta a memória baixa e salta para o jogo
; As chamadas do original são corrigidas para a tabela de saltos abaixo (tools/relocs.py, IO).

KBOUT       = $C000         ; seleção de linha do teclado (escrita)
KBIN        = $C010         ; colunas do teclado (leitura; bit 7 = fita)
CTRL_OFF    = $C05E
CTRL_ON     = $C05F
COLOUR      = $C050
MONO        = $C051
ROMSEL      = $C05A
RAMSEL      = $C05B         ; RAM em $C100-$FFFF (o modelo de 64K)

src         = $00           ; Unlz (a página zero do próprio carregador do Apple: livre durante uma carga)
dst         = $02
flags       = $04
count       = $05
mptr        = $06

        .include "dir.inc"  ; tools/mkimage.py: DIR_* (os arquivos compactados), START_* (registradores),
                            ; SFX_AT (src/sfx.s)

        .org    $5B00

        jmp     LoadFile    ; $5B00: a entrada do carregador do Apple (A = letra do arquivo | $80)
        jmp     KbdRead     ; $5B03: LDA $C000
        jmp     KbdStrobe   ; $5B06: LDA/STA $C010
        jmp     Paddles     ; $5B09: a leitura dos paddles (C $1CA8)
btn0:   .byte   0           ; $5B0C: botão 0 (bit 7), lido no lugar de $C061
btn1:   .byte   0           ; $5B0D: botão 1 (bit 7), lido no lugar de $C062
        jmp     Start       ; $5B0E
        jmp     SkillReturn ; $5B11: N $AF7E (RETURN na habilidade do computador)
        jmp     SFX_AT      ; $5B14: D $6FBB (um ataque atingiu um inimigo): HitSound
        jmp     SFX_AT+3    ; $5B17: D $8044 (o jogador morre): DeathSound
        jmp     SFX_AT+6    ; $5B1A: D $815E (um chefe derrotado): BossSound
        jmp     SFX_AT+9    ; $5B1D: D $7FFB (o jogador atingido): ThudSound
        jmp     SFX_AT+12   ; $5B20: C $04D5 (o topo do laço principal): MusicCheck
        jmp     SFX_AT+18   ; $5B23: D $7D44 (o tempo acabou): TimeUp
        jmp     SFX_AT+21   ; $5B26: D $851F (o próximo andar): FloorMusic
        jmp     NewGame     ; $5B29: C $04EF (depois do menu de opções): G, depois a carta

; --- arquivos: A = letra | $80. Descompacta o arquivo no endereço dele no TK2000 (DIR_DEST) a partir
; da RAM sob a ROM (DIR_SRC); letras desconhecidas são ignoradas (o carregador do Apple teria falhado).
LoadFile:
        and     #$7F
        ldx     #0
        cmp     #'N'                ; o menu de opções (texto): branco, sem as franjas
        bne     :+                  ; de cor; qualquer outro arquivo (o jogo) volta à cor
        sta     MONO
        dex
        bne     LoadLook
:       sta     COLOUR
LoadLook:
        stx     menu
        ldx     #DIR_COUNT-1
@find:  cmp     DirName,x
        beq     @found
        dex
        bpl     @find
        rts
@found: lda     DirSrcLo,x
        sta     src
        lda     DirSrcHi,x
        sta     src+1
        lda     DirDstLo,x
        sta     dst
        lda     DirDstHi,x
        sta     dst+1
        ; (cai no Unlz)

; Descompacta dados do tools/lz.py de (src) para (dst)
Unlz:   ldy     #0
@group: lda     (src),y
        sta     flags
        jsr     @next
        lda     #8
        sta     count
@item:  lsr     flags
        bcs     @match
        lda     (src),y             ; um literal
        sta     (dst),y
        jsr     @next
        jsr     @out
        jmp     @done
@match: lda     (src),y             ; distância, parte baixa
        sta     mptr
        jsr     @next
        lda     (src),y             ; distância alta << 4 | tamanho - 3
        jsr     @next
        pha
        lsr
        lsr
        lsr
        lsr
        sta     mptr+1
        ora     mptr
        bne     :+
        pla                         ; distância 0: o fim
        rts
:       sec                         ; mptr = dst - distância
        lda     dst
        sbc     mptr
        sta     mptr
        lda     dst+1
        sbc     mptr+1
        sta     mptr+1
        pla
        and     #$0F
        clc
        adc     #3
        tax
@copy:  lda     (mptr),y
        sta     (dst),y
        inc     mptr
        bne     :+
        inc     mptr+1
:       jsr     @out
        dex
        bne     @copy
@done:  dec     count
        bne     @item
        beq     @group
@next:  inc     src
        bne     :+
        inc     src+1
:       rts
@out:   inc     dst
        bne     :+
        inc     dst+1
:       rts

; --- teclado: o latch do Apple. KbdRead devolve o código de uma tecla recém-apertada com o bit 7
; ligado até o KbdStrobe; uma tecla mantida apertada é informada uma vez. Flags como LDA. CTRL-N
; não é do jogo: liga e desliga o nunca morrer (src/sfx.s).
CTRL_N      = $8E

KbdRead:
        lda     latch
        bmi     @out
        jsr     Scan
        cmp     held
        beq     @same
        sta     held
        tax
        beq     @same
        cmp     #CTRL_N
        beq     @never
        sta     latch
        rts
@never: jsr     SFX_AT+15           ; NeverDie
        jmp     @same
@same:  lda     latch
@out:   rts

KbdStrobe:                          ; (preserva A e as flags: pontos com STA $C010)
        php
        pha
        lda     latch
        and     #$7F
        sta     latch
        pla
        plp
        rts

; Scan: A = código Apple (| $80) da primeira tecla mapeada apertada, 0 se nenhuma; também os botões
Scan:   jsr     Buttons
        bit     menu                ; no menu de opções: DOWN = RETURN (próxima opção),
        bpl     @keys               ; LEFT/RIGHT = SPACE (muda a opção)
        ldx     #2
@arrow: lda     ArrowRow,x
        sta     KBOUT
        lda     KBIN
        and     #$01
        bne     @isarrow
        dex
        bpl     @arrow
        bmi     @keys
@isarrow:
        lda     #0
        sta     KBOUT
        lda     ArrowCode,x
        rts
@keys:  ldx     #KEYS-1
@key:   lda     KeyRow,x
        sta     KBOUT
        lda     KBIN
        and     KeyCol,x
        bne     @down
        dex
        bpl     @key
        lda     #0
        sta     KBOUT
        rts
@down:  lda     #0
        sta     KBOUT
        lda     KeyCode,x
        cmp     #$C0                ; letras: com CTRL, o código de controle
        bcc     @done
        sta     CTRL_ON
        ldy     KBIN
        sta     CTRL_OFF
        tya
        and     #$01
        beq     @plain
        lda     KeyCode,x
        and     #$9F
        rts
@plain: lda     KeyCode,x
@done:  rts

; Buttons: bit 7 de btn0/btn1 a partir das teclas deles (KeyBtn: linha, coluna)
Buttons:
        lda     #BTN0_ROW
        sta     KBOUT
        lda     KBIN
        and     #BTN0_COL
        cmp     #1                  ; C = apertada
        ror     btn0
        lda     #BTN1_ROW
        sta     KBOUT
        lda     KBIN
        and     #BTN1_COL
        cmp     #1
        ror     btn1
        lda     #0
        sta     KBOUT
        rts

; --- joystick: o original cronometra os paddles (C $1CA8: $0A = x, $0B = y, 0..127, centro
; cerca de 45); aqui a partir das setas. Leva o mesmo tempo que o laço do original (127 passadas
; de 35 ciclos) para o jogo manter a velocidade.
Paddles:
        jsr     Buttons
        ldx     #PAD_MID
        lda     #$08                ; LEFT
        sta     KBOUT
        lda     KBIN
        and     #$01
        beq     :+
        ldx     #PAD_MIN
:       lda     #$10                ; RIGHT
        sta     KBOUT
        lda     KBIN
        and     #$01
        beq     :+
        ldx     #PAD_MAX
:       stx     $0A
        ldx     #PAD_MID
        lda     #$40                ; UP
        sta     KBOUT
        lda     KBIN
        and     #$01
        beq     :+
        ldx     #PAD_MIN
:       lda     #$20                ; DOWN
        sta     KBOUT
        lda     KBIN
        and     #$01
        beq     :+
        ldx     #PAD_MAX
:       stx     $0B
        lda     #0
        sta     KBOUT
        ldx     #PAD_WAIT           ; o resto do tempo do original
:       pha
        pla
        pha
        pla
        dex
        bne     :-
        rts

PAD_MIN     = 0
PAD_MID     = 45
PAD_MAX     = 127
PAD_WAIT    = 226             ; (19 ciclos por passada: cerca de 4.300 ciclos)

latch:  .byte   0
held:   .byte   0
menu:   .byte   0           ; $FF enquanto o menu de opções (arquivo N) está carregado

ArrowRow:  .byte   $20, $08, $10   ; DOWN, LEFT, RIGHT (coluna 1)
ArrowCode: .byte   $8D, $A0, $A0

; Teclas que a versão Apple lê como caracteres (menus e teclas de função): linha, coluna, código
KEYS        = 10
KeyRow: .byte   $04, $80, $08, $08, $08, $08, $08, $20, $80, $04
KeyCol: .byte   $01, $01, $20, $10, $08, $04, $02, $20, $02, $20
KeyCode:.byte   $A0, $8D, $B1, $B2, $B3, $B4, $B5, $9B, $CE, $D1
        ;       SPC  RET  1    2    3    4    5    P=ESC N    Q  (N, Q + CTRL: CTRL-N, CTRL-Q)
        ; (sem S: o CTRL-S, liga/desliga o som, não existe mais; CTRL-N é o nunca morrer do porte)

; Botões: SPACE = botão 0, Z = botão 1 (a confirmar com o dono do projeto)
BTN0_ROW    = $04
BTN0_COL    = $01
BTN1_ROW    = $01
BTN1_COL    = $20

; --- a habilidade do computador no menu lê dígitos, depois RETURN; RETURN sem dígito não fazia nada.
; Aqui ele mantém o nível: o último escolhido ($0256), ou 1, entrado como se digitado, depois RETURN
; (o latch: a próxima tecla do menu).
SKILL       = $0256         ; a habilidade que o menu definiu para a partida
SKILL_DIGITS= $14           ; N: dígitos digitados até agora (0/1)
SKILL_DONE  = $4FA5         ; N $AFA5: RETURN depois de dígitos
SKILL_DIGIT = $4F84         ; N $AF84: uma tecla de dígito (A)

SkillReturn:
        ldy     SKILL_DIGITS
        beq     :+
        jmp     SKILL_DONE
:       lda     #$8D                ; RETURN em seguida
        sta     latch
        lda     SKILL
        beq     @one
        cmp     #6
        bcc     @digit
@one:   lda     #1
@digit: ora     #$B0
        jmp     SKILL_DIGIT


; --- uma partida começa (depois do menu de opções): G carregado como o original fazia, depois a
; carta do fliperama (src/letter.s, em G) até uma tecla, depois volta à cor.
LETTER      = $4B03         ; G $AB03

NewGame:
        jsr     $1B2D               ; C: desenho na página 2 (como D $8689 antes de uma carga)
        lda     #'G'                ; G, sem a troca para cor do LoadFile: o menu fica
        ldx     #0                  ; branco até a carta (mono também)
        jsr     LoadLook
        jmp     LETTER


; --- início: o programa da fita salta para cá. Descompacta a memória baixa do Apple ($0000-$07FF
; no começo do jogo) passando pela página 2 e entra no jogo como o carregador do original fazia ($AB00).
Start:
        cld
        sei
        sta     COLOUR              ; a primeira tela: a demo
        sta     RAMSEL              ; os arquivos compactados: sob a ROM
        lda     #<LOW_PACKED
        sta     src
        lda     #>LOW_PACKED
        sta     src+1
        lda     #$00
        sta     dst
        lda     #$A0
        sta     dst+1
        jsr     Unlz
        ldx     #0
@copy:
.repeat 8, I
        lda     $A000+I*$100,x
        sta     $0000+I*$100,x
.endrepeat
        inx
        bne     @copy
        ldx     #START_SP
        txs
        lda     #START_P
        pha
        lda     #START_A
        ldx     #START_X
        ldy     #START_Y
        plp
        jmp     $4B00               ; (Apple $AB00)

DirName:   .byte   DIR_NAMES
DirSrcLo:  .lobytes DIR_SRC
DirSrcHi:  .hibytes DIR_SRC
DirDstLo:  .lobytes DIR_DST
DirDstHi:  .hibytes DIR_DST
