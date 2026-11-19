; Som: os dois canais do original no alto-falante de 1 bit, até agora: no canal 0, o motor (AUDC 3,
; o poly de 4 bits avançando nos 1s do poly de 5 bits) ou os freios (AUDC 8 AUDF 10, o ruído
; branco do poly de 9 bits na taxa dele: escolha A do dono do projeto, tools/brakeprev.py) ou o
; estrondo da batida (AUDC 8 AUDF 8 e 9, na taxa dele: escolha A do dono do projeto,
; tools/crashprev.py; os intervalos do canal 0 vêm de Gap3 ou Gap9: S0Gap0/2/3, escolhidos por
; SndRegs) e, no canal 1, o ruído branco na neve (AUDC 8, à metade da taxa: escolha B do dono do
; projeto, tools/snowprev.py) ou o motor do outro carro mais próximo (AUDC 3 AUDF 12 volume 6;
; escolha B do dono do projeto, tools/oppprev.py; Gap3 ou Gap9: S1Gap1/4) ou o bipe (AUDC 4, um
; tom puro: GapLo1 todo de um período; o canal 0 pausado enquanto isso: escolha B do dono do
; projeto, tools/beepprev.py) ou as músicas (AUDC 12 e 7, o original silencia o canal 0 nessa
; hora: tools/tuneprev.py; os tipos: C1Kind); os outros AUDCs ficam em silêncio. O alto-falante
; troca quando qualquer uma das saídas muda (o XOR delas). Não há temporizador: checkpoints (SND)
; espalhados pelo trabalho, uns dois por ms, descontam de sDue, o tempo até a próxima troca
; agendada, o tempo de CPU desde o anterior (SNDK_nome, em unidades de 8 ciclos, medido por
; tools/sndfit.py: src/sndk.inc); quando ele acaba (SndBorrow, SndEvent) o canal cuja troca venceu
; troca o alto-falante e recebe o tempo até a próxima (sR0, sR1, contado a partir do instante
; agendado; o motor: Gap3 pulsos do período dele, PerT por AUDF, de GapLo/GapHi montados quando
; AUDF muda; o ruído: Gap9 pulsos, GapLo1/GapHi1), e o mais próximo dos dois é agendado (sSch).
; Dentro da lógica de jogo do original, oito ganchos também fazem checkpoints (tools/mktk.py). O
; original ajusta seus registradores uma vez por tique; SndRegs os pega no fim de cada tique
; (TkFrame). Sem volume (AUDV 0: silêncio).

SPKR        = $C030         ; troca o alto-falante
SND_EVENT_K = 14            ; o tempo próprio de uma troca do motor, sozinho (~118 ciclos, unidades de 8 ciclos)
SND_NOISE_K = 16            ; o de uma troca do ruído (~130 ciclos)
SND_TWO_K   = 28            ; o tempo próprio de SndTwo por passada (ajustado: tools/sndfit.py --snow)
AUDC0       = $15           ; as escritas do original na TIA (página zero)
AUDC1       = $16
AUDF0       = $17
AUDF1       = $18
AUDV0       = $19
AUDV1       = $1A
SND_FAR     = $40           ; um canal em silêncio: a próxima troca dele a esta distância (byte alto)

; um checkpoint: passou o tempo de name (SNDK_name); A e os flags se perdem, X e Y são mantidos.
; Só no nível de cima (não dentro de outra macro): tools/sndfit.py os acha na listagem
.macro  SND name
        lda     sDue
        sec
        sbc     #.ident(.concat("SNDK_", .string(name)))
        sta     sDue
        bcs     *+5
        jsr     SndBorrow
.endmacro

; o byte baixo de sDue pediu emprestado: o byte alto desce; abaixo de 0, as trocas venceram; mantém X e Y
SndBorrow:
        dec     sDue+1
        bmi     :+
        rts
:       stx     sX
SndEvent:
        lda     sMode1              ; o ruído ligado: os dois canais (SndTwo)
        bne     SndTwo
        lda     sMode               ; senão o motor sozinho (ou nada): sDue é o tempo dele
        bne     :+
        lda     #SND_FAR
        sta     sDue+1
        ldx     sX
        rts
:       inc     sEvents
        bne     SndTog
        inc     sEvents+1
