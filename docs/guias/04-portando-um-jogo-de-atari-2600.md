# 4. Portando um jogo de Atari 2600

A partir do porte do River Raid. Um jogo de 2600 é código 6502 como o do TK2000, então a
**lógica** é portada quase linha por linha; tudo o que os chips do 2600 faziam (desenho, posições,
colisões, som, temporização) vira software no TK2000.

## 4.1 Comece de um fonte verificado

1. Encontre uma desmontagem comentada (River Raid: a de Thomas Jentzsch).
2. Remonte-a com o `dasm` e compare com o cartucho de verdade (MD5) **antes de confiar nela**.
3. Rode o original num simulador de 6502 (py65, em Python), com os chips de vídeo e de
   temporização do 2600 reduzidos a registradores. Essa é a referência contra a qual cada passo
   seguinte é conferido.

Guarde a imagem da ROM em `reference/` e tire as tabelas originais (formas, cores, dados das
fases) direto dela com `.incbin` nos endereços que elas têm na ROM, em vez de digitá-las de novo.

## 4.2 Porte a lógica, mantenha a página zero

- **Mantenha as variáveis do original nos endereços do 2600 (`$80-$FF`).** Assim o código da
  lógica é portado instrução por instrução, com os rótulos e comentários originais; o
  renderizador do TK2000 usa o resto da página zero.
- Troque só o acesso ao hardware. O que o chip TIA do 2600 fazia tem de virar código:
  - **posições:** o 2600 guarda a temporização grossa/fina do feixe; guarde um x simples (0-159)
  - **área de jogo (playfield):** as ordens de bits de PF0/PF1/PF2 (PF0 e PF2 invertidos,
    metades espelhadas ou repetidas)
  - **tamanhos e cópias** dos objetos (NUSIZ), **reflexão** (REFP)
  - **colisões:** faça AND dos pixels dos dois objetos nas mesmas colunas; teste os bits do
    playfield sob os pixels do sprite
- **Confira a lógica portada contra o original**, gerando os mesmos dados de jogo: o River Raid
  comparou os blocos de rio gerados pelo original e pelo porte nas fases 1-9 (316 blocos, 0
  diferenças) antes de desenhar qualquer coisa.

Coisas sutis que quebraram:

- O TIA registra as colisões durante um quadro e o jogo as lê no seguinte. Num porte que desenha
  uma vez a cada 2-3 tiques de jogo, uma colisão vale para todos eles. Se o original desloca sua
  lista de objetos (o River Raid desce os objetos uma posição a cada bloco), qualquer índice de
  objeto guardado também tem de ser deslocado, senão a colisão atinge o vizinho (passar por cima
  do combustível explodia o helicóptero acima dele).
- Objetos rápidos (o míssil anda 6 linhas por tique) têm de ser testados a cada tique, não a
  cada imagem desenhada, senão eles pulam por cima dos alvos.

## 4.3 Desenhe só o que mudou

O 2600 redesenha a tela 60 vezes por segundo de graça; o TK2000 precisa de ~80 ms para
reescrever uma página. O que fez o River Raid rodar a ~20-24 imagens por segundo:

- **Renderização por diferença:** guarde, por página, o que cada linha mostra; reescreva só os
  bytes que mudaram. Pré-calcule os bytes de saída para cada valor do playfield.
- **Sprites pré-deslocados:** 7 cópias de cada sprite (uma por deslocamento de pixel dentro de
  um byte), geradas por uma ferramenta em Python a partir das formas originais.
- **Apague recalculando o fundo** a partir do estado "mostrado" e desenhe um objeto em movimento
  numa só passada sobre a união do retângulo antigo com o novo (apagar + desenhar juntos: menos
  escritas, menos cintilação).
- **Duas páginas:** desenhe na página escondida e depois troque. Todo registro do "que está
  mostrado" tem de ser mantido por página.
- **Escala:** um pixel do 2600 = um par de pixels do TK2000 (assim o branco funciona sobre
  qualquer fundo); as 160 colunas do 2600 viram 280 pixels, então os sprites ficam um pouco mais
  largos que no original.
- **Cores:** mapeie a paleta do 2600 para a do TK2000 com uma tabela explícita, decidida com o
  dono do projeto (River Raid: helicóptero preto, avião branco). Renderize as opções de cores
  lado a lado antes de escolher.

Meça antes de otimizar: no River Raid, o desenho dos objetos levava ~63% do quadro e o
renderizador do rio ~25%; desenrolar mais os laços depois que as tabelas estavam prontas não
compensou.

## 4.4 Velocidade do jogo sem temporizador

O 2600 roda sua lógica uma vez por quadro (60 por segundo). O TK2000 desenha mais devagar e de
forma irregular, então o River Raid separa as duas coisas:

- A lógica original roda em **tiques** de 1/60 s (17.068 ciclos cada).
- Cada imagem desenhada roda tantos tiques quanto o tempo que ela levou (2-3 a ~24 fps, imagens
  por segundo).
- O tempo é **estimado**: cada rotina soma o seu custo em ciclos a um contador (por imagem, por
  linha de sprite desenhada, por grupo do renderizador, por rajada de som...). Uma imagem mais
  curta que um tique espera o resto.
- Os custos são **calibrados** no py65 (mínimos quadrados sobre milhares de quadros), e então a
  velocidade é conferida no emulador contando os tiques por segundo emulado (meta: 59,9).

O emulador não soma o ciclo extra das leituras que cruzam página, então ele roda 3-5% mais rápido
do que as contagens do py65; o River Raid ajustou a escala dos seus custos para que o emulador
mostre a velocidade certa.

## 4.5 Som por último

Porte a lógica de som do original como ela é (ela produz valores de registradores do TIA a cada
tique) e depois transforme esses valores em som de 1 bit: uma rajada curta por efeito, na altura
original (veja o [guia 2](02-a-maquina.md#26-som)). Compare WAVs do TK2000 com WAVs renderizados a
partir dos valores de registradores do original, um efeito de cada vez.

## 4.6 Ordem de trabalho que funcionou

1. Fonte verificado e simulação do original.
2. Layout da tela e cores (mostre as opções).
3. Plano de memória.
4. Ferramentas: gerador de fita, geradores de gráficos, executor sem janela, scripts de
   comparação.
5. Lógica, conferida contra o original.
6. Renderizador, depois os sprites.
7. Ritmo de quadros, calibrado.
8. Colisões, placar, barra de status, estados do jogo.
9. Som, um efeito de cada vez.
10. Telas de introdução e a fita final.
