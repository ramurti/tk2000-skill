; Sky Fox no TK2000: sons refeitos no alto-falante (escolhas do dono do projeto, 26/11/2026)
; Montado em $6A93, no lugar do tratador de interrupção da Mockingboard do t7 ($6A93-$6B19), que no
; TK2000 nunca roda (não há placa); tools/sfrelocs.py põe os bytes no t7 (CODE). Variáveis e tabelas
; no vão da camada ($64E0-$64FD, src/tklayer.s).
;
; A turbina (opção B: o tom mais alto da placa, sujo de ruído): na tela "Prepare To Launch" (t21 $7516)
; e na escolha da altitude, o jogo espera o FIRE num laço apertado que chama $7772 milhares de vezes
; por segundo. Cada chamada passa por TURB, que calcula uma amostra: o tom (acumulador de fase de 8
; bits), o volume (largura do pulso: ligado enquanto a fase < VOLW, dentro do meio período) e o ruído
; (LFSR de 8 bits, inverte a saída em 1/4 das amostras); troca o cone quando a saída muda. A subida
; (como na placa: período 76 -> 49 em passos de 3, volume 0 -> 15) anda um passo a cada TPASSO*256
; chamadas.

SPKR    = $C030
FIRE    = $7772                 ; a leitura do FIRE do t21 (devolve os flags)

PHH     = $64E0
INCH    = $64E1
VOLW    = $64E2
TSTEP   = $64E3
LF      = $64E4
LAST    = $64E5
TCL     = $64E6
TCH     = $64E7
OUT     = $64E8
TINC    = $64EA                 ; 10 passos: o incremento de fase por chamada
TVOL    = $64F4                 ; 10 passos: a largura do pulso (0 = silêncio)

NPASSOS = 10
TPASSO  = 6                     ; 6*256 chamadas por passo (~0,32 s a ~4,85 mil chamadas por segundo, medido)

        .org    $6A93

; t21 $7516 (lda #$06 / sta $30): o começo da tela; a turbina recomeça do silêncio
TURB0:  lda     #$00
        sta     TSTEP
        sta     VOLW
        lda     #$06
        sta     $30
        rts

; no lugar de jsr $7772: uma amostra da turbina, depois a leitura do FIRE (preserva X e Y)
TURB:   jsr     AMOSTRA
        jmp     FIRE

; uma amostra da turbina (preserva X e Y; A muda): também no desenho do tubo (src/tkdesenho.s)
AMOSTRA:
        inc     TCL
        bne     @fase
        inc     TCH
        lda     TCH
        cmp     #TPASSO
        bcc     @fase
        lda     #$00
        sta     TCH
        txa
        pha
        ldx     TSTEP
        cpx     #NPASSOS
        bcs     @fica
        lda     TINC,x
        sta     INCH
        lda     TVOL,x
        sta     VOLW
        inc     TSTEP
@fica:  pla
        tax
@fase:  clc
        lda     PHH
        adc     INCH
        sta     PHH
        cmp     VOLW            ; C = 0: ligado (a fase ainda no começo do meio período)
        lda     #$00
        ror     a
        sta     OUT
        lda     VOLW
        beq     @sai            ; volume 0: silêncio
        lda     LF
        lsr     a
        bcc     @lf
        eor     #$B8
@lf:    sta     LF
        and     #$03
        cmp     #$03
        bne     @sai
        lda     #$80
        eor     OUT
        sta     OUT
@sai:   lda     OUT
        cmp     LAST
        beq     @fim
        sta     LAST
        bit     SPKR
@fim:   rts