SndTog: bit     SPKR                ; (tools/sndfit.py: as trocas de SndTog, SndTog1 e SndTog2)
        inc     sGi                 ; o próximo intervalo (são 256)
        ldx     sGi
S0Gap0: lda     Gap3,x
        tax
        lda     sDue                ; (GapLo/GapHi: menos o tempo que isto leva, SND_EVENT_K)
        clc
        adc     GapLo-1,x
        sta     sDue
        lda     sDue+1
        adc     GapHi-1,x
        sta     sDue+1
        bmi     SndEvent
        ldx     sX
        rts

; os dois canais: chegou o instante agendado: o canal agendado (sWho) troca e recebe o tempo até a
; próxima troca; o tempo do outro menos o tempo que passou (os dois agora a partir daqui; abaixo
; de 1: ele troca também); o mais próximo é agendado
SndTwo:
        lda     sWho
        bne     S2Noise
        lda     sR1                 ; a vez do motor: o tempo do ruído menos sSch
        sec
        sbc     sSch
        sta     sR1
        lda     sR1+1
        sbc     sSch+1
        sta     sR1+1
        lda     sMode               ; a troca do motor (como em SndEngine, o tempo dele a partir daqui)
        beq     S2EOff
        inc     sEvents
        bne     SndTog3
        inc     sEvents+1
SndTog3:
        bit     SPKR
        inc     sGi
        ldx     sGi
S0Gap3: lda     Gap3,x
        tax
        lda     GapLo-1,x           ; (GapLo/GapHi menos SND_EVENT_K, devolvido: o tempo de SndTwo
        clc                         ; é SND_TWO_K)
        adc     #SND_EVENT_K
        sta     sR0
        lda     GapHi-1,x
        adc     #0
        sta     sR0+1
        jmp     :+
S2EOff: lda     #SND_FAR
        sta     sR0+1
:       lda     sR1+1               ; o ruído venceu também?
        bmi     :+
        ora     sR1
        bne     S2Sch
:       jsr     SndNoise
        jmp     S2Sch
S2Noise:
        lda     sR0                 ; a vez do ruído: o tempo do motor menos sSch
        sec
        sbc     sSch
        sta     sR0
        lda     sR0+1
        sbc     sSch+1
        sta     sR0+1
        lda     sMode1              ; a troca do ruído (como em SndNoise, o tempo dele a partir daqui)
        beq     S2NOff
        inc     sEvents             ; (contado três vezes: SndTwo custa umas três trocas do
        inc     sEvents             ; motor sozinho)
        inc     sEvents
        bne     SndTog4
        inc     sEvents+1
SndTog4:
        bit     SPKR
        inc     sG9
        ldx     sG9
S1Gap4: lda     Gap9,x
        tax
        lda     GapLo1-1,x
        sta     sR1
        lda     GapHi1-1,x
        sta     sR1+1
        jmp     :+
S2NOff: lda     #SND_FAR
        sta     sR1+1
:       lda     sR0+1               ; o motor venceu também?
        bmi     :+
        ora     sR0
        bne     S2Sch
:       jsr     SndEngine
S2Sch:  ldx     #0                  ; o mais próximo
        lda     sR0
        cmp     sR1
        lda     sR0+1
        sbc     sR1+1
        bcc     :+
        ldx     #2
:       stx     sWho
        lda     sR0,x
        sta     sSch
        clc
        adc     sDue
        sta     sDue
        lda     sR0+1,x
        sta     sSch+1
        adc     sDue+1
        sta     sDue+1
        lda     sDue                ; o tempo que isto levou (SND_TWO_K)
        sec
        sbc     #SND_TWO_K
        sta     sDue
        bcs     :+
        dec     sDue+1
:       lda     sDue+1
        bpl     :+
        jmp     SndTwo
:       ldx     sX
        rts

; (SndTwo, quando o outro canal vence no mesmo instante) a troca do motor: o alto-falante
; trocado, o tempo até a próxima somado a sR0; em silêncio: longe
SndEngine:
        lda     sMode
        bne     :+
        lda     #SND_FAR
        sta     sR0+1
        rts
:       inc     sEvents
        bne     SndTog2
        inc     sEvents+1
