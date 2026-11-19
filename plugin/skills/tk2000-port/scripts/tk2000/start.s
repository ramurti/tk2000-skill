; A tela de abertura (tools/mkstart.py: src/start.inc), a entrada do programa depois da carga ($401E,
; Boot): o título em vermelho, as faixas do pôr do sol, as teclas (em português), o som dos outros
; carros e os créditos na página 1 de hi-res; S muda o som dos outros carros (oppSnd: normal, curto,
; mudo); RETURN (ou SPACE) começa uma partida: Start, o reset do jogo mantido nos primeiros tiques
; (holdReset, ReadKeys).
; Os pixels do texto são desenhados invertendo pares de pixels sobre preto (FlipP, como os morros):
; branco com uma máscara de $7F, vermelho com os bits do padrão vermelho em bytes cujo bit de
; paleta é ligado antes.

Boot:
        sei
        cld
        ldx     #$FF
        txs
        jsr     MakeLines
        lda     #0
        sta     pageBit
        ldx     #0
        ldy     #192
        jsr     FillBlack
        sta     VCOLOR
        sta     PAGE1
        ldy     #40                 ; as máscaras: branco (SkyRow), vermelho (SkyRow + 41)
:       lda     #$7F
        sta     SkyRow,y
        tya
        lsr
        lda     #$2A
        bcc     :+
        lda     #$55
:       sta     SkyRow+41,y
        dey
        bpl     :--
        lda     #<StartBands        ; as faixas: duas linhas cada, o padrão delas pela paridade da linha
        sta     src
        lda     #>StartBands
        sta     src+1
        lda     #BAND_ROW
        sta     row
@brow:  ldx     row
        lda     LineLo,x
        sta     ptr
        lda     LineHi,x
        sta     ptr+1
        txa
        and     #1
        asl
        asl
        sta     t0
        ldx     #0
@bcol:  txa
        and     #3
        ora     t0
        tay
        lda     (src),y
        pha
        txa
        tay
        pla
        sta     (ptr),y
        inx
        cpx     #40
        bne     @bcol
        inc     row
        lda     row
        sec
        sbc     #BAND_ROW
        cmp     #2 * BANDS
        beq     @text
        lsr
        bcs     @brow
        lda     src
        clc
        adc     #8
        sta     src
        bcc     @brow
        inc     src+1
        bne     @brow
@text:  lda     #<StartText
        sta     src
        lda     #>StartText
        sta     src+1
        jsr     DrawText
        jsr     ShowOpt
        jmp     StartKeys

; os textos em src, até uma linha de $FF
DrawText:
@str:   ldy     #0                  ; um texto: linha, par, pares e linhas por pixel, vermelho?
        lda     (src),y
        cmp     #$FF
        bne     :+
        rts
:       sta     sRow
        iny
        lda     (src),y
        sta     cPair
        iny
        lda     (src),y
        sta     sSx
        iny
        lda     (src),y
        sta     sSy
        iny
        lda     (src),y
        sta     sRed
        iny
        lda     (src),y
        sta     sStep
        lda     src
        clc
        adc     #6
        sta     src
        bcc     :+
        inc     src+1
:       lda     #<SkyRow            ; a máscara dele
        ldx     #>SkyRow
        ldy     sRed
        beq     :+
        lda     #<(SkyRow + 41)
        ldx     #>(SkyRow + 41)
:       sta     gp
        stx     gp+1
        lda     sRed                ; vermelho: bits de paleta das linhas dele ligados
        beq     @chr
        lda     sSy                 ; (7 * linhas por pixel)
        asl
        asl
        asl
        sec
        sbc     sSy
        clc
        adc     sRow
        sta     t0
        ldx     sRow
@red:   lda     LineLo,x
        sta     ptr
        lda     LineHi,x
        sta     ptr+1
        lda     #$80
        ldy     #39
:       sta     (ptr),y
        dey
        bpl     :-
        inx
        cpx     t0
        bne     @red
