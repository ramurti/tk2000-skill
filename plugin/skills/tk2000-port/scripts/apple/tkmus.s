; Sky Fox no TK2000: a música do título no alto-falante (escolhas do dono do projeto, 26/11/2026:
; só a melodia, o tema do começo tocado 2 vezes, metade de cada quadro tocando; depois a música para e a
; animação volta à velocidade do Apple)
; Montado em $DD80, no fim do t25 (zeros no disco, nada escreve ali na abertura); tools/sfrelocs.py põe os
; bytes no t25 (CODE) e troca a entrada $D006 (jmp $D15F) por jmp MUS.
;
; A abertura desenha ~10,8 quadros por segundo sem folga; a cada quadro (a entrada $D006, chamada uma vez
; por quadro) MUS toca JANELA unidades de 8 ciclos da melodia e depois adianta o relógio da música em
; DESENHO unidades (o tempo que o quadro leva para ser desenhado): a música fica picotada, mas no
; andamento da placa. Só com $A97E negativo (a animação; o menu do t25 passa por aqui com ele positivo).
;
; Tempo em unidades de 8 ciclos: o meio período de uma nota do AY de período p é 8p ciclos = p unidades;
; a batida (0,1305 s) = 16.640 unidades = 65 * 256: a tabela guarda o byte alto da duração.

SPKR    = $C030
ANIM    = $A97E                 ; o L497E do Apple: negativo na animação da abertura
VOLTA   = $D15F
SCNT    = $64E9                 ; a contagem da varredura do teclado da camada (src/tklayer.s)
TKKEY   = $6212                 ; a leitura do teclado da camada (X e Y ficam)                 ; o destino original da entrada $D006

JANELA  = 11875                 ; 95 mil ciclos tocando por quadro
VEZES   = 2                     ; quantas vezes o tema toca (escolha do dono do projeto)
DESENHO = 11855                 ; ~94,8 mil ciclos por quadro desenhando (medido no Apple)

        .org    $DD80

MUS:    bit     ANIM
        bpl     @nao
        jsr     LER             ; a cada quadro da animação, com ou sem música
        bit     FIM
        bpl     @toca
@nao:   jmp     VOLTA
@toca:  txa
        pha
        tya
        pha
        lda     #<JANELA
        sta     WL
        lda     #>JANELA
        sta     WH
; um meio período (o caminho comum): 81 ciclos fora da espera + 13 dex (26) + a espera 8 (PER - 13) - 1
; = 8 PER + 2
@meio:  lda     NL              ; 4
        ora     NH              ; 4
        bne     @tem            ; 3
        jsr     PROX
        bit     FIM
        bmi     @sai            ; o tema já tocou VEZES vezes
@tem:   lda     NH              ; 4
        cmp     #2              ; 2: os últimos 512 (4 ms) em silêncio, para separar as notas
        bcc     @mudo           ; 2
        bit     SPKR            ; 4
@mudo:  ldx     PER             ; 4
        dex                     ; 2 x13: o meio período fica 8 PER + 2 ciclos
        dex
        dex
        dex
        dex
        dex
        dex
        dex
        dex
        dex
        dex
        dex
        dex
@esp:   bit     $00             ; 3 \
        dex                     ; 2  > 8 por volta, 7 na última
        bne     @esp            ; 3 /
        sec                     ; 2: N -= PER (fica 0 se passar)
        lda     NL              ; 4
        sbc     PER             ; 4
        sta     NL              ; 4
        lda     NH              ; 4
        sbc     #0              ; 2
        sta     NH              ; 4
        bcs     @w              ; 3
        lda     #0
        sta     NL
        sta     NH
@w:     sec                     ; 2: a janela -= PER
        lda     WL              ; 4
        sbc     PER             ; 4
        sta     WL              ; 4
        lda     WH              ; 4
        sbc     #0              ; 2
        sta     WH              ; 4
        bcs     @meio           ; 3
; o quadro vai ser desenhado: o relógio da música anda DESENHO unidades
        lda     #<DESENHO
        sta     WL
        lda     #>DESENHO
        sta     WH
@pula:  lda     NL              ; cabe na nota atual?
        cmp     WL
        lda     NH
        sbc     WH
        bcc     @prox           ; N < W: a nota acaba durante o desenho
        lda     NL
        sbc     WL              ; C = 1
        sta     NL
        lda     NH
        sbc     WH
        sta     NH
@sai:   pla
        tay
        pla
        tax
        jmp     VOLTA
@prox:  lda     WL              ; W -= N, a próxima nota
        sec
        sbc     NL
        sta     WL
        lda     WH
        sbc     NH
        sta     WH
        jsr     PROX
        bit     FIM
        bmi     @sai
        jmp     @pula

; a próxima nota (no fim do tema: de novo, ou FIM depois de VEZES vezes)
PROX:   ldy     IDX
        cpy     #NNOTAS
        bcc     @ok
        dec     VOLTAS
        bne     @de0
        lda     #$80
        sta     FIM
        rts
@de0:   ldy     #0
@ok:    jsr     LER             ; e a cada nota: um toque rápido numa tecla não se perde
        lda     TPER,y
        sta     PER
        lda     TLEN,y
        sta     NH
        lda     #0
        sta     NL
        iny
        sty     IDX
        rts

VOLTAS: .byte   VEZES
FIM:    .byte   0               ; $80: a música acabou
; lê o teclado de verdade agora (a camada só varre a matriz a cada 8 leituras; a abertura lê uma vez por
; quadro e um toque rápido se perdia): a tecla nova vai para o latch KEY, que a abertura vê no próximo quadro
LER:    lda     #1
        sta     SCNT
        jmp     TKKEY

IDX:    .byte   0
PER:    .byte   0
NL:     .byte   0
NH:     .byte   0
WL:     .byte   0
WH:     .byte   0

        .include "tkmus-tab.inc"