SndTog2:
        bit     SPKR
        inc     sGi                 ; o próximo intervalo (são 256)
        ldx     sGi
S0Gap2: lda     Gap3,x
        tax
        lda     sR0                 ; (SND_EVENT_K devolvido, como em SndTwo)
        clc
        adc     GapLo-1,x
        sta     sR0
        lda     sR0+1
        adc     GapHi-1,x
        sta     sR0+1
        lda     sR0
        clc
        adc     #SND_EVENT_K
        sta     sR0
        bcc     :+
        inc     sR0+1
:       rts

; (o mesmo) a troca do ruído: o alto-falante trocado, o tempo até a próxima somado a sR1 (Gap9
; pulsos de dois períodos de AUDF1, metade da taxa da TIA); em silêncio: longe
SndNoise:
        lda     sMode1
        bne     SndTog1
        lda     #SND_FAR
        sta     sR1+1
        rts
SndTog1:
        bit     SPKR
        inc     sEvents
        bne     :+
        inc     sEvents+1
:       inc     sG9                 ; o próximo intervalo (são 256)
        ldx     sG9
S1Gap1: lda     Gap9,x
        tax
        lda     sR1
        clc
        adc     GapLo1-1,x
        sta     sR1
        lda     sR1+1
        adc     GapHi1-1,x
        sta     sR1+1
        rts

; no fim de um tique: os registradores do original
SndRegs:
        lda     AUDC1               ; o bipe (canal 1 AUDC 4): tocado de uma vez, cronometrado (BeepTone),
        and     #$0F                ; quando começa; depois os dois canais em silêncio enquanto dura
        cmp     #4                  ; e BEEP_REST tiques depois (escolha C do dono do projeto)
        bne     @nobeep
        lda     AUDV1
        and     #$0F
        beq     @nobeep
        lda     beepOn
        bne     :+
        inc     beepOn
        jsr     BeepTone
:       lda     #BEEP_REST
        sta     beepRest
        bne     @hush
@nobeep: lda    #0
        sta     beepOn
        lda     beepRest
        beq     :+
        dec     beepRest
@hush:  lda     #0
        sta     sMode
        sta     sMode1
        rts
:       lda     AUDV0               ; canal 0: o motor, os freios, a batida
        and     #$0F
        bne     :+
        jmp     @off0
:
        lda     AUDF0
        and     #$1F
        tax
        lda     AUDC0
        and     #$0F
        cmp     #8
        beq     @noise0
        cmp     #3
        bne     @off0               ; (só o motor, os freios e o estrondo da batida)
        cpx     #8                  ; AUDF 0-7: silêncio (o chiado depois de uma batida, AUDF 0-1 com volume
        bcc     @off0               ; 3, baixinho no 2600, tomaria ~30% da CPU aqui)
        txa
        bcs     @key0
@noise0:
        cpx     #8                  ; o ruído: o estrondo da batida (AUDF 8 e 9 em tiques
        bcc     @off0               ; alternados) e o dos freios (AUDF 10)
        cpx     #11
        bcs     @off0
        txa
        ora     #$80
@key0:  cmp     sF                  ; (sF: AUDF, bit 7 ligado para o ruído)
        beq     @same0
        sta     sF                  ; um período novo: GapLo/GapHi = 1..12 períodos, menos o tempo
        ldx     #<Gap3              ; próprio de uma troca (SND_EVENT_K: fora dos tempos dos checkpoints;
        ldy     #>Gap3              ; o de SndTwo é SND_TWO_K); a tabela de intervalos: Gap3 para o
        asl                         ; motor, Gap9 para o ruído
        bcc     :+
        ldx     #<Gap9
        ldy     #>Gap9
:       stx     S0Gap0+1
        stx     S0Gap2+1
        stx     S0Gap3+1
        sty     S0Gap0+2
        sty     S0Gap2+2
        sty     S0Gap3+2
        lsr
        tax
        lda     PerT,x
        sta     sPer
        ldx     #0
        ldy     #$FF
        lda     #<-SND_EVENT_K
@mul:   clc
        adc     sPer
        sta     GapLo,x
        bcc     :+
        iny
:       pha
        tya
        sta     GapHi,x
        pla
        inx
        cpx     #12
        bne     @mul
