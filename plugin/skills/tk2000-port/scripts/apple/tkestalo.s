; Sky Fox no TK2000: os estalinhos do voo (escolha do dono do projeto, 26/11/2026: "voo-F-estalos")
; Montado em $6A19, no lugar do caminho da Mockingboard do t7 ($6A19-$6A8F: só roda com a placa, o t7 $6A13
; pula para ele com a placa achada); tools/sfrelocs.py põe os bytes no t7 (CODE).
;
; No Apple sem placa o motor de som do t7 dá rajadas de cliques (o tique $6BA5 clica a cada chamada com
; $1B positivo, $6BB0; o tocador de sequências $6BD1 clica em $6BD5), 100 a 2.300 ciclos entre um e
; outro: um chiado. Com a placa o voo é quase mudo. Aqui cada rajada vira um estalo só: o primeiro
; clique de uma rajada dá 4 cliques em ~1.100 ciclos e os outros ficam mudos. "Rajada nova" = 10 tiques
; ou mais sem clique (o tique é chamado ~356 vezes por segundo no voo, medido: ~30 ms; contando assim,
; ~2% dos intervalos caem do lado errado dos 30 ms).

SPKR    = $C030
TIQUE   = $6BA5                 ; o tique do motor de som (r40 $45F8: jmp $6BA5)
NOVA    = 10                    ; tiques sem clique para a próxima rajada

        .org    $6A19

; r40 $45F8 (jmp $6BA5) -> jmp TICK: conta os tiques desde o último clique (para em 255); A, X, Y intactos
TICK:   inc     SIL
        bne     @v
        dec     SIL
@v:     jmp     TIQUE

; no lugar de bit $C030 ($6BB0 e $6BD5): A, X, Y intactos
ESTAL:  pha
        lda     SIL
        cmp     #NOVA
        lda     #0
        sta     SIL
        bcc     @fim            ; ainda dentro da rajada: mudo
        txa
        pha
        bit     SPKR
        ldx     #60             ; 5 ciclos por volta: ~300
@a:     dex
        bne     @a
        bit     SPKR
        ldx     #80             ; ~400
@b:     dex
        bne     @b
        bit     SPKR
        ldx     #80
@c:     dex
        bne     @c
        bit     SPKR            ; 4 cliques: o cone volta para onde estava
        pla
        tax
@fim:   pla
        rts

SIL:    .byte   $FF
