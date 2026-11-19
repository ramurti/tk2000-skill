; Kung Fu Master no TK2000: efeitos sonoros (o original não tem, só músicas). Na RAM
; sob a ROM, depois dos arquivos compactados (o tools/mkimage.py o monta em SFX_AT, dado com
; -D); a tabela de saltos do src/tk.s chama as entradas abaixo.

        .org    SFX_AT

        jmp     HitSound    ; +0
        jmp     DeathSound  ; +3
        jmp     BossSound   ; +6
        jmp     ThudSound   ; +9
        jmp     MusicCheck  ; +12
        jmp     NeverDie    ; +15
        jmp     TimeUp      ; +18
        jmp     FloorMusic  ; +21

; Curtos, para o jogo quase não ficar mais lento (a morte e o chefe: quando o jogo para de
; qualquer jeito); pelo ponteiro do alto-falante do jogo ($F9: $C030, ou um byte de RAM quando o
; CTRL-S desligou o som: o CTRL-S original, que não existe no porte).
SPEAKER     = $F9

; HitSound: um golpe, uma rajada de ruído ficando mais grave (24 cliques, cerca de 5 ms); depois o
; CPX que ele substitui. Preserva A, X, Y.
HIT_CLICKS  = 24

HitSound:
        pha
        txa
        pha
        tya
        pha
        ldx     #HIT_CLICKS
@click: ldy     #0
        lda     (SPEAKER),y
        lda     seed                ; parte aleatória: um LFSR de 8 bits
        lsr
        bcc     :+
        eor     #$B8
:       sta     seed
        and     #$0F
        sta     noise
        txa                         ; parte crescente: (cliques feitos) * 2
        eor     #$FF
        sec
        adc     #HIT_CLICKS
        asl
        clc
        adc     noise
        adc     #6
        tay
@wait:  dey                         ; 5 ciclos por passada
        bne     @wait
        dex
        bne     @click
        pla
        tay
        pla
        tax
        pla
        cpx     $04A2
        rts

; ThudSound: o jogador atingido (o golpe de um inimigo, uma faca; enquanto agarrado, de novo a
; cada poucos décimos de segundo): uma rajada de ruído grave, mais grave que um golpe (16 cliques,
; cerca de 6 ms); depois o JSR $8009 que ele substitui (a energia tirada). Preserva A, X, Y.
THUD_CLICKS = 16

ThudSound:
        pha
        txa
        pha
        tya
        pha
        ldx     #THUD_CLICKS
@click: ldy     #0
        lda     (SPEAKER),y
        lda     seed
        lsr
        bcc     :+
        eor     #$B8
:       sta     seed
        and     #$1F
        adc     #50                 ; 50-82 passadas: um clique a cada 0,3-0,4 ms
        tay
@wait:  dey
        bne     @wait
        dex
        bne     @click
        pla
        tay
        pla
        tax
        pla
        bit     immortal            ; nunca morrer: a energia fica
        bmi     :+
        jmp     $8009
:       rts

; --- nunca morrer (CTRL-N, src/tk.s KbdRead): a energia do jogador não é tirada (ThudSound) e
; o fim do tempo não mata (TimeUp; o tempo continua a partir de 9999). Um bipe subindo quando
; é ligado, descendo quando desligado.
NeverDie:
        lda     immortal
        eor     #$80
        sta     immortal
        ldx     #0                  ; as duas notas: grave, aguda (ligado) ou aguda, grave (desligado)
        bit     immortal
        bmi     :+
        ldx     #2
:       jsr     @note
        inx
@note:  lda     NeverHalves,x
        sta     halves
        lda     #0
        sta     halves+1
@half:  ldy     #0
        lda     (SPEAKER),y
        ldy     NeverDelay,x
@wait:  dey
        bne     @wait
        dec     halves
        bne     @half
        rts

NeverDelay: .byte   180, 120, 120, 180  ; 5 * atraso + cerca de 25 ciclos: cerca de 1.100, 1.650 Hz
NeverHalves:.byte   90, 130, 130, 90    ; cerca de 40 ms cada

; TimeUp: D $7D44, JSR $8044 quando o tempo chega a 0: a morte, a não ser com nunca morrer
TimeUp: bit     immortal
        bmi     :+
        jmp     $8044
:       rts

immortal:   .byte   0       ; bit 7: nunca morrer

; DeathSound: o jogador morre (tudo para durante a queda): um tom deslizando para baixo, cerca de
; 0,6 s (de cerca de 2,3 kHz até 400 Hz); depois o LDA #0 / STA $047D que ele substitui.
; Preserva X, Y.
DEATH_FROM  = 40            ; meio período: 5 * isto + cerca de 20 ciclos
DEATH_TO    = 255
DEATH_HALVES= 4             ; meios períodos em cada altura

DeathSound:
        txa
        pha
        tya
        pha
        lda     #DEATH_FROM
        sta     noise
@pitch: ldx     #DEATH_HALVES
@half:  ldy     #0
        lda     (SPEAKER),y
        ldy     noise
@wait:  dey
        bne     @wait
        dex
        bne     @half
        inc     noise
        lda     noise
        cmp     #DEATH_TO
        bne     @pitch
        pla
        tay
        pla
        tax
        lda     #0
        sta     $047D
        rts

; BossSound: o golpe que derrota o chefe de um andar: uma fanfarra, C E G (70 ms cada) e um C agudo
; (250 ms); depois o LDA #$FF / STA $04A2 que ele substitui. Preserva X, Y.
; Uma nota: o atraso do meio período (5 * atraso + cerca de 34 ciclos) e quantos meios períodos.
BOSS_NOTES  = 4
BossDelay:  .byte   189, 148, 124, 91           ; C5, E5, G5, C6
BossHalvesLo: .byte <73, <92, <110, <523
BossHalvesHi: .byte >73, >92, >110, >523

