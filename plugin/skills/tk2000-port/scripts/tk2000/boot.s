; O carregador de boot de um disco de jogo do TK2000 (tools/mkdsk.py), do porte de Kung Fu Master.
; A ROM de boot da interface de disco (CALL 49408) lê os setores físicos 0 a 3 da trilha 0 (a
; quantidade é o primeiro byte deste arquivo) em $0800-$0BFF e salta para $0801: este código se copia
; para $0400-$07FF, depois lê o jogo com o próprio código de disco, a partir da trilha 1 (uma página
; por setor: o índice da página = (trilha - 1) * 16 + setor físico): o programa a partir da página
; LOW_FIRST e, se houver, uma segunda parte na RAM sob a ROM a partir da página HIGH_FIRST (como a
; fita os carrega); depois o inicia como a fita faz (jmp START), com a ROM selecionada quando não há
; segunda parte. A memória do próprio carregador ($0200-$07FF, $F0-$F9) fica para o jogo depois.
; Dados pelo mkdsk.py (ca65 -D): LOW_FIRST, LOW_PAGES, HIGH_FIRST, HIGH_PAGES, START.

PHASE_OFF   = $C090         ; + fase * 2 (+ 1: ligada); os registradores da interface ($C090-$C09F)
MOTOR_OFF   = $C098
DATA        = $C09C         ; o latch de leitura (Q6 desligado, Q7 desligado)
COLOUR      = $C050
RAMSEL      = $C05B         ; a RAM sob a ROM ($C100-$FFFF; $C100-$C1FF continua sendo a
                            ; ROM da interface)

TOTAL       = LOW_PAGES + HIGH_PAGES
TRACKS      = (TOTAL + 15) / 16

DecTable    = $0200         ; nibble -> valor de 6 bits (256 bytes)
Aux         = $0300         ; os 86 valores de bits baixos de um setor
Done        = $0360         ; setores lidos nesta trilha (16)

dst         = $F0           ; para onde vai o setor
track       = $F2
ht          = $F3           ; a cabeça: meias trilhas
target      = $F4
count       = $F5
chk         = $F6
tmp         = $F7
sector      = $F8
page        = $F9           ; índice da página (0 a TOTAL - 1)

        .org    $0400

        .byte   4                   ; os setores que a ROM de boot lê (0 a 3)

; em $0801 (a ROM de boot salta para cá): copia as 4 páginas para $0400 e continua lá
        ldy     #0
@copy:  lda     $0800,y
        sta     $0400,y
        lda     $0900,y
        sta     $0500,y
        lda     $0A00,y
        sta     $0600,y
        lda     $0B00,y
        sta     $0700,y
        iny
        bne     @copy
        jmp     Loader

Loader: sei
        cld
        sta     COLOUR              ; uma imagem em $2000 aparece em cores enquanto carrega
.if HIGH_PAGES > 0
        sta     RAMSEL
.endif
        ldx     #63                 ; a tabela de decodificação
@dec:   ldy     WriteTable,x
        txa
        sta     DecTable,y
        dex
        bpl     @dec
        lda     #0                  ; a ROM de boot deixou a cabeça na trilha 0 (fase 0 ligada)
        sta     ht
        lda     #1
        sta     track

; --- uma trilha: os 16 setores dela, na ordem em que passam sob a cabeça
@track: lda     track
        asl
        jsr     Seek
        ldx     #15
        lda     #0
@clear: sta     Done,x
        dex
        bpl     @clear
        sta     count
@sector:
        jsr     ReadAddress
        bcs     @sector
        ldx     sector
        lda     Done,x
        bne     @sector
        lda     track               ; página = (trilha - 1) * 16 + setor
        sec
        sbc     #1
        asl
        asl
        asl
        asl
        ora     sector
        sta     page
        cmp     #TOTAL
        bcs     @mark               ; depois do fim: nada a ler
        cmp     #LOW_PAGES
        bcs     @high
        adc     #LOW_FIRST          ; o programa
        bne     @dest
@high:  sbc     #LOW_PAGES          ; (C = 1) os arquivos compactados
        clc
        adc     #HIGH_FIRST
@dest:  sta     dst+1
        lda     #0
        sta     dst
        jsr     ReadData
        bcs     @sector             ; checksum errado: lê de novo
@mark:  ldx     sector
        lda     #1
        sta     Done,x
        inc     count
        lda     count
        cmp     #16
        bne     @sector
        inc     track
        lda     track
        cmp     #TRACKS + 1
        bne     @track
        lda     MOTOR_OFF
        jmp     START

