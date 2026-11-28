; Sky Fox no TK2000: o "zuuum" da corrida no tubo de lançamento (escolha do dono do projeto, 27/11/2026: opção
; C, o chiado da placa e a turbina subindo de tom, alternando)
; Montado no fim do t22 ($AFB2 no Apple, $4FB2 no TK2000: zeros no disco), com a volta do chiado em $6A53
; (src/tkzuumr.s, no caminho da Mockingboard do t7); variáveis no vão da camada ($64B1-$64B4).
; tools/sfrelocs.py troca o jsr $A288 da corrida (t22 $A270) por jsr ZUUM.
;
; A corrida (t22 $A26D) espera a cada quadro em $A288: com n = $13 (64 no começo, um a menos por quadro) o
; laço dey/dex leva ~1.285 (n - 1) ciclos; a nave acelera porque a espera encurta. ZUUM faz o mesmo que $A288
; (n = 0: C = 0; senão n - 1 e C = 1) e gasta a espera tocando: n voltas de ~1.250 ciclos, alternando volta a
; volta a turbina (tom de 1.310 Hz a 2.880 Hz conforme n desce: fase de 8 bits + 29 - n/4 por amostra) e o
; chiado (LFSR trocado a 2n/256 das amostras: do agudo ao grave). No fim da corrida a espera fica curta e some:
; pelo menos MINV voltas por quadro e, depois, a cauda (src/tkzuumr.s) cada vez mais curta (o dono do projeto
; aceitou o fim da corrida um pouco mais lento: antes, ~2 s de silêncio até a nave sair). A volta do pouso usa a
; mesma espera com inc e outro alvo: ali fica a espera original.

        .include "tkzuum.inc"
Z_AT    = $4FB2                 ; o fim do t22 (zeros no disco), no TK2000 (o t22 do Apple em $A000 fica em $4000)

        .org    Z_AT

ZUUM:   lda     ALVO            ; a volta do pouso ($A21F troca o cmp #$00 por #$40 e o dec por inc):
        bne     @orig           ; a espera original, muda como antes
        lda     N
        bne     @toca
        jmp     CAUDA           ; a espera acabou: a cauda (t7) e C = 0, como $A28E
@orig:  jmp     ORIG
@toca:  dec     N
        ldy     #255
        sty     MV              ; a cauda recomeça
        tax                     ; X = n: as voltas
        asl     a
        sta     RINC            ; 2n
        lsr     a
        lsr     a
        lsr     a               ; n/4
        eor     #$FF
        sec
        adc     #29
        sta     FINC            ; 29 - n/4
        cpx     #MINV           ; no fim da corrida a espera é curta: pelo menos MINV voltas
        bcs     VOLTA_
        ldx     #MINV
VOLTA_:
        .assert VOLTA_ = VOLTA, error, "VOLTA mudou: acerte src/tkzuum.inc"
@volta: txa
        lsr     a
        bcc     @rui
        ldy     #KTOM
@tom:   clc
        lda     FPH
        adc     FINC
        sta     FPH
        bcc     @t1
        bit     SPKR
@t1:    dey
        bne     @tom
        beq     @prox
@rui:   jsr     RUIDO           ; a volta do chiado (src/tkzuumr.s, no t7)
@prox:  dex
        bne     @volta
        sec                     ; como $A29A
        rts
