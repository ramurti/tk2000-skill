; hello: um programa mínimo para o TK2000, o ponto de partida de um porte.
;
; 1. Texto pela ROM (como o BASIC o mostra): vídeo monocromático, HOME, COUT.
; 2. Depois o jogo é dono da máquina: página 1 da hi-res em cores, um bloco branco movido com as
;    setas (matriz do teclado), um bipe no espaço (alto-falante de 1 bit), um laço de espera para
;    o ritmo (não há timer).

        .setcpu "6502"

KBOUT       = $C000         ; teclado: escreva a máscara da linha ...
KBIN        = $C010         ; ... leia as colunas (o bit 7 é a entrada da fita: descarte-o)
SPEAKER     = $C030         ; qualquer acesso inverte o alto-falante
VCOLOR      = $C050         ; vídeo em cores
VMONO       = $C051         ; vídeo monocromático (texto da ROM nítido)
PAGE1       = $C054         ; mostra a página 1 da hi-res ($2000)
HOME        = $FC58         ; ROM: limpa a tela, cursor no canto superior esquerdo
COUT        = $FDF0         ; ROM: imprime o caractere em A (bit 7 ligado)

; página zero: só depois do texto da ROM (as rotinas de texto da ROM usam boa parte da página zero)
ptr         = $06           ; ..$07 ponteiro da linha da tela
bx          = $08           ; bloco: coluna em bytes (par: 0..38)
by          = $09           ; bloco: linha do topo (0..176)
keys        = $FA           ; teclas apertadas: bit 0 esquerda, 1 direita, 2 cima, 3 baixo, 4 espaço
tmp         = $FB
rows        = $FC

BLOCK_H     = 16

        .segment "CODE"
Start:
        cld
        ldx     #$FF
        txs
        sta     PAGE1

        ; --- 1. texto da ROM ---
        sta     VMONO
        jsr     HOME
        lda     #<Text              ; (aqui sem ponteiro na página zero: o operando de endereço do
        sta     @addr               ; lda abaixo é avançado no próprio código)
        lda     #>Text
        sta     @addr+1
@char:  lda     Text
@addr   = @char + 1
        beq     @wait
        ora     #$80
        jsr     COUT
        inc     @addr
        bne     @char
        inc     @addr+1
        bne     @char
@wait:  jsr     ReadKeys            ; espera o espaço (apertado, depois solto)
        lda     keys
        and     #$10
        beq     @wait
:       jsr     ReadKeys
        lda     keys
        bne     :-

        ; --- 2. o jogo ---
        sta     VCOLOR
        jsr     ClearPage1
        lda     #18
        sta     bx
        lda     #88
        sta     by
        lda     #$7F                ; branco: os 7 pixels acesos, bit de paleta 0
        jsr     DrawBlock
Loop:   jsr     ReadKeys
        lda     keys
        and     #$0F                ; uma seta: apaga, move, desenha
        beq     @space
        lda     #0
        jsr     DrawBlock
        lsr     keys                ; esquerda
        bcc     :+
        lda     bx
        beq     :+
        dec     bx
        dec     bx                  ; (colunas pares: sem franjas de cor)
:       lsr     keys                ; direita
        bcc     :+
        lda     bx
        cmp     #38
        bcs     :+
        inc     bx
        inc     bx
:       lsr     keys                ; cima
        bcc     :+
        lda     by
        cmp     #4
        bcc     :+
        sbc     #4
        sta     by
:       lsr     keys                ; baixo
        bcc     :+
        lda     by
        cmp     #192 - BLOCK_H
        bcs     :+
        adc     #4
        sta     by
:       lsr     keys                ; (espaço: agora no bit 0)
        lda     #$7F
        jsr     DrawBlock
        jmp     @pace
@space: lda     keys
        and     #$10
        beq     @pace
        jsr     Beep
@pace:  jsr     Delay               ; ~20 ms por passo: não há timer, então o tempo é gasto
        jmp     Loop                ; de propósito (um jogo conta os seus ciclos no lugar disso)

; keys = as setas e o espaço que estão apertados (matriz do teclado: KeyRow / KeyMask)
ReadKeys:
        ldx     #4
@key:   lda     KeyRow,x
        sta     KBOUT
        lda     KBIN
        and     KeyMask,x
        cmp     #1                  ; C = apertada
        rol     keys
        dex
        bpl     @key
        lda     #0
        sta     KBOUT
        rts

; preenche o bloco (2 bytes x BLOCK_H linhas em bx, by) com A
DrawBlock:
        sta     tmp
        lda     #BLOCK_H
        sta     rows
        ldx     by
@row:   lda     LineLo,x
        sta     ptr
        lda     LineHi,x
        sta     ptr+1
        ldy     bx
        lda     tmp
        sta     (ptr),y
        iny
        sta     (ptr),y
        inx
        dec     rows
        bne     @row
        rts

ClearPage1:
        lda     #$20
        sta     ptr+1
        lda     #0
        sta     ptr
        tay
:       sta     (ptr),y
        iny
        bne     :-
        inc     ptr+1
        ldx     ptr+1
        cpx     #$40
        bcc     :-
        rts

; um bipe curto: 60 meios períodos de ~1 ms (cerca de 500 Hz)
Beep:
        ldy     #60
@half:  ldx     #200                ; 200 x 5 ciclos
:       dex
        bne     :-
        bit     SPEAKER
        dey
        bne     @half
        rts

; cerca de 20 ms (20 x 256 x 5 ciclos a 1,02 MHz)
Delay:
        ldy     #20
:       ldx     #0
:       dex
        bne     :-
        dey
        bne     :--
        rts

        .segment "RODATA"

; esquerda, direita, cima, baixo, espaço (ReadKeys lê o último primeiro: a entrada n termina no bit n)
KeyRow:     .byte   $08, $10, $40, $20, $04
KeyMask:    .byte   $01, $01, $01, $01, $01

; o endereço na tela de cada linha: $2000 + (y & 7) * $400 + ((y >> 3) & 7) * $80 + (y >> 6) * 40
LineLo:
        .repeat 192, I
        .byte   <($2000 + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * 40)
        .endrep
LineHi:
        .repeat 192, I
        .byte   >($2000 + (I & 7) * $400 + ((I >> 3) & 7) * $80 + (I >> 6) * 40)
        .endrep

Text:   .byte   13, "HELLO, TK2000!", 13, 13
        .byte   "ARROWS MOVE THE BLOCK, SPACE BEEPS.", 13, 13
        .byte   "PRESS SPACE", 0
