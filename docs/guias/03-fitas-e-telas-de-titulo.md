# 3. Fitas e telas de título

## 3.1 A imagem de fita `.ct2`

O emulador carrega arquivos `.ct2`: `"CTK2"` seguido de blocos (`CA` tom piloto, `CB`
sincronismo, `DA` dados). Dentro, os dados são o que a ROM do TK2000 grava num cassete de
verdade: cada arquivo é um bloco de cabeçalho (nome de 6 caracteres, endereço de início e de fim)
seguido de blocos de dados de até 256 bytes, cada um com uma soma de verificação.
`tools/mkct2.py` grava tudo isso.

O carregamento corre a cerca de **170 bytes por segundo** numa máquina de verdade: um programa de
24 KB leva cerca de 2 minutos e 20 segundos; uma imagem de tela cheia acrescenta cerca de 48
segundos. O emulador acelera o carregamento automaticamente, então nele leva só alguns segundos.

## 3.2 Uma fita que se inicia sozinha

O jogador digita `LOADT` e aperta Play; nada mais deveria ser necessário. O `mkct2.py` faz o que
as fitas comerciais faziam:

1. O primeiro arquivo é um arquivo minúsculo de página zero (`$0036-$0070`). Ele redireciona o
   vetor de saída de caracteres da ROM para um carregador em `$0050`.
2. Quando a ROM imprime sua mensagem de "carregado", ela chama esse vetor: o carregador restaura
   o vetor, lê os arquivos restantes com a rotina de fita da ROM (`$EDAE`) e salta para o
   programa.

```sh
python3 tools/mkct2.py build/game.bin 0x4000 0x4000 GAME dist/game.ct2           # um arquivo
python3 tools/mkct2.py build/game.bin 0x4000 0x4000 GAME dist/game.ct2 build/low.bin@0x0800
```

Argumentos: o programa, seu endereço de carga, seu endereço de início, um nome (6 caracteres), a
saída e depois até dois arquivos extras (`FILE@ADDRESS`; acrescente `<` depois do endereço para
carregá-lo **antes** do programa). O carregador tem espaço para três leituras extras, então
planeje no máximo quatro arquivos no total.

## 3.3 Uma tela de carregamento de graça

Coloque uma imagem de hi-res em `$2000` **no começo do mesmo arquivo do programa**: ela aparece
linha a linha enquanto o resto carrega. Os dois portes carregam a tela de título e o programa
como um só arquivo a partir de `$2000` (título em `$2000-$3FFF`, programa a partir de `$4000`):

```make
build/full.bin: build/title.bin build/game.bin
	cat build/title.bin build/game.bin > $@
dist/game.ct2: build/full.bin
	python3 tools/mkct2.py build/full.bin 0x2000 0x4000 GAME $@
```

Dois detalhes:

- **A ROM escreve sua linha de status da fita nas linhas 184-191** da página 1 durante o
  carregamento ("GAME 0C 08 WAIT: OK"). Deixe essas 8 linhas lisas, ou guarde uma cópia delas no
  programa e escreva-as de volta quando o programa começar (o porte do xadrez guarda os 320
  bytes e os restaura).
- A ROM deixa o vídeo em monocromático depois do `LOADT`: passe para cores (`sta $C050`) no
  início.

## 3.4 Fazendo a imagem

A tela tem 140 pares coloridos × 192 linhas, com 4 cores por byte de 7 pixels (veja o
[guia 2](02-a-maquina.md)). Para converter uma arte:

1. Redimensione para 140 × 192 pares (um par é cerca de 1,83 vez mais largo do que uma linha é
   alta).
2. Escolha a paleta de cada byte (teste as duas e fique com a de menor erro).
3. Aplique pontilhado (Floyd-Steinberg) com as cores da paleta escolhida.

O pontilhado completo fica granulado em fotos, mas manteve os rostos reconhecíveis no título do
xadrez; arte de desenho animado, com cores chapadas, converte melhor com pouco ou nenhum
pontilhado. Um reforço de saturação/contraste muda muito o resultado: faça dele uma opção e
mostre as alternativas.

Desenhe o texto do título **depois** do pontilhado, a partir de uma fonte de verdade renderizada
na resolução de pares (o título do xadrez usa Rockwell para o nome), com um contorno preto para
que se leia sobre qualquer fundo.

**Mantenha a tela convertida no repositório** (8 KB) e carimbe as partes pequenas que mudam na
hora da compilação: o porte do xadrez guarda `art/title.bin` e carimba a versão ("V. 0.9")
abaixo dos créditos a partir de uma variável `VERSION` no Makefile, de modo que uma versão nova
não precisa da arte original nem de uma nova conversão.

## 3.5 A sequência antes do jogo

O que os jogadores dos dois portes viram:

1. A imagem de título enquanto a fita carrega; "PRESS SPACE" ao terminar.
2. Uma tela de instruções (xadrez: texto da ROM com os controles e os nomes dos níveis; River
   Raid: o texto da missão rolando para cima).
3. O jogo.

Só a primeira partida passa por elas; "novo jogo" vai direto para o tabuleiro.

## 3.6 Direitos

A arte do título e o código do jogo costumam ter dono. Mantenha portes de jogos comerciais e de
arte protegida por direitos autorais em repositórios **privados**, dê crédito aos autores na
tela de título e no README e peça autorização antes de publicar. O motor de xadrez usado aqui é
livre para uso não comercial com crédito (os termos do autor dele); a arte do título não é,
então esse porte fica privado até que o artista concorde.
