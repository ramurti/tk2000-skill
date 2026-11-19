# 2. A máquina

Tudo aqui foi lido no código-fonte do emulador ou medido durante os portes. O comportamento do
hardware real nem sempre foi conferido; onde não foi, o texto diz.

## 2.1 Mapa de memória

| Faixa | Uso |
|---|---|
| `$0000-$00FF` | Página zero. A ROM usa boa parte dela; quando o jogo assume a máquina, ela toda é sua |
| `$0100-$01FF` | Pilha |
| `$0200-$07FF` | Buffers da ROM e o BASIC; livre quando o jogo está rodando |
| `$0800-$1FFF` | Livre (tabelas, dados carregados antes do jogo) |
| `$2000-$3FFF` | Página 1 de hi-res |
| `$4000-$9FFF` | Livre, 24 KB: o lugar de costume para o programa |
| `$A000-$BFFF` | Página 2 de hi-res (o Apple II tem ela em `$4000`), ou 8 KB de RAM livre se você usar uma página só |
| `$C000-$C0FF` | E/S |
| `$C100-$FFFF` | ROM, ou 16 KB de RAM no modelo de 64 KB (`$C05B` seleciona a RAM, `$C05A` a ROM) |

O porte do xadrez usou uma página de hi-res e pôs suas listas de lances em `$A000-$B8FF`; o
River Raid usou as duas páginas e coube com o código em `$4000-$9FFF` mais tabelas em `$0800-$1FFF`.

## 2.2 E/S

| Endereço | Função |
|---|---|
| `$C000` (escrita) | Seleção de linha do teclado |
| `$C010` (leitura) | Colunas do teclado (bits 0-5); o bit 7 é a entrada da fita: mascare-o |
| `$C030` | Inverte o alto-falante (qualquer acesso) |
| `$C050` / `$C051` | Vídeo colorido / monocromático |
| `$C054` / `$C055` | Mostra a página 1 / página 2 de hi-res |
| `$C05A` / `$C05B` | ROM / RAM em `$C100-$FFFF` (modelo de 64 KB) |

## 2.3 A tela

**Organização** (igual à do Apple II): 192 linhas de 40 bytes; cada byte mostra 7 pixels, o bit
0 à esquerda; **o bit 7 não é um pixel**, e sim a paleta do byte. A linha y começa em
`$2000 + (y & 7) * $400 + ((y >> 3) & 7) * $80 + (y >> 6) * 40`: mantenha uma tabela.

**Cores** (é aqui que o TK2000 difere do Apple II): os pixels são agrupados em pares a partir de
x = 0, e cada par mostra uma cor, escolhida pelos seus dois bits e pelo bit de paleta do byte que
contém o pixel da esquerda do par:

| Par (esquerda, direita) | Paleta 0 | Paleta 1 |
|---|---|---|
| 0 0 | preto | preto |
| 1 1 | branco | branco |
| 1 0 | verde | ciano |
| 0 1 | azul | vermelho |

Portanto:

- **A resolução em cores é 140 × 192.** Desenhe tudo em pares de pixels, em x par.
- **Um pixel sozinho é uma cor, não branco.** O branco precisa dos dois pixels do par.
- **Conflito de paleta:** a paleta é por byte (7 pixels). Vermelho e ciano não podem dividir um
  byte com verde e azul. O River Raid mantém a área de jogo na paleta 0 (branco, preto, verde,
  azul) e usa a paleta 1 só na barra de status, onde o vermelho fica sobre branco e preto.
- **Colunas de byte pares para gráficos alinhados a byte:** o byte n começa no pixel 7n, que só
  é par quando n é par; um caractere numa coluna de byte ímpar mostra franjas de cor.
- **Reescrever uma página inteira custa ~80 ms.** Nas taxas de quadros de um jogo, redesenhe só
  o que mudou (guarde uma cópia do que cada linha mostra) e use as duas páginas para evitar
  cintilação (desenhe na página escondida e depois troque com `$C054`/`$C055`).

Os gráficos do Apple II não mostram as mesmas cores aqui: remapeie ou redesenhe.

## 2.4 Texto

O TK2000 **não tem modo texto**: a ROM desenha os caracteres na página 1 de hi-res. Um jogo tem
duas maneiras de mostrar texto:

1. **Os próprios caracteres da ROM** (a cara do BASIC): passe para monocromático (`sta $C051`),
   limpe com `jsr $FC58` (HOME), imprima cada caractere com o bit 7 ligado por `jsr $FDF0`
   (COUT); 13 começa uma nova linha. 40 colunas × 24 linhas. Volte para cores (`sta $C050`) para
   o jogo.
   - **As rotinas de texto da ROM usam a página zero.** Não guarde ponteiros nem variáveis do
     jogo na página zero enquanto imprime: o texto do porte do xadrez saiu embaralhado porque o
     byte alto do ponteiro de texto ficava em `$32`, que a ROM usa como máscara de
     inverso/piscante. Percorra o texto com um endereço absoluto que o código avança no próprio
     lugar (veja `examples/hello/hello.s`) e inicialize as variáveis de página zero do jogo
     depois da tela de texto.
   - Só funciona enquanto a ROM está mapeada (não com a RAM de 64 KB selecionada).