@same0: lda     sMode
        bne     @ch1
        lda     #3                  ; estava em silêncio: liga
        sta     sMode
        ldy     #0
        lda     sPer
        jsr     SndOn
        jmp     @ch1
@off0:  lda     #0
        sta     sMode
        jmp     @ch1
@off1:  lda     #OPP_SHORT          ; (o som dos outros carros desligado: o próximo curto de novo)
        sta     oppLeft
@hush1: lda     #0
        sta     sMode1
        rts
@ch1:   lda     AUDV1               ; canal 1: os outros carros, o bipe, as músicas, a neve
        and     #$0F
        beq     @off1
        tay
        lda     AUDC1
        and     #$0F
        tax
        lda     C1Kind,x            ; o tipo dele << 5 (C1Kind), $FF: silêncio
        cmp     #$FF
        beq     @off1
        cmp     #0
        bne     :+
        cpy     #6                  ; os outros carros: só o mais próximo (volume 6; o da posição
        bne     @off1               ; seguinte, volume 3, em silêncio: escolha B do dono do projeto,
        ldx     oppSnd              ; tools/oppprev.py); a opção da tela inicial: 0 assim, 1
        beq     @opp                ; só os primeiros OPP_SHORT tiques, 2 nunca
        dex
        bne     @hush1
        lda     oppLeft
        beq     @hush1
        dec     oppLeft
@opp:   lda     #0
:       sta     sT1
        lda     AUDF1
        and     #$1F
        ora     sT1
        cmp     sF1                 ; (sF1: AUDF | o tipo << 5)
        beq     @same1
        sta     sF1                 ; um período novo: PerT vezes o C1Mul do tipo; GapLo1/GapHi1 =
        and     #$1F                ; 1..12 deles (um tom: todos de um período); a tabela de intervalos:
        tax                         ; a do tipo (S1Gap1/4)
        lda     PerT,x
        sta     sT1+1
        lda     sF1
        lsr
        lsr
        lsr
        lsr
        lsr
        sta     sK1
        tay
        lda     #0
        sta     sP1
        sta     sP1+1
        ldx     C1Mul,y
:       lda     sP1
        clc
        adc     sT1+1
        sta     sP1
        bcc     :+
        inc     sP1+1
:       dex
        bne     :--
        lda     C1GapL,y
        sta     S1Gap1+1
        sta     S1Gap4+1
        lda     C1GapH,y
        sta     S1Gap1+2
        sta     S1Gap4+2
        ldx     #0
        lda     #0
        sta     sT1
        sta     sT1+1
@gap1:  ldy     sK1
        lda     C1Tone,y
        beq     :+
        lda     #0
        sta     sT1
        sta     sT1+1
:       lda     sT1
        clc
        adc     sP1
        sta     sT1
        sta     GapLo1,x
        lda     sT1+1
        adc     sP1+1
        sta     sT1+1
        sta     GapHi1,x
        inx
        cpx     #12
        bne     @gap1
@same1: lda     AUDC1               ; (diferente de zero)
        and     #$0F
        ldx     sMode1
        sta     sMode1
        txa
        bne     @rts                ; estava em silêncio: liga
        ldy     #2
        lda     sP1
        jmp     SndOn
@rts:   rts

; o bipe: o alto-falante trocado no tom de AUDF1 (AUDC 4: 31.440 / 2 / (AUDF + 1) Hz; um meio
; período de (AUDF + 1) * 31 + 15 ciclos (medido), ~1.223 Hz para AUDF 12, contra 1.209 do
; original) BEEP_HALVES vezes (~0,066 s, como os 4 tiques do original), sem mais nada rodando; o
; tempo dele vai para o saldo do ritmo (o jogo recupera, com menos imagens nessa hora)
OPP_SHORT   = 6                     ; tiques do som dos outros carros na opção curta (~0,1 s)
BEEP_HALVES = 162
BEEP_REST   = 4                     ; tiques de silêncio depois dele (~0,07 s)
BEEP_COST   = BEEP_HALVES * (13 * 31 + 15) / 16
BeepTone:
        lda     AUDF1
        and     #$1F
        sta     sT1
        lda     #BEEP_HALVES
        sta     sT1+1
