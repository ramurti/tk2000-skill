# 8. Portando um jogo de Apple II (a partir de um .dsk)

A partir do porte do Kung Fu Master (Data East 1985, Apple II pela Berkeley Softworks), feito a
partir de uma imagem de disco DOS 3.3 crackeada em cerca de um dia, e depois melhorado em mais
alguns. O TK2000 é tão parecido com o Apple II que **o código original pode rodar sem mudanças**:
só mudam os endereços e a entrada e saída. Os detalhes, com todos os números, estão no
[`references/apple-ii.md`](../../plugin/skills/tk2000-port/references/apple-ii.md) da skill; as
ferramentas, em [`scripts/apple/`](../../plugin/skills/tk2000-port/scripts/apple).

## 8.1 O que é igual, o que não é

| | Apple II | TK2000 | O que fazer |
|---|---|---|---|
| CPU e clock | 6502, 1,02 MHz | o mesmo | temporizações por ciclos (músicas no beeper) funcionam como estão |
| Organização da alta resolução (hi-res) | 280 × 192, 40 bytes por linha | a mesma | o código de desenho do jogo funciona como está |
| Página 2 da hi-res | `$4000` | **`$A000`** | relocar: trocar `$4000-$5FFF` e `$A000-$BFFF` |
| Cores | violeta/verde, azul/laranja | verde/azul, ciano/vermelho | a arte aparece em outras cores (o Kung Fu as manteve) |
| Modo texto | sim | **não** | as telas de texto são desenhadas em hi-res; mostre-as em monocromático |
| Teclado | latch ASCII em `$C000` | uma matriz | uma rotina pequena monta um latch no estilo do Apple |
| Joystick | paddles analógicos | nenhum | as setas dão valores fixos de paddle; SPACE e Z são os botões |
| Alto-falante | `$C030` | o mesmo | |
| Disco | Disk II + DOS 3.3 | uma cópia do Disk II + TKDOS | os arquivos do jogo vão compactados na memória ou num disco de boot do TK2000 |

## 8.2 Os passos

1. **Arrume uma cópia crackeada.** Os arquivos dela são binários DOS 3.3 comuns e o carregador
   é simples; senão, a proteção contra cópia seria o primeiro problema.
2. **Liste os arquivos** (`dos33.py`) e descubra qual é carregado onde e quando.
3. **Dê boot nele num Apple II pequeno escrito em Python** (`a2boot.py`, py65): teclas e joystick
   comandados por script jogam a demonstração, uma partida, todos os níveis. Ele registra o que
   rodou como código e salva a memória no início do jogo.
4. **Desmonte** (`disa2.py`) até cada arquivo remontar em bytes idênticos.
5. **Reloque**: os rótulos se movem sozinhos; endereços que o jogo monta durante a execução, não.
   Ache-os rastreando de onde vem cada byte (`taint.py`) e procurando padrões (`immscan.py`);
   confira cada candidato pela forma como o código o usa.
6. **Confira em lockstep** (`lockstep.py`; execução lado a lado, passo a passo): o original e o
   porte rodam lado a lado, instrução por instrução, com as mesmas teclas; a execução para na
   primeira diferença. Chegue a 0.
7. **Substitua o hardware** por uma camada pequena (`tk.s`): carregador de arquivos, latch do
   teclado, paddles. As instruções de entrada e saída do original são modificadas para pular
   para ela.
8. **Gere a fita e o disco** (`mkimage.py`, `mkct2.py`, `mkdsk.py`) a partir da própria memória
   de início do jogo.
9. **Jogue todas as opções de menu e todas as teclas no emulador.** O lockstep só prova o que ele
   executou: dois bugs (textos dos menus, setas sem efeito) estavam em caminhos que ele nunca
   percorreu.

## 8.3 O que o deixou melhor que o original

Tudo em passos pequenos, cada um aprovado depois de um teste: menus comandados pelas setas,
efeitos sonoros que a versão de Apple nunca teve (golpes, morte, chefe), o tema do fliperama a
partir de um arquivo MIDI, as escadas no fim de cada andar, uma tecla de "nunca morrer" para
explorar todos os andares, a letra do fliperama antes de cada partida no lugar de uma calibração
de joystick de que o TK2000 não precisa, e um disco que dá boot em 2 segundos.
