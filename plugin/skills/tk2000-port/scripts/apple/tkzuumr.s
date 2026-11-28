; Sky Fox no TK2000: o "zuuum" da corrida no tubo, as partes no t7 ($6A53-$6A8F, depois dos estalinhos, no
; caminho da Mockingboard: só roda com a placa): a volta do chiado (src/tkzuum.s chama a cada volta par; Y e A
; mudam) e a cauda do fim da corrida.
        .include "tkzuum.inc"
        .org    RUIDO
        ldy     #KRUI
@r0:    clc
        lda     RPH
        adc     RINC
        sta     RPH
        bcc     @r1
        lda     LF              ; o LFSR anda; o bit que sai decide se o cone troca
        lsr     a
        bcc     @r2
        eor     #$B8
@r2:    sta     LF
        bcc     @r1
        bit     SPKR
@r1:    dey
        bne     @r0
        rts

; a espera da corrida acabou (n = 0): o laço da corrida chama a espera a cada ~10 ms, ~150 vezes até a nave sair;
; o zuuum continua cada vez mais curto, MV/64 voltas (3, 2, 1; 64 chamadas cada), o tom no agudo (FINC já é 29
; desde n < 4) e um chiado grave; volta com C = 0, como $A28E
CAUDA_: lda     MV
        beq     @fim
        dec     MV
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        lsr     a
        beq     @fim
        tax
        lda     #10
        sta     RINC
        jsr     VOLTA
@fim:   clc
        rts
        .assert CAUDA_ = CAUDA, error, "CAUDA mudou: acerte src/tkzuum.inc"
