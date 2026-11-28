; Sky Fox no TK2000: a turbina continua enquanto a imagem do tubo é desenhada (o silêncio entre a turbina e o
; zuuum: ~1,6 s, dos quais ~0,6 s desenhando; o resto é leitura de disco). Escolha do dono do projeto (27/11/2026).
; Montado em $1EEB-$1F27, no fim do r1A: zeros que nenhuma medição usa (tools/usage.py, 21 medições). Cuidado: as
; medições não contam as cargas de disco, e em volta delas o t8 guarda a página zero em $1F29-$1F3F; o t14 usa
; $1F75-$1F7F como tabela. Daí o limite em $1F28;
; tools/sfrelocs.py põe os bytes no r1A (CODE) e faz as trocas:
;   t21 $7585 jsr $B229 (o desenho do tubo, depois do FIRE)  -> jsr TDRAW
;   rB0 $B26D dex / bne $B243 (o laço dos bytes soltos)       -> jmp GANCHO1
;   rB0 $B299 dex / beq $B292 (o laço das repetições)         -> jmp GANCHO2
; Os ganchos tocam uma amostra da turbina por byte desenhado só com DESENHO ligado (só nesta chamada); nas outras
; telas custam ~10 ciclos por byte.

AMOSTRA = $6AA6                 ; src/tksom.s: uma amostra da turbina (X e Y ficam, A muda)
INCH    = $64E1                 ; o incremento de fase da turbina
DECOD   = $5229                 ; rB0 $B229 no TK2000
B243    = $5243
B270    = $5270
B29C    = $529C
B292    = $5292
INCD    = $3C                   ; 1.302 Hz: 1302 * 256 / 5525 (uma amostra por byte: 7.680 bytes em ~1,39 s, medido)
; (depois do desenho a turbina não toca mais até a próxima tela, que recomeça do silêncio: o incremento não volta)

        .org    $1EEB

DESENHO: .byte  0               ; $80 enquanto o tubo é desenhado

; no lugar de lda #0 / ... / jsr $B229 (A = 0: o modo sta); depois o t21 não lê A ($7591 e $7601 o trocam antes)
TDRAW:  .assert TDRAW = $1EEC, error, "TDRAW mudou: acerte tools/sfrelocs.py"
        lda     #INCD
        sta     INCH
        lda     #$80
        sta     DESENHO
        lda     #0
        jsr     DECOD
        asl     DESENHO         ; $80 -> 0
        rts

GANCHO1:
        .assert GANCHO1 = $1EFF, error, "GANCHO1 mudou: acerte tools/sfrelocs.py"
        bit     DESENHO
        bpl     @n
        jsr     AMOSTRA_
@n:     dex
        beq     @f
        jmp     B243
@f:     jmp     B270

GANCHO2:
        .assert GANCHO2 = $1F10, error, "GANCHO2 mudou: acerte tools/sfrelocs.py"
        bit     DESENHO
        bpl     @n
        jsr     AMOSTRA_
@n:     dex
        beq     @z
        jmp     B29C
@z:     jmp     B292

AMOSTRA_:                       ; A fica
        pha
        jsr     AMOSTRA
        pla
        rts
        .assert * <= $1F28, error, "passou de $1F28: o t8 guarda a página zero em $1F29"
