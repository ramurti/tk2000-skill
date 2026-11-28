; o "zuuum" da corrida no tubo (src/tkzuum.s no fim do t22, src/tkzuumr.s no t7): os nomes em comum
SPKR    = $C030
N       = $13                   ; a espera da corrida (t22): 64 no começo, um a menos por quadro
FPH     = $64B1                 ; a fase do tom (vão da camada)
FINC    = $64B2                 ; o incremento do tom
RPH     = $64B3                 ; a fase do chiado
RINC    = $64B4                 ; o incremento do chiado
LF      = $64E4                 ; o LFSR da turbina (src/tksom.s; nunca 0)
KTOM    = 57                    ; amostras do tom por volta: ~22,5 ciclos cada (~1.280)
KRUI    = 41                    ; amostras do chiado: ~31 ciclos em média (custa mais quando troca; medido no emulador)
RUIDO   = $6A53                 ; src/tkzuumr.s: a volta do chiado
CAUDA   = $6A75                 ; src/tkzuumr.s: o fim da corrida
VOLTA   = $4FDE                 ; src/tkzuum.s: as voltas (X), conferido com .assert
MV      = $64B5                 ; a cauda: 255 na corrida, um a menos por chamada depois dela (vão da camada)
MINV    = 4                     ; voltas mínimas por quadro no fim da corrida (~5 ms; a cauda começa com 3)
ALVO    = $428B                 ; t22 $A28B (cmp #$00 da espera): 0 na decolagem, 64 na volta do pouso ($A21F)
ORIG    = $4288                 ; t22 $A288: a espera original