BossSound:
        txa
        pha
        tya
        pha
        ldx     #0
@note:  lda     BossHalvesLo,x
        sta     halves
        lda     BossHalvesHi,x
        sta     halves+1
@half:  ldy     #0
        lda     (SPEAKER),y
        ldy     BossDelay,x
@wait:  dey
        bne     @wait
        lda     halves
        bne     :+
        dec     halves+1
:       dec     halves
        lda     halves
        ora     halves+1
        bne     @half
        inx
        cpx     #BOSS_NOTES
        bne     @note
        pla
        tay
        pla
        tax
        lda     #$FF
        sta     $04A2
        rts

; --- a música do título (tools/midi2tk.py: reference/music.mid, uma oitava acima): na primeira
; tela da demo depois da carga e cada vez que a demo volta (depois de uma partida: CTRL-Q ou o
; game over), até SPACE (aí a demo continua); e em cada andar novo, até um movimento (uma
; seta, SPACE ou Z: aí o jogo continua).
KBOUT       = $C000
KBIN        = $C010
MUSIC_WAIT  = 2             ; passadas do laço principal antes dela (a tela desenhada)

; FloorMusic: D $851F, JSR $1EF3 (o fim do andar: o próximo andar): a escada (stairs.s),
; depois a música quando o próximo andar é desenhado
FloorMusic:
        jsr     Stairs
        lda     #MUSIC_WAIT
        sta     music
        lda     #$80
        sta     mfloor
        jmp     $1EF3

; MusicCheck: no topo do laço principal, a cada quadro, no lugar de LDA $04AF (depois o mesmo).
; $04AF: 0 na demo; a música do título só ali, a do andar só numa partida.
MusicCheck:
        lda     $04AF
        beq     :+
        sta     ingame              ; numa partida
        bne     @check
:       lda     ingame              ; a demo de novo, depois de uma partida: a música do título de novo
        beq     @check
        lda     #0
        sta     ingame
        sta     mfloor
        lda     #MUSIC_WAIT
        sta     music
@check: lda     music
        beq     @done
        lda     $04AF               ; a do título: na demo (0); a de um andar: numa partida
        bit     mfloor
        bmi     @game
        cmp     #0
        bne     @done
        beq     @wait
@game:  cmp     #0
        beq     @done
@wait:  dec     music
        bne     @done
        jsr     Music
        lda     #0
        sta     mfloor
@done:  lda     $04AF
        rts

Music:  txa
        pha
        tya
        pha
        lda     #0
        sta     mstep
@step:  ldx     mstep
        lda     MusicSteps,x
        beq     @rest
        tax                         ; a nota: meios períodos como no BossSound
        dex
        lda     MusicHalvesLo,x
        sta     halves
        lda     MusicHalvesHi,x
        sta     halves+1
@half:  ldy     #0
        lda     (SPEAKER),y
        ldy     MusicDelay,x
@wait:  nop                         ; 7 ciclos por passada
        dey
        bne     @wait
        lda     halves
        bne     :+
        dec     halves+1
:       dec     halves
        lda     halves
        ora     halves+1
        bne     @half
        ldy     #MUSIC_STEP_MS - MUSIC_NOTE_MS  ; as notas separadas (midi2tk.py)
        bne     @quiet
@rest:  ldy     #MUSIC_STEP_MS
@quiet: jsr     WaitMs
        jsr     StopDown
        bne     @stop
        inc     mstep
        lda     mstep
        cmp     #MUSIC_STEPS
        bne     @step
        lda     #0                  ; de novo
        sta     mstep
        beq     @step
@stop:  bit     mfloor              ; um andar: o movimento continua no jogo
        bmi     @out
:       jsr     SpaceDown           ; até soltar SPACE: a demo não o vê (o menu)
        bne     :-
@out:
        pla
        tay
        pla
        tax
        rts

; WaitMs: Y milissegundos (aproximadamente)
WaitMs:
@ms:    ldx     #203
@l:     dex
        bne     @l
        dey
        bne     @ms
        rts

; StopDown: Z = 0 se a tecla que para a música está apertada: SPACE (o título); uma seta, SPACE ou Z
; (um andar)
StopDown:
        bit     mfloor
        bpl     SpaceDown
        ldx     #MOVE_KEYS-1
@key:   lda     MoveRow,x
        sta     KBOUT
        lda     KBIN
        and     MoveCol,x
        bne     @down
        dex
        bpl     @key
@down:  pha
        lda     #0
        sta     KBOUT
        pla
        rts

MOVE_KEYS   = 6
MoveRow:    .byte   $08, $10, $20, $40, $04, $01    ; LEFT, RIGHT, DOWN, UP, SPACE, Z
MoveCol:    .byte   $01, $01, $01, $01, $01, $20

; SpaceDown: Z = 0 se SPACE está apertada
SpaceDown:
        lda     #$04
        sta     KBOUT
        lda     KBIN
        and     #$01
        pha
        lda     #0
        sta     KBOUT
        pla
        rts

        .include "music.inc"
        .include "stairs.s"

music:  .byte   MUSIC_WAIT          ; 0: tocada (o título: depois da carga, depois de uma partida)
mfloor: .byte   0                   ; bit 7: a música do andar (senão a do título)
ingame: .byte   0                   ; não 0: uma partida vista ($04AF)
mstep:  .byte   0
halves: .word   0
seed:   .byte   1
noise:  .byte   0
