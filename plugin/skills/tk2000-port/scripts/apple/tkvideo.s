; Sky Fox no TK2000: preto e branco nas telas do computador da base (escolha do dono do projeto, 28/11/2026).
;
; No TK2000 uma letra branca de traço fino sai colorida (os pares de pontos são fixos); no modo preto e
; branco ($C051) cada ponto aceso é branco e as letras ficam como no Apple. Três modos, trocados com CTRL+C
; nas telas do computador da base (C -> B -> A -> C):
;   C (0, o padrão): preto e branco nas telas de texto (relatório, ajuda, placar, $1D = 7..11) e na
;                    briefing; o mapa tático colorido;
;   B (1): preto e branco em todas as telas do computador na base e na briefing;
;   A (2): tudo colorido, como antes.
; Em voo o computador abre dentro da cabine e fica sempre colorido (este código só roda na base).
;
; Fica no começo da página da pilha ($0100: o jogo começa a pilha em $01FF e nenhuma medição passou de
; $01EE); vai no disco junto com a página da pilha (sfrelocs.LAYER). Ligações (tools/sfrelocs.py):
;   t21 $709C  bit $C057 -> jsr VIDEO   (o laço das telas do computador, uma vez por volta)
;   t21 $7288  a tecla $83 (CTRL+C) na posição 5 da tabela de teclas, que leva a CTRLC
;   t25 $D7AC  jsr $5EF8 -> jsr BRIEF   (a briefing, antes da espera)
;   t21 $742A  bit $C057 -> jsr COR     (a saída para o lançamento: de volta às cores)
;   t21 $7585  jsr TDRAW -> jsr TUBO    (o desenho do tubo: de volta às cores)
;   as saídas da base para $4AFB (abertura, CTRL+Q, CTRL+R, fim de jogo) e $D00C: REST1, REST2

SCNT    = $64E9                 ; src/tklayer.s: o contador da varredura do teclado
SCR     = $1D                  ; a tela do computador (0 mapa, 7/8 relatório, 9/10 ajuda, 11 placar...)
DISP    = $7279                 ; t21: o despacho da tela $1D (Y = $1D)
COLOR   = $C050
MONO    = $C051
TDRAW   = $1EEC                 ; src/tkdesenho.s
ESPERA  = $BEF8                 ; rB0 $5EF8 do Apple, no TK2000
ABERT   = $AAFB                 ; r40 $4AFB do Apple, no TK2000
MESMO   = $D00C                 ; t25

        .org    $0100
        jmp     VIDEO           ; $0100
        jmp     CTRLC           ; $0103
        jmp     BRIEF           ; $0106
        jmp     TUBO            ; $0109
        jmp     REST1           ; $010C
        jmp     REST2           ; $010F
        jmp     COR             ; $0112
MODO:   .byte   0               ; $0115
ULT:    .byte   0               ; $0116: a última tela (para voltar a ela depois do CTRL+C)

VIDEO:  pha
        lda     #1              ; a próxima leitura varre o teclado: cada volta deste laço leva até ~0,14 s
        sta     SCNT            ; (placar) e a camada só varre a cada 8 leituras: um toque rápido se perdia
        lda     SCR
        cmp     #5              ; a posição do CTRL+C: o despacho troca o modo e volta à tela de antes
        beq     @fim
        sta     ULT
        lda     MODO
        beq     @c
        cmp     #1
        beq     @mono
@cor:   sta     COLOR
@fim:   pla
        rts
@c:     lda     SCR
        cmp     #7
        bcc     @cor
        cmp     #12
        bcs     @cor
@mono:  sta     MONO
        pla
        rts

CTRLC:  ldy     MODO
        iny
        cpy     #3
        bcc     :+
        ldy     #0
:       sty     MODO
        ldy     ULT
        sty     SCR
        jmp     DISP

BRIEF:  pha
        lda     MODO
        cmp     #2
        beq     :+
        sta     MONO
:       pla
        jmp     ESPERA

TUBO:   sta     COLOR
        jmp     TDRAW

COR:    sta     COLOR           ; a saída para o lançamento (antes do "Prepare To Launch")
        rts

REST1:  sta     COLOR
        jmp     ABERT

REST2:  sta     COLOR
        jmp     MESMO

        .assert * <= $0180, error, "tkvideo passa de $0180 (a pilha)"