@chr:   ldy     #0                  ; um glifo ($FF: o fim do texto)
        lda     (src),y
        inc     src
        bne     :+
        inc     src+1
:       cmp     #$FF
        bne     @gl
        jmp     @str
@gl:
        sta     t0                  ; as linhas dele: StartGlyphs + 7 * glifo (16 bits: passando de 36
        lda     #0                  ; glifos passa de 255), no endereço de @gb
        sta     gHi
        lda     t0
        asl
        rol     gHi
        asl
        rol     gHi
        asl
        rol     gHi
        sec
        sbc     t0
        bcs     :+
        dec     gHi
:       clc
        adc     #<StartGlyphs
        sta     @gb+1
        lda     gHi
        adc     #>StartGlyphs
        sta     @gb+2
        lda     #0
        sta     gOff
        lda     sRow
        sta     gRow
        lda     #7
        sta     gy
@gy:    ldx     gOff
@gb:    lda     StartGlyphs,x
        inc     gOff
        asl                         ; bit 4 (o pixel da esquerda) para o bit 7
        asl
        asl
        sta     gBits
        lda     cPair
        sta     pxPair
        lda     #5
        sta     gPix
@gx:    asl     gBits
        bcc     @gnext
        lda     gRow                ; um pixel: sSx pares em sSy linhas
        sta     dRow2
        lda     sSy
        sta     dyc
@dy:    ldx     dRow2
        lda     LineLo,x
        sta     ptr
        lda     LineHi,x
        sta     ptr+1
        lda     pxPair
        sta     pa
        clc
        adc     sSx
        sec
        sbc     #1
        sta     pb
        jsr     FlipP
        inc     dRow2
        dec     dyc
        bne     @dy
@gnext: lda     pxPair
        clc
        adc     sSx
        sta     pxPair
        dec     gPix
        bne     @gx
        lda     gRow
        clc
        adc     sSy
        sta     gRow
        dec     gy
        bne     @gy
        lda     cPair               ; o próximo glifo: sStep pares adiante
        clc
        adc     sStep
        sta     cPair
        jmp     @chr
; as teclas: primeiro nenhuma apertada, depois RETURN ou SPACE (uma partida) ou S (a próxima opção de som)
StartKeys:
@wait:  ldx     #2
:       lda     KeyRow,x
        sta     KBOUT
        lda     KBIN
        and     KeyBit,x
        bne     @wait
        dex
        bpl     :-
@key:   lda     #$80                ; RETURN
        sta     KBOUT
        lda     KBIN
        lsr
        bcs     @go
        lda     #$04                ; SPACE
        sta     KBOUT
        lda     KBIN
        lsr
        bcs     @go
        lda     #$02                ; S
        sta     KBOUT
        lda     KBIN
        and     #$10
        beq     @key
        ldx     oppSnd
        inx
        cpx     #OPTS
        bcc     :+
        ldx     #0
:       stx     oppSnd
        jsr     ShowOpt
        jmp     @wait
@go:    lda     #10                 ; o reset do jogo mantido por 10 tiques: uma partida começa
        sta     holdReset
        jmp     Start

KeyRow:     .byte   $80, $04, $02       ; RETURN, SPACE, S: a linha (KBOUT) e o bit (KBIN) de cada uma
KeyBit:     .byte   $01, $01, $10

; o texto da opção de som: os bytes dele apagados, depois o texto
ShowOpt:
        ldx     #OPT_ROW
@row:   lda     LineLo,x
        sta     ptr
        lda     LineHi,x
        sta     ptr+1
        lda     #0
        ldy     #OPT_BYTE
:       sta     (ptr),y
        iny
        cpy     #40
        bne     :-
        inx
        cpx     #OPT_ROW + 14
        bne     @row
        ldx     oppSnd
        lda     StartOptLo,x
        sta     src
        lda     StartOptHi,x
        sta     src+1
        jmp     DrawText
