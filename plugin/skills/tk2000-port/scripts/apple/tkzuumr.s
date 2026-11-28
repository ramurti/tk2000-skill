; Sky Fox no TK2000: o "zuuum" da corrida no tubo, a volta do chiado (src/tkzuum.s chama a cada volta par):
; em $6A53, depois dos estalinhos, no caminho da Mockingboard do t7 (só roda com a placa). Y e A mudam.
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