@half:  bit     SPKR                ; 4
        ldx     sT1                 ; 4
        inx                         ; 2
@d:     ldy     #5                  ; (AUDF + 1) * 31 - 1
@d2:    dey
        bne     @d2
        dex
        bne     @d
        dec     sT1+1               ; 6
        bne     @half               ; 3
        lda     balance
        clc
        adc     #<BEEP_COST
        sta     balance
        lda     balance+1
        adc     #>BEEP_COST
        sta     balance+1
        rts

; um canal ligado (Y: 0 o motor, 2 o ruído: sR0 + Y; A: o byte baixo do período dele): quando o
; outro canal está em silêncio, tudo recomeça a partir de agora (a primeira troca dele a um
; período daqui); senão a primeira troca dele no instante já agendado. (O ruído desligado:
; SndEvent volta ao motor sozinho, com sDue tomado como o tempo do motor: no máximo uma troca
; adiantada.)
SndOn:
        pha
        lda     sMode               ; (os dois ligados: cada um diferente de zero; não o AND deles, 3 AND 8 ou 4 dá 0)
        beq     :+
        lda     sMode1
        bne     @both
:       lda     #0                  ; sozinho: o outro longe, este a um período daqui, agendado
        sta     sR0                 ; agora
        sta     sR1
        sta     sSch+1
        sta     sDue+1
        lda     #SND_FAR
        sta     sR0+1
        sta     sR1+1
        sty     sWho
        pla
        sta     sSch
        sta     sDue
        sta     sR0,y
        lda     #0
        sta     sR0+1,y
        rts
@both:  pla
        cpy     #2
        beq     @noise
        lda     sSch                ; o motor: a troca dele no instante agendado (o do ruído)
        sta     sR0
        lda     sSch+1
        sta     sR0+1
        rts
@noise: lda     #0                  ; o ruído: o motor estava sozinho (sDue o tempo dele): a troca
        sta     sWho                ; dele é a agendada, a do ruído no mesmo instante
        sta     sSch
        sta     sSch+1
        sta     sR1
        sta     sR1+1
        rts

; os tipos do canal 1 por AUDC (C1Kind: tipo << 5, $FF silêncio): 0 os outros carros (AUDC 3,
; Gap3), 1 o bipe (4, um tom puro), 2 a vinheta (12, um tom puro a um terço), 3 o fim de jogo (7,
; o tom avançando nos 1s do poly de 5 bits, Gap5), 4 a neve (8, Gap9, metade da taxa); por tipo:
; o múltiplo de PerT do período, a tabela de intervalos, um tom (todo intervalo de um período)
C1Kind: .byte   $FF, $FF, $FF, $00, $20, $FF, $FF, $60, $80, $FF, $FF, $FF, $40, $FF, $FF, $FF
C1Mul:  .byte   1, 1, 3, 1, 2
C1GapL: .byte   <Gap3, <Gap3, <Gap3, <Gap5, <Gap9
C1GapH: .byte   >Gap3, >Gap3, >Gap3, >Gap5, >Gap9
C1Tone: .byte   0, 1, 1, 0, 0

; os ganchos dentro da lógica de jogo do original (HOOKS em tools/mktk.py, pela tabela de saltos
; em $4006): um checkpoint, mantendo os registradores e os flags, depois a instrução que eles
; substituem
Hook0:  php
        pha
        SND     hook0
        pla
        plp
        jmp     ORIG_Lf4cd
Hook1:  php
        pha
        SND     hook1
        pla
        plp
        bit     SWCHA
        rts
Hook2:  php
        pha
        SND     hook2
        pla
        plp
        ldy     INTIM
        rts
Hook3:  php
        pha
        SND     hook3
        pla
        plp
        lda     ORIG_Lfdec,y
        rts
Hook4:  php
        pha
        SND     hook4
        pla
        plp
        jmp     ORIG_Lfdc9
Hook5:  php
        pha
        SND     hook5
        pla
        plp
        jmp     ORIG_Lfdc9
Hook6:  php
        pha
        SND     hook6
        pla
        plp
        lda     ORIG_HillColors,y
        rts
Hook7:  php
        pha
        SND     hook7
        pla
        plp
        lda     ORIG_CurveTable,y
        rts
