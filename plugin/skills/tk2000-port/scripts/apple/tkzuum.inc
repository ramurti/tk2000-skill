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
RUIDO   = $6A53                 ; src/tkzuumr.s