; --- Seek: A = a meia trilha para onde ir, uma fase de cada vez (cerca de 13 ms cada)
Seek:   sta     target
@step:  lda     ht
        cmp     target
        beq     @there
        bcc     @up
        dec     ht
        bcs     @move
@up:    inc     ht
@move:  lda     ht                  ; liga a fase da nova meia trilha
        and     #3
        asl
        tay
        lda     PHASE_OFF+1,y
        jsr     Wait
        lda     ht                  ; as outras desligadas
        and     #3
        sta     tmp
        ldx     #3
@off:   cpx     tmp
        beq     :+
        txa
        asl
        tay
        lda     PHASE_OFF,y
:       dex
        bpl     @off
        jmp     @step
@there: jsr     Wait                ; espera assentar
        rts

Wait:   ldx     #10
@outer: ldy     #0
@inner: dey
        bne     @inner
        dex
        bne     @outer
        rts

; --- ReadAddress: o próximo campo de endereço desta trilha: setor (C = 0), ou C = 1 (de outra
; trilha, ou checksum errado)
ReadAddress:
@sync:  lda     DATA
        bpl     @sync
@d5:    cmp     #$D5
        bne     @sync
:       lda     DATA
        bpl     :-
        cmp     #$AA
        bne     @d5
:       lda     DATA
        bpl     :-
        cmp     #$96
        bne     @d5
        ldy     #4                  ; volume, trilha, setor, checksum (4-and-4)
        lda     #0
        sta     chk
@field: jsr     Read44
        sta     Fields-1,y
        eor     chk
        sta     chk
        dey
        bne     @field
        lda     chk                 ; os quatro juntos: 0
        bne     @bad
        lda     Fields+2            ; a trilha
        cmp     track
        bne     @bad
        lda     Fields+1            ; o setor
        sta     sector
        clc
        rts
@bad:   sec
        rts

Read44: lda     DATA
        bpl     Read44
        sec
        rol
        sta     tmp
:       lda     DATA
        bpl     :-
        and     tmp
        rts

Fields: .res    4                   ; checksum, setor, trilha, volume

; --- ReadData: o campo de dados em (dst): C = 1 se errado
ReadData:
        ldy     #32                 ; o prólogo do campo de dados, logo depois
@sync:  dey
        beq     @bad
:       lda     DATA
        bpl     :-
@d5:    cmp     #$D5
        bne     @sync
:       lda     DATA
        bpl     :-
        cmp     #$AA
        bne     @d5
:       lda     DATA
        bpl     :-
        cmp     #$AD
        bne     @d5
        lda     #0
        sta     chk
        ldy     #0
@aux:   lda     DATA                ; 86 valores de bits baixos, depois 256 dos 6 bits altos; cada
        bpl     @aux                ; nibble é o valor XOR o anterior
        tax
        lda     chk
        eor     DecTable,x
        sta     chk
        sta     Aux,y
        iny
        cpy     #86
        bne     @aux
        ldy     #0
@high:  lda     DATA
        bpl     @high
        tax
        lda     chk
        eor     DecTable,x
        sta     chk
        sta     (dst),y
        iny
        bne     @high
:       lda     DATA                ; o checksum
        bpl     :-
        tax
        lda     chk
        eor     DecTable,x
        bne     @bad
        ldx     #0                  ; os bytes: os 6 bits altos, depois os 2 baixos (guardados
@byte:  lda     (dst),y             ; trocados: bit 1, depois bit 0), a 86 valores de distância
        lsr     Aux,x
        rol
        lsr     Aux,x
        rol
        sta     (dst),y
        inx
        cpx     #86
        bne     :+
        ldx     #0
:       iny
        bne     @byte
        clc
        rts
@bad:   sec
        rts

WriteTable:
        .byte   $96, $97, $9A, $9B, $9D, $9E, $9F, $A6, $A7, $AB, $AC, $AD, $AE, $AF, $B2, $B3
        .byte   $B4, $B5, $B6, $B7, $B9, $BA, $BB, $BC, $BD, $BE, $BF, $CB, $CD, $CE, $CF, $D3
        .byte   $D6, $D7, $D9, $DA, $DB, $DC, $DD, $DE, $DF, $E5, $E6, $E7, $E9, $EA, $EB, $EC
        .byte   $ED, $EE, $EF, $F2, $F3, $F4, $F5, $F6, $F7, $F9, $FA, $FB, $FC, $FD, $FE, $FF

        .assert * <= $0800, error, "the boot loader is over 4 sectors"