2. **Uma fonte própria em cores**, desenhada em pares de pixels: uma fonte 3 × 5 em células de 4
   pares dá 35 caracteres por linha; uma fonte 5 × 7, cerca de 22. Células de 7 pares alinhadas
   a byte (2 bytes por caractere) são as mais rápidas de desenhar.

O dono do projeto do xadrez preferiu o texto simples da ROM a um desenhado para a tela de
instruções.

## 2.5 Teclado

Uma matriz: escreva uma máscara de linha em `$C000`, leia `$C010` e teste o bit da coluna.

```
             $C010 bit:  0      1   2   3   4   5
$C000 = $01:             SHIFT  B   V   C   X   Z
$C000 = $02:             -      G   F   D   S   A
$C000 = $04:             SPACE  T   R   E   W   Q
$C000 = $08:             LEFT   5   4   3   2   1
$C000 = $10:             RIGHT  6   7   8   9   0
$C000 = $20:             DOWN   Y   U   I   O   P
$C000 = $40:             UP     H   J   K   L   :
$C000 = $80:             RETURN N   M   ,   .   ?
```

(O bit 0 de `$C010` é a primeira coluna; por exemplo, a tecla `1` é a linha `$08`, máscara `$20`.)

Leia todas as teclas de que precisa num conjunto de bits a cada passo e compare com o passo
anterior para saber quais teclas "acabaram de ser apertadas":

```
KeyRow:  .byte $08, $10, $40, $20, $04      ; esquerda, direita, cima, baixo, espaço
KeyMask: .byte $01, $01, $01, $01, $01
ReadKeys:
        ldx #4
@key:   lda KeyRow,x
        sta $C000
        lda $C010
        and KeyMask,x
        cmp #1              ; C = apertada
        rol keys
        dex
        bpl @key
        lda #0
        sta $C000
        rts
```

Não há trava de tecla nem código ASCII: código de Apple II que lê `$C000` tem de ser reescrito.

## 2.6 Som

O alto-falante é de um bit: cada acesso a `$C030` move o cone. Não há temporizador nem volume,
então a CPU faz o som invertendo o alto-falante em laços de ciclos contados, e **enquanto ela
desenha, o alto-falante fica mudo**.

Um tom: X = meio período em unidades de 5 ciclos, Y = número de meios períodos.

```
Tone:   stx tmp
@half:  ldx tmp
:       dex             ; 5 ciclos por X
        bne :-
        bit $C030
        dey
        bne @half
        rts
```

Frequência ≈ 1022727 / (2 × (5X + 11)) Hz, então X desce até cerca de 400 Hz (X = 255). Para
uma vinheta, toque uma tabela de pares (X, Y), dividindo as notas longas em várias entradas, e
use uma entrada de "pausa" que espera sem inverter o alto-falante. A fanfarra de vitória do
porte do xadrez (dó-mi-sol-dó, cerca de 1 s) e o "trombone triste" da derrota (três notas
descendentes com intervalos e uma última nota trêmula, cerca de 2 s) ocupam 23 e 41 bytes de
tabela.

O que funcionou num jogo de ação (River Raid): **uma rajada curta e contínua por efeito**, tocada
quando o efeito começa (explosão de 80 ms de ruído com período crescente, bipes de 25 ms no
reabastecimento, deslizamento de 30 ms no míssil). Espalhar o som por todos os quadros em fatias
curtas soou picotado (uma vibração de 20 Hz) e foi rejeitado. Conte os ciclos da rajada no tempo
do quadro para que a velocidade do jogo continue certa.

Ouça os sons como arquivos WAV antes de colocá-los no jogo: sintetize a mesma onda quadrada em
Python, nas mesmas frequências e durações.

## 2.7 Tempo

**Não há como medir o tempo**: nem temporizador, nem retraço vertical, nem relógio. Tudo o que é
cronometrado é contado em ciclos de CPU:

- **Esperas e som:** laços de ciclos contados.
- **Velocidade do jogo:** some os ciclos estimados que cada rotina gasta e converta em tiques do
  jogo (veja o [guia 4](04-portando-um-jogo-de-atari-2600.md)).
- **Um relógio mostrado ao jogador:** só é possível contando. Esperar uma tecla num laço de
  duração conhecida é preciso; estimar o tempo de um cálculo longo (uma busca de xadrez) pelo
  trabalho feito errou em até 30% por lance, a menos que o laço mais interno também seja contado,
  o que deixou a busca 3-4% mais lenta. O dono do projeto do xadrez desistiu do relógio depois de
  ver isso.
